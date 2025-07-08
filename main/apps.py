from django.apps import AppConfig

_watcher_started = False  # Global module-level flag

class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        global _watcher_started
        if not _watcher_started:
            from main.email_watcher import start_background_email_watcher

            try:
                start_background_email_watcher()
                print("[✓] Email watcher thread started")
            except Exception as e:
                print(f"[✗] Email watcher failed to start: {e}")

            _watcher_started = True
