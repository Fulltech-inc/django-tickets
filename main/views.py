# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils import timezone
from .models import Ticket, Attachment, FollowUp
from .forms import UserSettingsForm, TicketCreateForm, TicketEditForm, FollowupForm, AttachmentForm
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def inbox_view(request):
    tickets = Ticket.objects.filter(assigned_to=request.user).exclude(status="DONE")
    tickets_waiting = Ticket.objects.filter(waiting_for=request.user, status="WAITING")
    context = {
        "tickets": tickets,
        "tickets_waiting": tickets_waiting,
    }
    return render(request, 'main/inbox.html', context)


def all_tickets_view(request):
    tickets_open = Ticket.objects.exclude(status="DONE")
    context = {"tickets": tickets_open}
    return render(request, 'main/all-tickets.html', context)


def archive_view(request):
    tickets_closed = Ticket.objects.filter(status="DONE")
    context = {"tickets": tickets_closed}
    return render(request, 'main/archive.html', context)


def usersettings_update_view(request):
    user = request.user
    if request.method == 'POST':
        form_user = UserSettingsForm(request.POST, instance=user)
        if form_user.is_valid():
            form_user.save()
            return HttpResponseRedirect(request.GET.get('next', '/inbox/'))
    else:
        form_user = UserSettingsForm(instance=user)
    context = {'form_user': form_user}
    return render(request, 'main/settings.html', context)



from urllib.parse import unquote

def ticket_create_view(request):
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.status = "TODO"
            obj.save()

            # Email notifications
            try:
                base_url = f"http://{request.get_host()}/ticket/{obj.id}/"
                
                logger.info(f"Sending email: [#{obj.id}] Assigned a ticket")

                result = send_mail(
                    subject=f"[#{obj.id}] Assigned a ticket",
                    message=f"Hi,\n\nA ticket was assigned to you: {base_url}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[obj.assigned_to.email],
                    fail_silently=False,
                )

                logger.info(f"Result: {result}")

            except Exception as e:
                logger.error(f"Email failed: {e}")

            return redirect('inbox')
    else:
        # Extract caller info from GET parameters
        call_id = request.GET.get('call_id', '')
        caller_id = request.GET.get('caller_id', '')
        caller_name = request.GET.get('caller_name', '')
        queue = request.GET.get('queue', '')

        # Optional: Decode URL-encoded values
        caller_id = unquote(caller_id)
        caller_name = unquote(caller_name)

        # Prepopulate form fields
        initial_data = {
            'title': f"Call from {caller_name}" if caller_name else '',
            'description': f"Calle ID: {call_id}\nCaller ID: {caller_id}\nCaller Name: {caller_name}\nQueue: {queue}" if  call_id or caller_id or caller_name or queue else ''
        }

        form = TicketCreateForm(initial=initial_data)

    context = {'form': form}
    return render(request, 'main/ticket_edit.html', context)



def ticket_edit_view(request, pk):
    data = get_object_or_404(Ticket, id=pk)
    if request.method == 'POST':
        form = TicketEditForm(request.POST, instance=data)
        if form.is_valid():
            data = form.instance

            # Get original values from DB
            old_data = type(data).objects.get(pk=data.pk)

            # Detect changes
            assigned_to_changed = old_data.assigned_to != form.cleaned_data.get('assigned_to')
            waiting_for_changed = old_data.waiting_for != form.cleaned_data.get('waiting_for')

            # Existing logic
            if form.cleaned_data['status'] == "DONE":
                data.closed_date = timezone.now()

            form.save()

            # React to changes
            base_url = f"http://{request.get_host()}/ticket/{data.id}/"
            if assigned_to_changed:

                notification_subject = f"[#{data.id}] Assigned a ticket"
                notification_body = f"Hi,\n\nA ticket was assigned to you: {base_url}"

                # email connection
                try:
                    logger.info("Attempting to send email via send_mail()...")

                    result = send_mail(
                        subject=notification_subject,
                        message=notification_body,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[data.assigned_to.email],
                        fail_silently=False,
                    )

                    logger.info(f"Email send result: {result}")  # should be 1 on success

                except Exception as e:
                    logger.error(f"Email sending failed: {e.__class__.__name__}: {e}")

                logger.info(f"assigned_to changed to {data.assigned_to}")

            if waiting_for_changed:

                notification_subject = f"[#{data.id}] Colleagues are waiting for your input!"
                notification_body = f"Hi,\n\nColleagues are waiting for your input on ticket: {base_url}"

                # email connection
                try:
                    logger.info("Attempting to send email via send_mail()...")

                    result = send_mail(
                        subject=notification_subject,
                        message=notification_body,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[data.waiting_for.email],
                        fail_silently=False,
                    )

                    logger.info(f"Email send result: {result}")  # should be 1 on success

                except Exception as e:
                    logger.error(f"Email sending failed: {e.__class__.__name__}: {e}")

                logger.info(f"waiting_for changed to {data.waiting_for}")

            return redirect('inbox')
    else:
        form = TicketEditForm(instance=data)
    context = {'form': form}
    return render(request, 'main/ticket_edit.html', context)


