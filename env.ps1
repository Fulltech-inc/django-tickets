$env:DJANGO_SECRET_KEY = "this-is-temporary-and-insecure"
$env:DJANGO_PRODUCTION_DOMAIN = "5.189.181.199:8000"

# log file
$env:DJANGO_LOG_FILE = "C:\Users\SPENCER\Documents\GitHub\django-tickets\log.txt"

# static and media files dir in production
$env:DJANGO_STATIC_ROOT = "C:\Users\SPENCER\Documents\GitHub\django-tickets\staticfiles"
$env:DJANGO_MEDIA_ROOT = "C:\Users\SPENCER\Documents\GitHub\django-tickets\media"

# User who gets django's email notifications (ADMINS/MANAGERS), see settings.py
$env:DJANGO_ADMIN_NAME = "Spencer"
$env:DJANGO_ADMIN_EMAIL = "spencertasatech@gmail.com"

# Django email (SMTP) configuration
$env:DJANGO_EMAIL_HOST = "mail.pinesofttechnologies.co.za"
$env:DJANGO_EMAIL_HOST_USER = "noreply@pinesofttechnologies.co.za"
$env:DJANGO_EMAIL_HOST_PASSWORD = "Xcally#2030"

# ticket email inbox (IMAP)
$env:DJANGO_TICKET_INBOX_SERVER = "mail.pinesofttechnologies.co.za"
$env:DJANGO_TICKET_INBOX_USER = "tickets@pinesofttechnologies.co.za"
$env:DJANGO_TICKET_INBOX_PASSWORD = "Xcally#2030"

# email notifications
$env:DJANGO_TICKET_EMAIL_NOTIFICATIONS_FROM = "noreply@pinesofttechnologies.co.za"
$env:DJANGO_TICKET_EMAIL_NOTIFICATIONS_TO = "admin@pinesofttechnologies.co.za"
