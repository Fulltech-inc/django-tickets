from django.apps import AppConfig
import os
import sys


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # Skip during migrations
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
            
        # Only run in development server, avoid double execution
        if os.environ.get('RUN_MAIN') != 'true' and 'runserver' in sys.argv:
            # Wait a bit for database to be ready
            import time
            time.sleep(3)
            
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            from django.conf import settings

            # Use in-memory scheduler to avoid database locks
            scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
            
            from .escalations import run_escalation_check

            scheduler.add_job(
                run_escalation_check,
                trigger=IntervalTrigger(minutes=1),
                id='run_escalation_check',
                name='Check and escalate stale WAITING tickets',
                replace_existing=True,
                misfire_grace_time=30,
            )

            scheduler.start()
            print("✅ Escalation scheduler started (in-memory mode)")