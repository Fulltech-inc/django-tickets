from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.storage import default_storage, FileSystemStorage
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import os


class Ticket(models.Model):
    STATUS_CHOICES = (
        ('TODO', 'TODO'),
        ('IN PROGRESS', 'IN PROGRESS'),
        ('WAITING', 'WAITING'),
        ('DONE', 'DONE'),
    )

    title = models.CharField('Title', max_length=255)
    owner = models.ForeignKey(
        User,
        related_name='tickets_owned',
        null=True,
        verbose_name='Owner',
        on_delete=models.SET_NULL
    )
    description = models.TextField('Description', null=True)
    status = models.CharField(
        'Status',
        choices=STATUS_CHOICES,
        max_length=255,
        blank=True,
        null=True
    )
    waiting_for = models.ForeignKey(
        User,
        related_name='tickets_waiting_for',
        blank=True,
        null=True,
        verbose_name='Waiting For',
        on_delete=models.SET_NULL
    )
    closed_date = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User,
        related_name='tickets_assigned_to',
        null=True,
        verbose_name='Assigned to',
        on_delete=models.SET_NULL
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Escalation tracking fields
    escalation_count = models.IntegerField(default=0)
    last_escalation_check = models.DateTimeField(null=True, blank=True)
    last_escalation_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{self.id}: {self.title}"


class FollowUp(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, verbose_name='Ticket')
    date = models.DateTimeField('Date', default=timezone.now)
    title = models.CharField('Title', max_length=200)
    text = models.TextField('Text', blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='User')
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-modified']

    def __str__(self):
        return f"FollowUp #{self.id} on Ticket #{self.ticket.id}"


def attachment_path(instance, filename):
    path = f'tickets/{instance.ticket.id}'
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    if isinstance(default_storage, FileSystemStorage) and not os.path.exists(full_path):
        os.makedirs(full_path, 0o777)
    return os.path.join(path, filename)


class Attachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, verbose_name='Ticket')
    file = models.FileField('File', upload_to=attachment_path, max_length=1000)
    filename = models.CharField('Filename', max_length=1000)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, verbose_name='User')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'
        ordering = ['filename']

    def __str__(self):
        return f"Attachment #{self.id} - {self.filename}"


# ── UserProfile ───────────────────────────────────────────────

# main/models.py - UserProfile (has targets) and EscalationConfig (has thresholds only)

class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    level1_target = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='level1_escalations_received',
        verbose_name='Level 1 Escalation Target',
        help_text='Who this user escalates to at Level 1'
    )
    level2_target = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='level2_escalations_received',
        verbose_name='Level 2 Escalation Target',
        help_text='Who this user escalates to at Level 2'
    )

    def __str__(self):
        return f"Profile of {self.user.username}"


class EscalationConfig(models.Model):
    level1_minutes = models.IntegerField(
        default=2880,
        verbose_name='Level 1 threshold (minutes)',
        help_text='Minutes before Level 1 escalation'
    )
    level2_minutes = models.IntegerField(
        default=1440,
        verbose_name='Level 2 threshold (minutes)',
        help_text='Minutes before Level 2 escalation'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Escalation Config'
        verbose_name_plural = 'Escalation Config'

    def __str__(self):
        return f"Escalation Config - L1:{self.level1_minutes}min, L2:{self.level2_minutes}min"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()



@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)


# ── EscalationConfig ──────────────────────────────────────────


class EscalationConfig(models.Model):
    level1_minutes = models.IntegerField(
        default=2880,
        verbose_name='Level 1 threshold (minutes)',
        help_text='Minutes a WAITING ticket is untouched before Level-1 escalation'
    )
    level2_minutes = models.IntegerField(
        default=1440,
        verbose_name='Level 2 threshold (minutes)',
        help_text='Minutes after Level-1 before Level-2 escalation'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Escalation Config'
        verbose_name_plural = 'Escalation Config'

    def __str__(self):
        return f"Escalation Config - L1:{self.level1_minutes}min, L2:{self.level2_minutes}min"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


# ── EscalationRule ────────────────────────────────────────────

class EscalationRule(models.Model):
    name = models.CharField('Name', max_length=255)
    escalation_level = models.IntegerField('Escalation Level', default=1)
    threshold_hours = models.IntegerField(
        'Threshold (hours)',
        default=48,
        help_text='Hours before this rule triggers.'
    )
    target_role = models.CharField(
        'Target Role',
        max_length=255,
        blank=True,
        null=True,
        help_text='Optional: role/group name to escalate to.'
    )
    is_active = models.BooleanField('Active', default=True)

    class Meta:
        verbose_name = 'Escalation Rule'
        verbose_name_plural = 'Escalation Rules'
        ordering = ['escalation_level']

    def __str__(self):
        return f"{self.name} (L{self.escalation_level}, {self.threshold_hours}h)"


# ── TicketEscalation ──────────────────────────────────────────

class TicketEscalation(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    )

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='escalations',
        verbose_name='Ticket'
    )
    escalation_level = models.IntegerField('Escalation Level', default=1)
    escalated_from_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='escalations_sent',
        verbose_name='Escalated From'
    )
    escalated_to_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='escalations_received',
        verbose_name='Escalated To'
    )
    escalated_at = models.DateTimeField('Escalated At', default=timezone.now)
    acknowledged_at = models.DateTimeField('Acknowledged At', null=True, blank=True)
    resolved_at = models.DateTimeField('Resolved At', null=True, blank=True)
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    notification_sent = models.BooleanField('Notification Sent', default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # ADD THIS LINE

    class Meta:
        verbose_name = 'Ticket Escalation'
        verbose_name_plural = 'Ticket Escalations'
        ordering = ['-escalated_at']

    def __str__(self):
        return f"Escalation L{self.escalation_level} on Ticket #{self.ticket.id} ({self.status})"

    def acknowledge(self, user):
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['status', 'acknowledged_at'])

    def resolve(self):
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])