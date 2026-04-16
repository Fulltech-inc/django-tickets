from django.apps import AppConfig
import sys
import os
import atexit


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return

        # Prevent double-start from Django's auto-reloader
        if os.environ.get('RUN_MAIN') != 'true':
            return

        