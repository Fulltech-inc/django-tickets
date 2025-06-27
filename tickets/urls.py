# -*- coding: utf-8 -*-

from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static

import main.views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Login and logout pages
    url(r'^$', auth_views.login, name='login'),
    url(r'^logout/$', auth_views.logout_then_login, name='logout'),

    # User settings
    url(r'^settings/$', login_required(main.views.usersettings_update_view), name='user-settings'),

    # Django admin
    url(r'^admin/', admin.site.urls),

    # Tickets
    url(r'^ticket/new/$', login_required(main.views.ticket_create_view), name='ticket_new'),
    url(r'^ticket/edit/(?P<pk>\d+)/$', login_required(main.views.ticket_edit_view), name='ticket_edit'),
    url(r'^ticket/(?P<pk>\d+)/$', login_required(main.views.ticket_detail_view), name='ticket_detail'),

    # Followups
    url(r'^followup/new/$', login_required(main.views.followup_create_view), name='followup_new'),
    url(r'^followup/edit/(?P<pk>\d+)/$', login_required(main.views.followup_edit_view), name='followup_edit'),

    # Attachments
    url(r'^attachment/new/$', login_required(main.views.attachment_create_view), name='attachment_new'),

    # Ticket overviews
    url(r'^inbox/$', login_required(main.views.inbox_view), name='inbox'),
    url(r'^my-tickets/$', login_required(main.views.my_tickets_view), name='my-tickets'),
    url(r'^all-tickets/$', login_required(main.views.all_tickets_view), name='all-tickets'),
    url(r'^archive/$', login_required(main.views.archive_view), name='archive'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
