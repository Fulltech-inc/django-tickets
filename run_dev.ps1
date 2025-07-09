$env:DJANGO_ENV = "development"
Start-Process powershell -ArgumentList "python watcher_runner.py"
Start-Process powershell -ArgumentList "python manage.py runserver"