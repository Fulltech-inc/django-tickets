# main/management/commands/run_escalation.py
from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
import atexit
import sys
import signal


class Command(BaseCommand):
    help = 'Runs the escalation check scheduler manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=2,
            help='Interval in minutes between escalation checks (default: 2)',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run escalation check once and exit (no scheduler)',
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        # Using SITE_BASE_URL from settings.py
        base_url = settings.SITE_BASE_URL

        if run_once:
            self.run_single_check(base_url)
            return

        self.run_scheduler(interval, base_url)

    def run_single_check(self, base_url):
        """Run escalation check once and exit"""
        self.stdout.write("Running escalation check once...")
        from main.escalations import run_escalation_check
        run_escalation_check(base_url=base_url)
        self.stdout.write(self.style.SUCCESS("Escalation check completed."))

    def run_scheduler(self, interval, base_url):
        """Start the background scheduler"""
        from main.escalations import run_escalation_check

        self.stdout.write(f"Starting escalation scheduler (interval={interval} minutes)")
        self.stdout.write(f"Base URL: {base_url}")
        
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

        scheduler.add_job(
            run_escalation_check,
            trigger=IntervalTrigger(minutes=interval),
            id='run_escalation_check',
            name='Escalation check',
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=60,
            kwargs={'base_url': base_url},
        )

        scheduler.start()
        self.stdout.write(self.style.SUCCESS(f"Scheduler started. Running every {interval} minute(s)."))
        self.stdout.write("Press Ctrl+C to stop.")

        # Handle shutdown gracefully
        def shutdown_scheduler(signum=None, frame=None):
            self.stdout.write("\nShutting down scheduler...")
            scheduler.shutdown(wait=False)
            sys.exit(0)

       
        signal.signal(signal.SIGTERM, shutdown_scheduler)
        signal.signal(signal.SIGINT, shutdown_scheduler)

        # Keep the command running
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            shutdown_scheduler()