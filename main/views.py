# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.core.mail import get_connection, EmailMessage
from django.conf import settings
from .models import Ticket, Attachment, FollowUp
from .forms import UserSettingsForm, TicketCreateForm, TicketEditForm, FollowupForm, AttachmentForm
import logging

logger = logging.getLogger(__name__)


def inbox_view(request):
    users = User.objects.all()
    tickets_unassigned = Ticket.objects.exclude(assigned_to__in=users)
    tickets_assigned = Ticket.objects.filter(assigned_to__in=users)
    context = {
        "tickets_assigned": tickets_assigned,
        "tickets_unassigned": tickets_unassigned,
    }
    return render(request, 'main/inbox.html', context)


def my_tickets_view(request):
    tickets = Ticket.objects.filter(assigned_to=request.user).exclude(status="DONE")
    tickets_waiting = Ticket.objects.filter(waiting_for=request.user, status="WAITING")
    context = {
        "tickets": tickets,
        "tickets_waiting": tickets_waiting,
    }
    return render(request, 'main/my-tickets.html', context)


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


def ticket_create_view(request):
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.status = "TODO"
            obj.save()
            return redirect('inbox')
    else:
        form = TicketCreateForm()
    context = {'form': form}
    return render(request, 'main/ticket_edit.html', context)


def ticket_edit_view(request, pk):
    data = get_object_or_404(Ticket, id=pk)
    if request.method == 'POST':
        form = TicketEditForm(request.POST, instance=data)
        if form.is_valid():
            if form.cleaned_data['status'] == "DONE":
                data.closed_date = timezone.now()
            form.save()
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

            # Manage email connection manually (production-safe)
            connection = get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL,
                fail_silently=False
            )

            email = EmailMessage(
                notification_subject,
                notification_body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_NOTIFICATIONS_TO_EMAIL],
                connection=connection
            )
            email.send()


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
