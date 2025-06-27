from django.apps import AppConfig
import os

class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        from main.email_watcher import start_background_email_watcher
        # Ensure this only runs in the main process, not the autoreloader
        if os.environ.get("RUN_MAIN") == "true":
            start_background_email_watcher()
