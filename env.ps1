
$env:DJANGO_SECRET_KEY = "this-is-temporary-and-insecure"
$env:DJANGO_PRODUCTION_DOMAIN = "pinesofttechnologies.co.za"

# log file
$env:DJANGO_LOG_FILE = "C:\Users\SPENCER\Documents\GitHub\django-tickets\log.txt"

# static and media files dir in production
$env:DJANGO_STATIC_ROOT = "C:\Users\SPENCER\Documents\GitHub\django-tickets\staticfiles"
$env:DJANGO_MEDIA_ROOT = "C:\Users\SPENCER\Documents\GitHub\django-tickets\media"

# User who gets django's email notifications (ADMINS/MANAGERS), see settings.py
$env:DJANGO_ADMIN_NAME = "Spencer"
$env:DJANGO_ADMIN_EMAIL = "spencertasatech@gmail.com"

# Django email configuration
$env:DJANGO_EMAIL_HOST = "mail.pinesofttechnologies.co.za"
$env:DJANGO_EMAIL_HOST_USER = "dev@pinesofttechnologies.co.za"
$env:DJANGO_EMAIL_HOST_PASSWORD = "Pinesoft#2030"

# ticket email inbox, see 'main/management/commands/get_email.py'
$env:DJANGO_TICKET_INBOX_SERVER = "mail.pinesofttechnologies.co.za"
$env:DJANGO_TICKET_INBOX_USER = "dev@pinesofttechnologies.co.za"
$env:DJANGO_TICKET_INBOX_PASSWORD = "Pinesoft#2030"

# email notifications to admin, see 'main/management/commands/get_email.py'
$env:DJANGO_TICKET_EMAIL_NOTIFICATIONS_FROM = "dev@pinesofttechnologies.co.za"
$env:DJANGO_TICKET_EMAIL_NOTIFICATIONS_TO = "dev@pinesofttechnologies.co.za"