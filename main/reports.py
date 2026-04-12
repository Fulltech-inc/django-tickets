from django.db.models import Count, Q, Avg, F, DurationField
from django.db.models.functions import ExtractDay, TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta
from .models import Ticket, TicketEscalation, User
from django.db.models import Count, Q, Avg, F, DurationField, Case, When, Value, CharField
from django.db.models import Count, Q


class TicketReports:
    
    @staticmethod
    def tickets_by_date_range(start_date, end_date):
        """Tickets created between dates"""
        if start_date and end_date:
            return Ticket.objects.filter(created__date__gte=start_date, created__date__lte=end_date)
        return Ticket.objects.all()
    
    @staticmethod
    def tickets_by_status(status=None):
        """Tickets grouped by status"""
        if status:
            return Ticket.objects.filter(status=status)
        return Ticket.objects.values('status').annotate(count=Count('id')).order_by('status')
    
    @staticmethod
    def tickets_by_department():
        """Tickets grouped by assigned department/user"""
        return Ticket.objects.values('assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name').annotate(
            total=Count('id'),
            open=Count('id', filter=Q(~Q(status='DONE'))),
            closed=Count('id', filter=Q(status='DONE'))
        ).order_by('-total')
    
    @staticmethod
    def average_resolution_time():
        """Average time to close tickets in hours"""
        closed_tickets = Ticket.objects.filter(status='DONE', closed_date__isnull=False)
        if not closed_tickets.exists():
            return None
        total_seconds = sum([(t.closed_date - t.created).total_seconds() for t in closed_tickets])
        avg_hours = total_seconds / closed_tickets.count() / 3600
        return round(avg_hours, 2)
    
    @staticmethod
    def escalated_tickets_report():
        """Tickets that were escalated"""
        return TicketEscalation.objects.select_related('ticket', 'escalated_to_user').values(
            'ticket__id', 'ticket__title', 'escalation_level', 'status', 'escalated_to_user__username'
        ).annotate(escalation_count=Count('id')).order_by('-escalated_at')
    
    @staticmethod
    def sla_breaches(threshold_hours=48):
        """Tickets not closed within threshold"""
        threshold_time = timezone.now() - timedelta(hours=threshold_hours)
        return Ticket.objects.filter(
            created__lte=threshold_time,
            status__in=['TODO', 'IN PROGRESS', 'WAITING']
        ).select_related('assigned_to')
    
    @staticmethod
    def daily_ticket_summary(days=30):
        """Daily ticket creation summary for last N days"""
        start_date = timezone.now().date() - timedelta(days=days)
        return Ticket.objects.filter(created__date__gte=start_date).annotate(
            day=TruncDate('created')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
    
    @staticmethod
    def tickets_by_priority():
        """Tickets grouped by priority (using escalation count as priority)"""
        return Ticket.objects.values('escalation_count').annotate(
            count=Count('id'),
            label=Case(
                When(escalation_count=0, then=Value('Normal')),
                When(escalation_count=1, then=Value('Level 1 Escalated')),
                When(escalation_count=2, then=Value('Level 2 Escalated')),
                default=Value('Unknown'),
                output_field=CharField(),
            )
        )
    
    @staticmethod
    def monthly_summary(year=None):
        """Monthly ticket summary"""
        if not year:
            year = timezone.now().year
        return Ticket.objects.filter(created__year=year).annotate(
            month=TruncMonth('created')
        ).values('month').annotate(
            total=Count('id'),
            closed=Count('id', filter=Q(status='DONE')),
            open=Count('id', filter=Q(~Q(status='DONE')))
        ).order_by('month')
    

@staticmethod
def tickets_by_category():
    """Tickets grouped by category"""
    return Ticket.objects.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')