def ticket_detail_view(request, pk):
    ticket = get_object_or_404(Ticket, id=pk)
    attachments = Attachment.objects.filter(ticket=ticket)
    followups = FollowUp.objects.filter(ticket=ticket)
    context = {
        'ticket': ticket,
        'attachments': attachments,
        'followups': followups,
    }
    return render(request, 'main/ticket_detail.html', context)


def followup_create_view(request):
    if request.method == 'POST':
        form = FollowupForm(request.POST)
        if form.is_valid():
            followup = form.save()
            ticket = followup.ticket

            notification_subject = f"[#{ticket.id}] New followup"
            notification_body = (
                f"Hi,\n\nNew followup created for ticket #{ticket.id} "
                f"(http://{request.get_host()}/ticket/{ticket.id}/)\n\n"
                f"Title: {form.cleaned_data['title']}\n\n{form.cleaned_data['text']}"
            )

            # email connection
            try:
                logger.info("Attempting to send email via send_mail()...")

                result = send_mail(
                    subject=notification_subject,
                    message=notification_body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[ticket.owner.email],
                    fail_silently=False,
                )

                logger.info(f"Email send result: {result}")  # should be 1 on success

            except Exception as e:
                logger.error(f"Email sending failed: {e.__class__.__name__}: {e}")


            return redirect('inbox')
    else:
        form = FollowupForm(initial={'ticket': request.GET.get('ticket'), 'user': request.user})
    context = {'form': form}
    return render(request, 'main/followup_edit.html', context)


def followup_edit_view(request, pk):
    data = get_object_or_404(FollowUp, id=pk)
    if request.method == 'POST':
        form = FollowupForm(request.POST, instance=data)
        if form.is_valid():
            form.save()
            return redirect('inbox')
    else:
        form = FollowupForm(instance=data)
    context = {'form': form}
    return render(request, 'main/followup_edit.html', context)


def attachment_create_view(request):
    if request.method == 'POST':
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = Attachment(
                ticket=get_object_or_404(Ticket, id=request.GET.get('ticket')),
                file=request.FILES['file'],
                filename=request.FILES['file'].name,
                user=request.user
            )
            attachment.save()
            return redirect('inbox')
    else:
        form = AttachmentForm()
    context = {'form': form}
    return render(request, 'main/attachment_add.html', context)


# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────
# ADD these to your existing views.py
# ─────────────────────────────────────────────────────────────

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import TicketEscalation, Ticket


def escalations_view(request):
    """
    Escalation dashboard.
    - Superusers / managers see ALL pending escalations.
    - Regular users see only escalations assigned to them.
    """
    user = request.user

    if user.is_superuser or user.is_staff:
        escalations = TicketEscalation.objects.select_related(
            'ticket', 'escalated_from_user', 'escalated_to_user'
        ).exclude(status='RESOLVED').order_by('-escalated_at')
    else:
        escalations = TicketEscalation.objects.filter(
            escalated_to_user=user
        ).select_related(
            'ticket', 'escalated_from_user', 'escalated_to_user'
        ).exclude(status='RESOLVED').order_by('-escalated_at')

    context = {
        'escalations': escalations,
        'pending_count': escalations.filter(status='PENDING').count(),
    }
    return render(request, 'main/escalations.html', context)


def escalation_acknowledge_view(request, pk):
    """Mark a single escalation as acknowledged."""
    escalation = get_object_or_404(TicketEscalation, id=pk)

    # Only the person it was escalated TO (or staff) can acknowledge
    if request.user != escalation.escalated_to_user and not request.user.is_staff:
        return redirect('escalations')

    if request.method == 'POST':
        escalation.acknowledge(request.user)

    return redirect('escalations')


def escalation_resolve_view(request, pk):
    """Manually resolve an escalation (staff only or ticket owner)."""
    escalation = get_object_or_404(TicketEscalation, id=pk)

    if request.user != escalation.escalated_to_user and not request.user.is_staff:
        return redirect('escalations')

    if request.method == 'POST':
        escalation.resolve()
        # Also mark the ticket DONE if the user chose to close it
        if request.POST.get('close_ticket'):
            ticket = escalation.ticket
            ticket.status = 'DONE'
            ticket.closed_date = timezone.now()
            ticket.save(update_fields=['status', 'closed_date'])

            # Resolve all other open escalations for this ticket
            TicketEscalation.objects.filter(
                ticket=ticket,
                status__in=['PENDING', 'ACKNOWLEDGED']
            ).update(status='RESOLVED', resolved_at=timezone.now())

    return redirect('escalations')
