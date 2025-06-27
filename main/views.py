# -*- coding: utf-8 -*-

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.core.mail import send_mail

from .models import Ticket, Attachment, FollowUp
from .forms import UserSettingsForm, TicketCreateForm, TicketEditForm, FollowupForm, AttachmentForm

import logging
logger = logging.getLogger(__name__)


def inbox_view(request):
    users = User.objects.all()
    tickets_unassigned = Ticket.objects.exclude(assigned_to__in=users)
    tickets_assigned = Ticket.objects.filter(assigned_to__in=users)
    return render(request, 'main/inbox.html', {
        "tickets_assigned": tickets_assigned,
        "tickets_unassigned": tickets_unassigned,
    })


def my_tickets_view(request):
    tickets = Ticket.objects.filter(assigned_to=request.user).exclude(status="DONE")
    tickets_waiting = Ticket.objects.filter(waiting_for=request.user, status="WAITING")
    return render(request, 'main/my-tickets.html', {
        "tickets": tickets,
        "tickets_waiting": tickets_waiting,
    })


def all_tickets_view(request):
    tickets_open = Ticket.objects.exclude(status="DONE")
    return render(request, 'main/all-tickets.html', {"tickets": tickets_open})


def archive_view(request):
    tickets_closed = Ticket.objects.filter(status="DONE")
    return render(request, 'main/archive.html', {"tickets": tickets_closed})


def usersettings_update_view(request):
    user = request.user
    if request.method == 'POST':
        form_user = UserSettingsForm(request.POST)
        if form_user.is_valid():
            user.first_name = request.POST['first_name']
            user.last_name = request.POST['last_name']
            user.save()
            return HttpResponseRedirect(request.GET.get('next', '/inbox/'))
    else:
        form_user = UserSettingsForm(instance=user)
    return render(request, 'main/settings.html', {'form_user': form_user})


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
    return render(request, 'main/ticket_edit.html', {'form': form})


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
    return render(request, 'main/ticket_edit.html', {'form': form})


def ticket_detail_view(request, pk):
    ticket = get_object_or_404(Ticket, id=pk)
    attachments = Attachment.objects.filter(ticket=ticket)
    followups = FollowUp.objects.filter(ticket=ticket)
    return render(request, 'main/ticket_detail.html', {
        'ticket': ticket,
        'attachments': attachments,
        'followups': followups,
    })


def followup_create_view(request):
    if request.method == 'POST':
        form = FollowupForm(request.POST)
        if form.is_valid():
            followup = form.save()
            ticket = followup.ticket

            # Send notification email
            notification_subject = "[#{}] New followup".format(ticket.id)
            notification_body = (
                "Hi,\n\nNew followup created for ticket #{} (http://localhost:8000/ticket/{}/)\n\n"
                "Title: {}\n\n{}".format(
                    ticket.id, ticket.id, form.cleaned_data['title'], form.cleaned_data['text']
                )
            )
            send_mail(notification_subject, notification_body, 'test@test.tld',
                      [ticket.owner.email], fail_silently=False)

            return redirect('inbox')
    else:
        form = FollowupForm(initial={'ticket': request.GET.get('ticket'), 'user': request.user})
    return render(request, 'main/followup_edit.html', {'form': form})


def followup_edit_view(request, pk):
    data = get_object_or_404(FollowUp, id=pk)
    if request.method == 'POST':
        form = FollowupForm(request.POST, instance=data)
        if form.is_valid():
            form.save()
            return redirect('inbox')
    else:
        form = FollowupForm(instance=data)
    return render(request, 'main/followup_edit.html', {'form': form})


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
    return render(request, 'main/attachment_add.html', {'form': form})
