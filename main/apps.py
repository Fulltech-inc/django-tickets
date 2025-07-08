# main/apps.py
import os
from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        if os.environ.get("DJANGO_ENV") != "production":
            from .email_watcher import start_background_email_watcher
            if os.environ.get("RUN_MAIN") == "true":
                print("[✓] Email watcher thread started by main app ready method")
                start_background_email_watcher()
