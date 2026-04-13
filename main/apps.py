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

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from django.conf import settings

            scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

            from .escalations import run_escalation_check

            scheduler.add_job(
                run_escalation_check,
                trigger=IntervalTrigger(minutes=2),
                id='run_escalation_check',
                name='Escalation check',
                replace_existing=True,
                coalesce=True,
                max_instances=1,
                misfire_grace_time=60,
                kwargs={'base_url': 'http://127.0.0.1:8000'},
            )

            scheduler.start()
            atexit.register(lambda: scheduler.shutdown(wait=False))  # Clean shutdown
            print("Escalation scheduler started.")

        except Exception as e:
            print(f"Escalation scheduler failed to start: {e}")