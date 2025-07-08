# -*- coding: utf-8 -*-

from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.contrib.auth import views as auth_views

import main.views

urlpatterns = [
    # Login and logout pages
    path('', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # User settings
    path('settings/', login_required(main.views.usersettings_update_view), name='user-settings'),

    # Django admin
    path('admin/', admin.site.urls),

    # Tickets
    path('ticket/new/', login_required(main.views.ticket_create_view), name='ticket_new'),
    re_path(r'^ticket/edit/(?P<pk>\d+)/$', login_required(main.views.ticket_edit_view), name='ticket_edit'),
    re_path(r'^ticket/(?P<pk>\d+)/$', login_required(main.views.ticket_detail_view), name='ticket_detail'),

    # Followups
    path('followup/new/', login_required(main.views.followup_create_view), name='followup_new'),
    re_path(r'^followup/edit/(?P<pk>\d+)/$', login_required(main.views.followup_edit_view), name='followup_edit'),

    # Attachments
    path('attachment/new/', login_required(main.views.attachment_create_view), name='attachment_new'),

    # Ticket overviews
    path('inbox/', login_required(main.views.inbox_view), name='inbox'),
    path('my-tickets/', login_required(main.views.my_tickets_view), name='my-tickets'),
    path('all-tickets/', login_required(main.views.all_tickets_view), name='all-tickets'),
    path('archive/', login_required(main.views.archive_view), name='archive'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
