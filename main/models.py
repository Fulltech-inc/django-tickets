from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.storage import default_storage, FileSystemStorage
import os
from django.conf import settings


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
        blank=True,
        null=True,
        verbose_name='Owner'
    )
    description = models.TextField('Description', blank=True, null=True)
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
        verbose_name='Waiting For'
    )
    closed_date = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ForeignKey(
        User,
        related_name='tickets_assigned_to',
        blank=True,
        null=True,
        verbose_name='Assigned to'
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

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
