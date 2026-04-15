# -*- coding: utf-8 -*-

# Standard library
import csv
import logging
from datetime import timedelta
from io import BytesIO
from urllib.parse import unquote

# Django
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# Third-party
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Local
from .activity_utils import log_activity
from .forms import AttachmentForm, FollowupForm, TicketCreateForm, TicketEditForm, UserSettingsForm
from .models import (
    Attachment,
    Category,
    FollowUp,
    GeneratedReport,
    Ticket,
    TicketActivity,
    TicketEscalation,
)


logger = logging.getLogger(__name__)


def inbox_view(request):
    user = request.user

    tickets = Ticket.objects.filter(assigned_to=user).exclude(status="DONE")
    tickets_waiting = Ticket.objects.filter(waiting_for=user, status="WAITING")

    from django.db.models import Prefetch
    tickets = tickets.prefetch_related(Prefetch('attachment_set', to_attr='prefetched_attachments'))
    tickets_waiting = tickets_waiting.prefetch_related(Prefetch('attachment_set', to_attr='prefetched_attachments'))

    context = {"tickets": tickets, "tickets_waiting": tickets_waiting}
    return render(request, 'main/inbox.html', context)


def get_subcategories(request):
    main_id = request.GET.get('main_id')
    subs = Category.objects.filter(
        is_active=True, parent_id=main_id
    ).values('id', 'name')
    return JsonResponse(list(subs), safe=False)


def all_tickets_view(request):
    user = request.user
    tickets_open = Ticket.objects.exclude(status="DONE").select_related(
        'category', 'sub_category', 'owner', 'assigned_to'
    )
    context = {"tickets": tickets_open}
    return render(request, 'main/all-tickets.html', context)


