# -*- coding: utf-8 -*-
# main/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Ticket, FollowUp, Attachment, EscalationRule, TicketEscalation, UserProfile, EscalationConfig, Category



class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profile'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(EscalationConfig)
class EscalationConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'level1_manager', 'level2_director', 'level1_minutes', 'level2_minutes', 'is_active']
    list_editable = ['level1_minutes', 'level2_minutes', 'is_active']
    fieldsets = (
        ('Escalation Targets', {
            'fields': ('level1_manager', 'level2_director'),
            'description': 'Set the Contact Center Manager and Director for all escalations.'
        }),
        ('Time Thresholds', {
            'fields': ('level1_minutes', 'level2_minutes'),
            'description': 'Set time in minutes. 2880 = 48hrs, 1440 = 24hrs.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'escalation_level', 'threshold_hours', 'target_role', 'is_active')
    list_filter = ('is_active', 'escalation_level')


@admin.register(TicketEscalation)
class TicketEscalationAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'escalation_level', 'escalated_from_user', 'escalated_to_user', 'escalated_at', 'status', 'notification_sent')
    list_filter = ('status', 'escalation_level')
    search_fields = ('ticket__title', 'escalated_to_user__username')
    readonly_fields = ('escalated_at', 'acknowledged_at', 'resolved_at')
    ordering = ('-escalated_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'category', 'assigned_to', 'escalation_count', 'last_escalation_at', 'created')
    list_filter = ('status', 'category')
    search_fields = ('title', 'interaction_id')


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'title', 'user', 'created')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'filename', 'user', 'created')

from .models import Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('parent', 'is_active')
    search_fields = ('name',)