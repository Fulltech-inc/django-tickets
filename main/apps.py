# main/apps.py
import os
from django.apps import AppConfig

# ✅ Global flag — module level
email_watcher_started = False

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        global email_watcher_started

        if os.environ.get("DJANGO_ENV") != "production" and not email_watcher_started:
            from .email_watcher import start_background_email_watcher
            print("[✓] Email watcher thread started by main app ready method")
            start_background_email_watcher()
            email_watcher_started = True