def archive_view(request):
    user = request.user
    tickets_closed = Ticket.objects.filter(status="DONE").select_related(
        'category', 'sub_category', 'owner', 'assigned_to'
    )
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

            log_activity(obj, 'CREATED', request.user, comment=f"Ticket created with title: {obj.title}")
            if obj.assigned_to:
                log_activity(obj, 'ASSIGNED', request.user, to_dept=obj.assigned_to, comment=f"Assigned to {obj.assigned_to}")

            # Handle Multiple Attachments
            files = request.FILES.getlist('attachments')
            for f in files:
                Attachment.objects.create(
                    ticket=obj,
                    file=f,
                    filename=f.name,
                    user=request.user
                )

            # Send email notification — single clean attempt
            if obj.assigned_to and obj.assigned_to.email:
                try:
                    base_url = f"http://{request.get_host()}/ticket/{obj.id}/"
                    send_mail(
                        subject=f"Assigned New Ticket[#{obj.id}]: {obj.title}",
                        message=(
                            f"Hi {obj.assigned_to.first_name or obj.assigned_to.username},\n\n"
                            f"A new ticket has been assigned to you.\n\n"
                            f"Title: {obj.title}\n"
                            f"Interaction ID: {obj.interaction_id or 'N/A'}\n"
                            f"Status: {obj.status}\n\n"
                            f"View ticket: {base_url}"
                        ),
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[obj.assigned_to.email],
                        fail_silently=False,
                    )
                    logger.info(f"Email sent to {obj.assigned_to.email} for ticket #{obj.id}")
                except Exception as e:
                    logger.error(f"Email failed for ticket #{obj.id}: {e}")
            else:
                logger.info(f"Ticket #{obj.id} created with no assigned user or no email — skipping notification")

            return redirect('inbox')
    else:
        channel_type=request.GET.get('channel_type', '')

        if channel_type == "voice":
            # Extract caller info from GET parameters
            call_id = request.GET.get('call_id', '')
            caller_id = request.GET.get('caller_id', '')
            caller_name = request.GET.get('caller_name', '')
            queue = request.GET.get('queue', '')

            # Optional: Decode URL-encoded values
            # caller_id = unquote(caller_id)
            # caller_name = unquote(caller_name)

            # Prepopulate form fields
            initial_data = {
                'title': f"Call from {caller_name}" if caller_name else '',
                'description': f"Channel Type: {channel_type}\nCaller ID: {caller_id}\nCaller Name: {caller_name}\nQueue: {queue}\n\n" if caller_id or caller_name or queue else '',
                'interaction_id': call_id
            }

        elif channel_type == "whatsapp":
        
            # Extract caller info from GET parameters
            queue_id = request.GET.get('queue_id', '')
            interaction_id = request.GET.get('interaction_id', '')
            customer_mobile_phone = request.GET.get('phone', '')

            # Prepopulate form fields
            initial_data = {
                'title': f"interaction from {customer_mobile_phone}" if customer_mobile_phone else '',
                'description': f"Channel Type: {channel_type}\nCustomer mobile phone: {customer_mobile_phone}\nQueue ID: {queue_id}\n\n" if  customer_mobile_phone or queue_id else '',
                'interaction_id': f"{interaction_id}"
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

            # After form.save() but before redirect
            if assigned_to_changed:
                log_activity(data, 'REASSIGNED', request.user, 
                            from_dept=old_data.assigned_to, 
                            to_dept=data.assigned_to,
                            comment=f"Reassigned from {old_data.assigned_to} to {data.assigned_to}")

            if waiting_for_changed:
                log_activity(data, 'WAITING_FOR', request.user,
                            to_dept=data.waiting_for,
                            comment=f"Waiting for input from {data.waiting_for}")

            if form.cleaned_data['status'] == "DONE" and old_data.status != "DONE":
                log_activity(data, 'CLOSED', request.user, comment="Ticket closed")

            # React to changes
            base_url = f"http://{request.get_host()}/ticket/{data.id}/"
            if assigned_to_changed:

                notification_subject = f"Assigned Ticket[#{data.id}]"
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

    activities = TicketActivity.objects.filter(ticket=ticket)
    context['activities'] = activities

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

def reports_view(request):
    # Only superusers and staff can access reports
    if not request.user.is_superuser and not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to view reports.")
    
    context = {}
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status_filter = request.GET.get('status')
    assigned_to_filter = request.GET.get('assigned_to')
    category_filter = request.GET.get('category')
    date_filter = request.GET.get('date_filter', 'all')

    today = timezone.now().date()
    if date_filter == 'today':
        start_date = end_date = today
    elif date_filter == 'week':
        start_date = today - timedelta(days=7); end_date = today
    elif date_filter == 'month':
        start_date = today - timedelta(days=30); end_date = today

    # Superusers see all tickets, staff see all tickets
    tickets = Ticket.objects.all().select_related('assigned_to', 'owner', 'category', 'sub_category')

    if start_date and end_date:
        from django.utils.dateparse import parse_date
        start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
        end_date = parse_date(end_date) if isinstance(end_date, str) else end_date
        if start_date and end_date:
            tickets = tickets.filter(created__date__gte=start_date, created__date__lte=end_date)
            context['start_date'] = start_date
            context['end_date'] = end_date

    if status_filter:
        tickets = tickets.filter(status=status_filter)
        context['status_filter'] = status_filter
    if assigned_to_filter:
        tickets = tickets.filter(assigned_to__id=assigned_to_filter)
        context['assigned_to_filter'] = assigned_to_filter
    if category_filter:
        tickets = tickets.filter(category__id=category_filter)
        context['category_filter'] = category_filter

    context['tickets'] = tickets
    context['total_tickets'] = tickets.count()
    context['open_tickets'] = tickets.exclude(status='DONE').count()
    context['closed_tickets'] = tickets.filter(status='DONE').count()

    context['status_summary'] = tickets.values('status').annotate(count=Count('id')).order_by('status')
    context['category_summary'] = tickets.values('category__name').annotate(count=Count('id')).order_by('-count')
    context['dept_summary'] = tickets.values(
        'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name'
    ).annotate(
        total=Count('id'),
        todo=Count('id', filter=Q(status='TODO')),
        in_progress=Count('id', filter=Q(status='IN PROGRESS')),
        waiting=Count('id', filter=Q(status='WAITING')),
        closed=Count('id', filter=Q(status='DONE'))
    ).order_by('-total')

    closed_tickets = tickets.filter(status='DONE', closed_date__isnull=False)
    context['avg_resolution'] = None
    if closed_tickets.exists():
        total_seconds = sum([(t.closed_date - t.created).total_seconds() for t in closed_tickets])
        context['avg_resolution'] = round(total_seconds / closed_tickets.count() / 3600, 2)

    context['status_choices'] = Ticket.STATUS_CHOICES
    context['users'] = User.objects.filter(is_active=True)
    context['categories'] = Category.objects.filter(parent__isnull=True, is_active=True)
    context['date_filter'] = date_filter

    ticket_ids = tickets.values_list('id', flat=True)
    escalated_tickets = TicketEscalation.objects.filter(
        ticket__id__in=ticket_ids
    ).select_related('ticket', 'ticket__category', 'ticket__sub_category',
                     'escalated_to_user', 'escalated_from_user', 'ticket__assigned_to')
    context['escalated_tickets'] = escalated_tickets
    context['escalated_count'] = escalated_tickets.values('ticket_id').distinct().count()

    return render(request, 'main/reports.html', context)



def export_reports_excel(request):
    import csv
    from django.db.models import Prefetch

    start_date         = request.GET.get('start_date')
    end_date           = request.GET.get('end_date')
    status_filter      = request.GET.get('status')
    assigned_to_filter = request.GET.get('assigned_to')
    category_filter    = request.GET.get('category')
    date_filter        = request.GET.get('date_filter', 'all')

    today = timezone.now().date()
    if date_filter == 'today':
        start_date = end_date = today
    elif date_filter == 'week':
        start_date = today - timedelta(days=7); end_date = today
    elif date_filter == 'month':
        start_date = today - timedelta(days=30); end_date = today

    tickets = Ticket.objects.all().select_related(
        'assigned_to', 'owner', 'category', 'sub_category', 'waiting_for'
    ).prefetch_related(
        Prefetch('escalations', queryset=TicketEscalation.objects.select_related(
            'escalated_to_user', 'escalated_from_user'
        ).order_by('-escalated_at')),
        'attachment_set',
        'followup_set',
    ).order_by('-created')

    if start_date and end_date:
        from django.utils.dateparse import parse_date
        start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
        end_date   = parse_date(end_date)   if isinstance(end_date, str) else end_date
        if start_date and end_date:
            tickets = tickets.filter(created__date__gte=start_date, created__date__lte=end_date)

    if status_filter:       tickets = tickets.filter(status=status_filter)
    if assigned_to_filter:  tickets = tickets.filter(assigned_to__id=assigned_to_filter)
    if category_filter:     tickets = tickets.filter(category__id=category_filter)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ticket_report.csv"'
    writer = csv.writer(response)

    # Applied filters info row at top
    filter_parts = []
    if start_date and end_date:
        filter_parts.append(f"Date: {start_date} to {end_date}")
    if status_filter:
        filter_parts.append(f"Status: {status_filter}")
    if category_filter:
        filter_parts.append(f"Category ID: {category_filter}")
    if assigned_to_filter:
        filter_parts.append(f"Assignee ID: {assigned_to_filter}")
    filter_str = "  |  ".join(filter_parts) if filter_parts else "No filters applied — showing all tickets"

    #writer.writerow([f'Ticket Report — Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}  |  {filter_str}'])
    #writer.writerow([])  # blank spacer row

    # REMOVED COLUMNS: Owner, Escalated To, Escalated From, Escalated At, Escalation Acknowledged At, Follow-up Count, Attachment Count
    writer.writerow([
        'Ticket ID',
        'Interaction ID',
        'Title',
        'Description',
        'Status',
        'Main Category',
        'Sub Category',
        # 'Owner',  # REMOVED - Line 1
        'Assigned To',
        'Waiting For',
        'Created At',
        'Last Updated',
        'Closed At',
        'Resolution Time (mins)',
        'Escalated?',
        'Escalation Level',
        # 'Escalation Status',
        # 'Escalated To',  # REMOVED - Line 2
        # 'Escalated From',  # REMOVED - Line 3
        # 'Escalated At',  # REMOVED - Line 4
        # 'Escalation Acknowledged At',  # REMOVED - Line 5
        # 'Follow-up Count',  # REMOVED - Line 6
        # 'Attachment Count',  # REMOVED - Line 7
    ])

    for ticket in tickets:
        res_hrs = ''
        if ticket.closed_date:
            res_hrs = round((ticket.closed_date - ticket.created).total_seconds() / 60, 2)

        escalations = list(ticket.escalations.all())
        if escalations:
            e = escalations[0]
            escalated    = 'Yes'
            esc_level    = f'Level {e.escalation_level}'
            esc_status   = e.get_status_display()
            # REMOVED: esc_to, esc_from, esc_at, esc_ack variables
            # esc_to       = str(e.escalated_to_user) if e.escalated_to_user else ''
            # esc_from     = str(e.escalated_from_user) if e.escalated_from_user else ''
            # esc_at       = e.escalated_at.strftime('%Y-%m-%d %H:%M')
            # esc_ack      = e.acknowledged_at.strftime('%Y-%m-%d %H:%M') if e.acknowledged_at else ''
        else:
            escalated  = 'No'
            esc_level  = ''
            esc_status = ''
            # REMOVED: esc_to, esc_from, esc_at, esc_ack = '', '', '', ''

        # Replace â€” (em dash) with empty string for blank cells
        def clean_value(value):
            """Convert None or '—' to empty string for clean Excel export"""
            if value is None or value == '—' or value == 'â€”':
                return ''
            return value

        writer.writerow([
            clean_value(f'#{ticket.id}'),
            clean_value(ticket.interaction_id or ''),
            clean_value(ticket.title),
            clean_value((ticket.description[:300] + '...') if ticket.description and len(ticket.description) > 300 else (ticket.description or '')),
            clean_value(ticket.status or ''),
            clean_value(ticket.category.name if ticket.category else ''),
            clean_value(ticket.sub_category.name if ticket.sub_category else ''),
            # clean_value(ticket.owner.get_full_name() or ticket.owner.username if ticket.owner else ''),  # REMOVED
            clean_value(ticket.assigned_to.get_full_name() or ticket.assigned_to.username if ticket.assigned_to else ''),
            clean_value(ticket.waiting_for.get_full_name() or ticket.waiting_for.username if ticket.waiting_for else ''),
            clean_value(ticket.created.strftime('%Y-%m-%d %H:%M')),
            clean_value(ticket.updated.strftime('%Y-%m-%d %H:%M')),
            clean_value(ticket.closed_date.strftime('%Y-%m-%d %H:%M') if ticket.closed_date else ''),
            clean_value(res_hrs or ''),
            clean_value(escalated),
            clean_value(esc_level),
            #clean_value(esc_status),
            # clean_value(esc_to),  # REMOVED
            # clean_value(esc_from),  # REMOVED
            # clean_value(esc_at),  # REMOVED
            # clean_value(esc_ack),  # REMOVED
            # clean_value(ticket.followup_set.count()),  # REMOVED
            # clean_value(ticket.attachment_set.count()),  # REMOVED
        ])

    return response

def delete_reports_view(request):
    if request.method == 'POST':
        ids = request.POST.getlist('report_ids')
        GeneratedReport.objects.filter(id__in=ids, requested_by=request.user).delete()
    return redirect('generated_reports')

 

def queue_report_view(request):
    if not request.user.is_superuser and not request.user.is_staff:
        return HttpResponseForbidden()

    filters = {
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
        'status': request.GET.get('status', ''),
        'assigned_to': request.GET.get('assigned_to', ''),
        'category': request.GET.get('category', ''),
        'date_filter': request.GET.get('date_filter', 'all'),
    }

    report = GeneratedReport.objects.create(
        requested_by=request.user,
        filters=filters,
        status='QUEUED',
    )

    # Run synchronously — no background worker needed
    try:
        from .tasks import generate_report_task
        generate_report_task(report.id)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")

    return JsonResponse({
        'status': 'queued',
        'report_id': report.id,
        'message': 'Report generated successfully! Go to My Reports to download.',
    })



def generated_reports_view(request):
    """Page showing all generated reports."""
    reports = GeneratedReport.objects.filter(requested_by=request.user).order_by('-created_at')
    return render(request, 'main/generated_reports.html', {'reports': reports})


def download_report_view(request, pk):
    """Serve the CSV file for download."""
    from django.http import FileResponse, Http404
    report = get_object_or_404(GeneratedReport, id=pk, requested_by=request.user)
    if report.status != 'DONE' or not report.file:
        raise Http404
    return FileResponse(report.file.open('rb'), as_attachment=True, filename=f'ticket_report_{pk}.csv')