from .models import TicketActivity

def log_activity(ticket, action, performed_by, from_dept=None, to_dept=None, old_value=None, new_value=None, comment=None):
    """Helper function to log ticket activities"""
    TicketActivity.objects.create(
        ticket=ticket,
        action=action,
        performed_by=performed_by,
        from_department=from_dept,
        to_department=to_dept,
        old_value=old_value,
        new_value=new_value,
        comment=comment
    )