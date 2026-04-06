from django.db.models import Count, Q, Avg, F, DurationField
from django.db.models.functions import ExtractDay, TruncDate
from django.utils import timezone
from datetime import timedelta
from .models import Ticket, TicketEscalation, User

class TicketReports:
    
    @staticmethod
    def tickets_by_date_range(start_date, end_date):
        """Tickets created between dates"""
        return Ticket.objects.filter(created__date__gte=start_date, created__date__lte=end_date)
    
    @staticmethod
    def tickets_by_status(status=None):
        """Tickets grouped by status"""
        if status:
            return Ticket.objects.filter(status=status)
        return Ticket.objects.values('status').annotate(count=Count('id'))
    
    @staticmethod
    def tickets_by_department():
        """Tickets grouped by assigned department/user"""
        return Ticket.objects.values('assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name').annotate(
            total=Count('id'),
            open=Count('id', filter=Q(~Q(status='DONE'))),
            closed=Count('id', filter=Q(status='DONE'))
        )
    
    @staticmethod
    def average_resolution_time():
        """Average time to close tickets"""
        closed_tickets = Ticket.objects.filter(status='DONE', closed_date__isnull=False)
        if not closed_tickets:
            return None
        total_time = sum([(t.closed_date - t.created).total_seconds() for t in closed_tickets])
        avg_seconds = total_time / closed_tickets.count()
        return timedelta(seconds=avg_seconds)
    
    @staticmethod
    def escalated_tickets_report():
        """Tickets that were escalated"""
        return TicketEscalation.objects.values('ticket__id', 'ticket__title', 'escalation_level', 'status').annotate(
            escalation_count=Count('id')
        )
    
    @staticmethod
    def sla_breaches(threshold_hours=48):
        """Tickets not closed within threshold"""
        threshold_time = timezone.now() - timedelta(hours=threshold_hours)
        return Ticket.objects.filter(
            created__lte=threshold_time,
            status__in=['TODO', 'IN PROGRESS', 'WAITING']
        )
    
    @staticmethod
    def daily_ticket_summary(days=30):
        """Daily ticket creation summary for last N days"""
        start_date = timezone.now().date() - timedelta(days=days)
        return Ticket.objects.filter(created__date__gte=start_date).annotate(
            day=TruncDate('created')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')