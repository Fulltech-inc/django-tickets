@echo off
set DJANGO_ENV=development
start cmd /k "python manage.py runserver"
start cmd /k "python watcher_runner.py"