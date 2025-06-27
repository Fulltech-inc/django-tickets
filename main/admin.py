from django.contrib import admin
from .models import Ticket, FollowUp, Attachment


class FollowUpInline(admin.TabularInline):
    model = FollowUp
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'assigned_to', 'status', 'created', 'updated')
    search_fields = ('title', 'description', 'assigned_to__username', 'owner__username')
    list_filter = ('status', 'assigned_to', 'owner')
    ordering = ('-created',)
    inlines = [FollowUpInline, AttachmentInline]


admin.site.register(Ticket, TicketAdmin)
admin.site.register(FollowUp)
admin.site.register(Attachment)
