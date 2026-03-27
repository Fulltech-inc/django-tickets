# main/escalations.py - Updated to include TODO tickets

import logging
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Ticket, TicketEscalation, EscalationConfig

logger = logging.getLogger(__name__)


def _send_escalation_email(subject, message, recipient_email):
    """Fire-and-forget escalation email."""
    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info(f"Escalation email sent to {recipient_email}: {result}")
    except Exception as e:
        logger.error(f"Escalation email failed to {recipient_email}: {e}")


def _escalate(ticket, level, from_user, to_user, base_url=""):
    """Perform escalation step."""
    if not to_user:
        logger.warning(f"Cannot escalate: no target user for level {level}")
        return
        
    # Reassign
    ticket.assigned_to = to_user
    ticket.escalation_count = level
    ticket.last_escalation_at = timezone.now()
    ticket.save(update_fields=['assigned_to', 'escalation_count', 'last_escalation_at'])

    # Log the escalation record
    escalation = TicketEscalation.objects.create(
        ticket=ticket,
        escalation_level=level,
        escalated_from_user=from_user,
        escalated_to_user=to_user,
        status='PENDING',
        notification_sent=False,
    )

    ticket_url = f"{base_url}/ticket/{ticket.id}/"

    # Notify new owner
    _send_escalation_email(
        subject=f"[Escalation L{level}] Ticket #{ticket.id} assigned to you",
        message=(
            f"Hi {to_user.first_name or to_user.username},\n\n"
            f"Ticket #{ticket.id} — \"{ticket.title}\" has been escalated to you "
            f"(Level {level}) because it has been left untouched too long.\n\n"
            f"Status: {ticket.status}\n"
            f"View ticket: {ticket_url}\n\n"
            f"Please action this as soon as possible."
        ),
        recipient_email=to_user.email,
    )

    # Notify previous owner
    if from_user and from_user.email:
        _send_escalation_email(
            subject=f"[Escalation L{level}] Ticket #{ticket.id} escalated from your queue",
            message=(
                f"Hi {from_user.first_name or from_user.username},\n\n"
                f"Ticket #{ticket.id} — \"{ticket.title}\" has been escalated "
                f"(Level {level}) to {to_user.get_full_name() or to_user.username} "
                f"because it was left untouched beyond the allowed time.\n\n"
                f"Status: {ticket.status}\n"
                f"View ticket: {ticket_url}"
            ),
            recipient_email=from_user.email,
        )

    escalation.notification_sent = True
    escalation.save(update_fields=['notification_sent'])

    logger.info(f"Ticket #{ticket.id} escalated to Level {level} from {from_user} to {to_user}")


def run_escalation_check(base_url=""):
    """
    Main entry point - checks all WAITING and TODO tickets and escalates based on:
    - User's profile targets (who to escalate to)
    - Global config thresholds (when to escalate)
    """
    # Get active config for thresholds
    config = EscalationConfig.get_active()
    if not config:
        logger.warning("No active EscalationConfig found. Skipping escalation check.")
        return
    
    if not config.is_active:
        logger.info("Escalation is disabled in config.")
        return
    
    l1_threshold = timedelta(minutes=config.level1_minutes)
    l2_threshold = timedelta(minutes=config.level2_minutes)
    
    logger.info(f"Using thresholds: L1={config.level1_minutes}min, L2={config.level2_minutes}min")
    
    now = timezone.now()
    
    # Check BOTH WAITING and TODO tickets
    stale_tickets = Ticket.objects.filter(
        status__in=['WAITING', 'TODO']  # <-- Added TODO status
    ).select_related('assigned_to__profile')

    for ticket in stale_tickets:
        if not ticket.assigned_to:
            logger.warning(f"Ticket #{ticket.id}: No assigned user, skipping escalation")
            continue
            
        profile = ticket.assigned_to.profile
        idle_time = now - ticket.updated

        # Level 1 escalation
        if ticket.escalation_count == 0 and idle_time >= l1_threshold:
            if profile.level1_target:
                logger.info(f"Escalating ticket #{ticket.id} (status={ticket.status}) to Level 1 (target: {profile.level1_target})")
                _escalate(ticket, 1, ticket.assigned_to, profile.level1_target, base_url)
            else:
                logger.warning(f"Ticket #{ticket.id}: No Level 1 target set for user {ticket.assigned_to}")

        # Level 2 escalation
        elif ticket.escalation_count == 1 and ticket.last_escalation_at:
            time_since_level1 = now - ticket.last_escalation_at
            if time_since_level1 >= l2_threshold:
                if profile.level2_target:
                    logger.info(f"Escalating ticket #{ticket.id} (status={ticket.status}) to Level 2 (target: {profile.level2_target})")
                    _escalate(ticket, 2, ticket.assigned_to, profile.level2_target, base_url)
                else:
                    logger.warning(f"Ticket #{ticket.id}: No Level 2 target set for user {ticket.assigned_to}")

    logger.info(f"Escalation check complete at {now.isoformat()}")