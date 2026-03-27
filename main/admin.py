 #main/admin.py

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Ticket, FollowUp, Attachment,
    EscalationRule, TicketEscalation,
    UserProfile, EscalationConfig,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Escalation Settings'
    fields = ('level1_target', 'level2_target')
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(EscalationConfig)
class EscalationConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'level1_minutes', 'level2_minutes', 'is_active']
    list_editable = ['level1_minutes', 'level2_minutes', 'is_active']
    
    fieldsets = (
        ('Escalation Time Thresholds', {
            'fields': ('level1_minutes', 'level2_minutes'),
            'description': 'Set time in minutes for escalation levels'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

# ── EscalationRule ────────────────────────────────────────────
@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'escalation_level', 'threshold_hours', 'target_role', 'is_active')
    list_filter = ('is_active', 'escalation_level')


# ── TicketEscalation ──────────────────────────────────────────
@admin.register(TicketEscalation)
class TicketEscalationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'ticket', 'escalation_level',
        'escalated_from_user', 'escalated_to_user',
        'escalated_at', 'status', 'notification_sent'
    )
    list_filter = ('status', 'escalation_level')
    search_fields = ('ticket__title', 'escalated_to_user__username')
    readonly_fields = ('escalated_at', 'acknowledged_at', 'resolved_at')
    ordering = ('-escalated_at',)


# ── Existing models ───────────────────────────────────────────
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'status', 'assigned_to',
        'escalation_count', 'last_escalation_at', 'created'
    )
    list_filter = ('status',)
    search_fields = ('title',)


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'title', 'user', 'created')


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'filename', 'user', 'created')