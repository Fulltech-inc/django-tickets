from django.apps import AppConfig

class MainConfig(AppConfig):
    name = 'main'
    _watcher_started = False

    def ready(self):
        if not MainConfig._watcher_started:
            from main.email_watcher import start_background_email_watcher
            start_background_email_watcher()
            MainConfig._watcher_started = True
