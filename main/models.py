# -*- coding: utf-8 -*-
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.storage import default_storage, FileSystemStorage
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
import logging

logger = logging.getLogger(__name__)


class Category(models.Model):
    name = models.CharField('Category Name', max_length=100)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Ticket(models.Model):
    STATUS_CHOICES = (
        ('TODO', 'TODO'),
        ('IN PROGRESS', 'IN PROGRESS'),
        ('WAITING', 'WAITING'),
        ('DONE', 'DONE'),
    )
    interaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="XCALLY Interaction ID")
    title = models.CharField('Title', max_length=255)
    owner = models.ForeignKey(User, related_name='tickets_owned', null=True, verbose_name='Owner', on_delete=models.SET_NULL)
    description = models.TextField('Description', null=True)
    status = models.CharField('Status', choices=STATUS_CHOICES, max_length=255, blank=True, null=True)
    waiting_for = models.ForeignKey(User, related_name='tickets_waiting_for', blank=True, null=True, verbose_name='Waiting For', on_delete=models.SET_NULL)
    closed_date = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ForeignKey(User, related_name='tickets_assigned_to', null=True, verbose_name='Assigned to', on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    escalation_count = models.IntegerField(default=0)
    last_escalation_check = models.DateTimeField(null=True, blank=True)
    last_escalation_at = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Main Category', related_name='main_tickets',
        limit_choices_to={'parent': None}
    )
    sub_category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Sub Category', related_name='sub_tickets'
    )


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
    safe_filename = filename.replace(' ', '_')
    return f'tickets/{instance.ticket.id}/{safe_filename}'
    


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
    
    @property
    def safe_url(self):
        return self.file.url.replace(' ', '_')


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)


class EscalationConfig(models.Model):
    level1_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='l1_escalations',
        verbose_name='Contact Center Manager (Level 1)',
        help_text='All tickets escalate to this person at Level 1.'
    )
    level2_director = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='l2_escalations',
        verbose_name='Contact Center Director (Level 2)',
        help_text='All tickets escalate to this person at Level 2.'
    )
    level1_minutes = models.IntegerField(
        default=2880,
        verbose_name='Level 1 threshold (minutes)',
        help_text='Minutes since ticket created before Level 1 escalation. Default 2880 = 48hrs.'
    )
    level2_minutes = models.IntegerField(
        default=1440,
        verbose_name='Level 2 threshold (minutes)',
        help_text='Minutes after Level 1 before Level 2 escalation. Default 1440 = 24hrs.'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Escalation Config'
        verbose_name_plural = 'Escalation Config'

    def __str__(self):
        return f"Config — L1:{self.level1_minutes}min ({self.level1_manager}) L2:{self.level2_minutes}min ({self.level2_director})"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


class EscalationRule(models.Model):
    name = models.CharField('Name', max_length=255)
    escalation_level = models.IntegerField('Escalation Level', default=1)
    threshold_hours = models.IntegerField('Threshold (hours)', default=48)
    target_role = models.CharField('Target Role', max_length=255, blank=True, null=True)
    is_active = models.BooleanField('Active', default=True)

    class Meta:
        verbose_name = 'Escalation Rule'
        verbose_name_plural = 'Escalation Rules'
        ordering = ['escalation_level']

    def __str__(self):
        return f"{self.name} (L{self.escalation_level}, {self.threshold_hours}h)"


class TicketEscalation(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('RESOLVED', 'Resolved'),
    )
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='escalations', verbose_name='Ticket')
    escalation_level = models.IntegerField('Escalation Level', default=1)
    escalated_from_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='escalations_sent', verbose_name='Escalated From')
    escalated_to_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='escalations_received', verbose_name='Escalated To')
    escalated_at = models.DateTimeField('Escalated At', default=timezone.now)
    acknowledged_at = models.DateTimeField('Acknowledged At', null=True, blank=True)
    resolved_at = models.DateTimeField('Resolved At', null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notification_sent = models.BooleanField('Notification Sent', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

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


class TicketActivity(models.Model):
    ACTION_CHOICES = (
        ('CREATED', 'Ticket Created'),
        ('ASSIGNED', 'Assigned to Department'),
        ('REASSIGNED', 'Reassigned to Another Department'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('WAITING_FOR', 'Waiting for Input'),
        ('FOLLOWUP_ADDED', 'Followup Added'),
        ('ESCALATED', 'Escalated'),
        ('CLOSED', 'Ticket Closed'),
        ('REOPENED', 'Ticket Reopened'),
        ('ATTACHMENT_ADDED', 'Attachment Added'),
    )
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='performed_activities')
    from_department = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='from_activities')
    to_department = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='to_activities')
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ticket Activity'
        verbose_name_plural = 'Ticket Activities'
    
    def __str__(self):
        return f"{self.action} on Ticket #{self.ticket.id} by {self.performed_by} at {self.created_at}"


class GeneratedReport(models.Model):
    STATUS_CHOICES = (
        ('QUEUED', 'Queued'),
        ('PROCESSING', 'Processing'),
        ('DONE', 'Done'),
        ('FAILED', 'Failed'),
    )
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED')
    filters = models.JSONField(default=dict)  # store what filters were applied
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Generated Report'

    def __str__(self):
        return f"Report #{self.id} by {self.requested_by} — {self.status}"



