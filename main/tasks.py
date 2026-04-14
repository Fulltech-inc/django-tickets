# main/tasks.py
import csv
import io
from django.utils import timezone
from django.db.models import Prefetch
from datetime import timedelta


def generate_report_task(report_id):
    from .models import GeneratedReport, Ticket, TicketEscalation
    from django.core.files.base import ContentFile

    report = GeneratedReport.objects.get(id=report_id)
    report.status = 'PROCESSING'
    report.save(update_fields=['status'])

    try:
        filters = report.filters
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        status_filter = filters.get('status')
        assigned_to_filter = filters.get('assigned_to')
        category_filter = filters.get('category')
        date_filter = filters.get('date_filter', 'all')

        today = timezone.now().date()
        if date_filter == 'today':
            start_date = end_date = str(today)
        elif date_filter == 'week':
            start_date = str(today - timedelta(days=7))
            end_date = str(today)
        elif date_filter == 'month':
            start_date = str(today - timedelta(days=30))
            end_date = str(today)

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
            sd = parse_date(start_date)
            ed = parse_date(end_date)
            if sd and ed:
                tickets = tickets.filter(created__date__gte=sd, created__date__lte=ed)

        if status_filter:
            tickets = tickets.filter(status=status_filter)
        if assigned_to_filter:
            tickets = tickets.filter(assigned_to__id=assigned_to_filter)
        if category_filter:
            tickets = tickets.filter(category__id=category_filter)

        # Build CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Info row
        filter_parts = []
        if start_date and end_date:
            filter_parts.append(f"Date: {start_date} to {end_date}")
        if status_filter:
            filter_parts.append(f"Status: {status_filter}")
        if category_filter:
            filter_parts.append(f"Category ID: {category_filter}")
        if assigned_to_filter:
            filter_parts.append(f"Assignee ID: {assigned_to_filter}")
        filter_str = "  |  ".join(filter_parts) if filter_parts else "No filters — all tickets"

        #writer.writerow([f'Ticket Report — Generated: {timezone.now().strftime("%Y-%m-%d %H:%M")}  |  {filter_str}'])
        #writer.writerow([])

        writer.writerow([
            'Ticket ID', 'Interaction ID', 'Title', 'Description', 'Status',
            'Main Category', 'Sub Category', 'Owner', 'Assigned To', 'Waiting For',
            'Created At', 'Last Updated', 'Closed At', 'Resolution Time (mins)',
            'Escalated?', 'Escalation Level', 'Escalation Status',
            'Escalated To', 'Escalated From', 'Escalated At', 'Escalation Acknowledged At',
            'Follow-up Count', 'Attachment Count',
        ])

        for ticket in tickets:
            res_hrs = ''
            if ticket.closed_date:
                res_hrs = round((ticket.closed_date - ticket.created).total_seconds() / 60, 2)

            escalations = list(ticket.escalations.all())
            if escalations:
                e = escalations[0]
                escalated  = 'Yes'
                esc_level  = f'Level {e.escalation_level}'
                esc_status = e.get_status_display()
                esc_to     = str(e.escalated_to_user) if e.escalated_to_user else ''
                esc_from   = str(e.escalated_from_user) if e.escalated_from_user else ''
                esc_at     = e.escalated_at.strftime('%Y-%m-%d %H:%M')
                esc_ack    = e.acknowledged_at.strftime('%Y-%m-%d %H:%M') if e.acknowledged_at else 'Not yet'
            else:
                escalated  = 'No'
                esc_level  = ''
                esc_status = ''
                esc_to = esc_from = esc_at = esc_ack = ''

            writer.writerow([
                f'#{ticket.id}',
                ticket.interaction_id or '',
                ticket.title,
                (ticket.description[:300] + '...') if ticket.description and len(ticket.description) > 300 else (ticket.description or ''),
                ticket.status or '',
                ticket.category.name if ticket.category else '',
                ticket.sub_category.name if ticket.sub_category else '',
                ticket.owner.get_full_name() or ticket.owner.username if ticket.owner else '',
                ticket.assigned_to.get_full_name() or ticket.assigned_to.username if ticket.assigned_to else '',
                ticket.waiting_for.get_full_name() or ticket.waiting_for.username if ticket.waiting_for else '',
                ticket.created.strftime('%Y-%m-%d %H:%M'),
                ticket.updated.strftime('%Y-%m-%d %H:%M'),
                ticket.closed_date.strftime('%Y-%m-%d %H:%M') if ticket.closed_date else '',
                res_hrs or '',
                escalated, esc_level, esc_status,
                esc_to, esc_from, esc_at, esc_ack,
                ticket.followup_set.count(),
                ticket.attachment_set.count(),
            ])

        # Save file
        csv_content = output.getvalue().encode('utf-8')
        filename = f'report_{report.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
        report.file.save(filename, ContentFile(csv_content), save=False)
        report.status = 'DONE'
        report.completed_at = timezone.now()
        report.save(update_fields=['status', 'completed_at', 'file'])

    except Exception as e:
        report.status = 'FAILED'
        report.error = str(e)
        report.save(update_fields=['status', 'error'])