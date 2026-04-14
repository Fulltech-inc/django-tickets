# -*- coding: utf-8 -*-
# main/escalation.py
import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Ticket, TicketEscalation, EscalationConfig
from .activity_utils import log_activity

logger = logging.getLogger(__name__)


def _send_escalation_email(subject, message, recipient_email):
    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info(f"Email sent to {recipient_email}: {result}")
    except Exception as e:
        logger.error(f"Email failed to {recipient_email}: {e}")

def _escalate(ticket, level, from_user, to_user, base_url=""):
    if not to_user:
        logger.warning(f"Ticket #{ticket.id}: no target user for L{level}, skipping.")
        return

    ticket.assigned_to = to_user
    ticket.escalation_count = level
    ticket.last_escalation_at = timezone.now()
    ticket.save(update_fields=['assigned_to', 'escalation_count', 'last_escalation_at'])

    escalation = TicketEscalation.objects.create(
        ticket=ticket,
        escalation_level=level,
        escalated_from_user=from_user,
        escalated_to_user=to_user,
        status='PENDING',
        notification_sent=False,
    )

    log_activity(
        ticket,
        'ESCALATED',
        performed_by=from_user if from_user else to_user,
        from_dept=from_user,
        to_dept=to_user,
        comment=f"Escalated to Level {level} - {to_user}"
    )

    ticket_url = f"{base_url}/ticket/{ticket.id}/"

    
    # Email to new owner — once only
    _send_escalation_email(
        subject=f"Ticket[#{ticket.id}] escalated to you",
        message=(
            f"Hi {to_user.first_name or to_user.username},\n\n"
            f"Ticket #{ticket.id} — \"{ticket.title}\" has been escalated to you "
            f"because it has not been resolved.\n\n"
            f"Current status: {ticket.status}\n"
            f"Created: {ticket.created.strftime('%d %b %Y %H:%M')}\n"
            f"View ticket: {ticket_url}\n\n"
            f"Please action this as soon as possible."
        ),
        recipient_email=to_user.email,
    )

    title = "manager" if level == 1 else title = "director"
    # Email to previous owner
    if from_user and from_user.email:
        
        _send_escalation_email(
            
            subject=f"Ticket[#{ticket.id}] escalated to the {title}",
            message=(
                f"Hi {from_user.first_name or from_user.username},\n\n"
                f"Ticket #{ticket.id} — \"{ticket.title}\" has been escalated "
                f"to the {title} {to_user.get_full_name() or to_user.username} "
                f"because it was not resolved in time.\n\n"
                f"Current status: {ticket.status}\n"
                f"View ticket: {ticket_url}"
            ),
            recipient_email=from_user.email,
        )

    escalation.notification_sent = True
    escalation.save(update_fields=['notification_sent'])
    logger.info(f"Ticket #{ticket.id} escalated to L{level} -> {to_user}")

def run_escalation_check(base_url=""):
    """
    Checks all non-DONE tickets and escalates based on time since created.
    Clock never resets — status changes and reassignments don't matter.
    Only DONE stops escalation.
    """
    config = EscalationConfig.get_active()
    if not config:
        logger.warning("Escalation skipped: no active EscalationConfig.")
        return

    if not config.level1_manager:
        logger.warning("Escalation skipped: no Level 1 manager set in EscalationConfig.")
        return

    if not config.level2_director:
        logger.warning("Escalation skipped: no Level 2 director set in EscalationConfig.")
        return

    now = timezone.now()
    l1_threshold = timedelta(minutes=config.level1_minutes)
    l2_threshold = timedelta(minutes=config.level2_minutes)

    logger.info(f"Running escalation check — L1:{config.level1_minutes}min L2:{config.level2_minutes}min")

    # ALL tickets that are not DONE — regardless of status or who they're assigned to
    open_tickets = Ticket.objects.exclude(status='DONE').select_related('assigned_to')

    for ticket in open_tickets:
        age = now - ticket.created

        # ── Level 1 ──────────────────────────────────────────
        if ticket.escalation_count == 0 and age >= l1_threshold:
            logger.info(f"Ticket #{ticket.id} (status={ticket.status}) triggering L1 after {age}")
            _escalate(
                ticket=ticket,
                level=1,
                from_user=ticket.assigned_to,
                to_user=config.level1_manager,
                base_url=base_url
            )

        # ── Level 2 ──────────────────────────────────────────
        elif ticket.escalation_count == 1 and ticket.last_escalation_at:
            time_since_l1 = now - ticket.last_escalation_at
            if time_since_l1 >= l2_threshold:
                logger.info(f"Ticket #{ticket.id} (status={ticket.status}) triggering L2 after {time_since_l1} at manager")
                _escalate(
                    ticket=ticket,
                    level=2,
                    from_user=ticket.assigned_to,
                    to_user=config.level2_director,
                    base_url=base_url
                )

        # ── Already at L2 — no further escalation ────────────

    logger.info(f"Escalation check complete at {now.isoformat()}")