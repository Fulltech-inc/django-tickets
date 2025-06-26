# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import main.models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='file',
            field=models.FileField(verbose_name='File', max_length=1000, upload_to=main.models.attachment_path),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='filename',
            field=models.CharField(verbose_name='Filename', max_length=1000),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='ticket',
            field=models.ForeignKey(verbose_name='Ticket', to='main.Ticket'),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='user',
            field=models.ForeignKey(verbose_name='User', blank=True, null=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='followup',
            name='date',
            field=models.DateTimeField(verbose_name='Date', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='followup',
            name='text',
            field=models.TextField(verbose_name='Text', blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='followup',
            name='ticket',
            field=models.ForeignKey(verbose_name='Ticket', to='main.Ticket'),
        ),
        migrations.AlterField(
            model_name='followup',
            name='title',
            field=models.CharField(verbose_name='Title', max_length=200),
        ),
        migrations.AlterField(
            model_name='followup',
            name='user',
            field=models.ForeignKey(verbose_name='User', blank=True, null=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='assigned_to',
            field=models.ForeignKey(verbose_name='Assigned to', blank=True, null=True, related_name='assigned_to', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='description',
            field=models.TextField(verbose_name='Description', blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='owner',
            field=models.ForeignKey(verbose_name='Owner', blank=True, null=True, related_name='owner', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(verbose_name='Status', max_length=255, blank=True, null=True, choices=[('TODO', 'TODO'), ('IN PROGRESS', 'IN PROGRESS'), ('WAITING', 'WAITING'), ('DONE', 'DONE')]),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='title',
            field=models.CharField(verbose_name='Title', max_length=255),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='waiting_for',
            field=models.ForeignKey(verbose_name='Waiting For', blank=True, null=True, related_name='waiting_for', to=settings.AUTH_USER_MODEL),
        ),
    ]
