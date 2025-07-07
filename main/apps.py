from django.apps import AppConfig
import os
import sys

class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        from main.email_watcher import start_background_email_watcher

        # Run only in main process, not migrations, shell, or Celery worker
        if (
            os.environ.get("RUN_MAIN") == "true"  # dev mode: runserver autoreload check
            or "gunicorn" in sys.argv[0]          # prod mode: e.g., gunicorn
        ):
            start_background_email_watcher()
