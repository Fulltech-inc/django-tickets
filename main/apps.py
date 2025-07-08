# main/apps.py
import os
from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # Only run this in the main process, not Django's autoreloader
        if os.environ.get('RUN_MAIN') == 'true':
            from main.email_watcher import start_background_email_watcher
            start_background_email_watcher()
            print("[✓] Email watcher thread started by main app ready method")
