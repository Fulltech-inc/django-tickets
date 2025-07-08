"""
Django settings.py - Fully portable, python-dotenv enabled, environment-based configuration
Compatible with: Python 3.6+, Django 1.11.29
"""

import os
import socket
from dotenv import load_dotenv

# Load .env file from BASE_DIR
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Basic environment configuration
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")
ENV = os.environ.get("DJANGO_ENV", "development").lower()

# Allowed Hosts
raw_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(",") if host.strip()]
if ENV == "development" and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
if ENV == "production" and not ALLOWED_HOSTS:
    raise Exception("DJANGO_ALLOWED_HOSTS must be set in production environment.")

# Debug mode toggle
DEBUG = ENV != "production"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Installed apps
INSTALLED_APPS = (
    'main.apps.MainConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
)

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Middleware
MIDDLEWARE_CLASSES = (
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'tickets.urls'
WSGI_APPLICATION = 'tickets.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Helper to resolve environment paths relative to BASE_DIR
def resolve_env_path(key, default_filename):
    path = os.environ.get(key, default_filename)
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return path

# Static & media files
STATIC_URL = '/static/'
STATIC_ROOT = resolve_env_path("DJANGO_STATIC_ROOT", "staticfiles")
MEDIA_URL = '/media/'
MEDIA_ROOT = resolve_env_path("DJANGO_MEDIA_ROOT", "media")
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

# Authentication redirects
LOGIN_REDIRECT_URL = "/inbox/"
LOGIN_URL = "/"

# Django Crispy Forms
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Admin contacts
admin_name = os.environ.get("DJANGO_ADMIN_NAME")
admin_email = os.environ.get("DJANGO_ADMIN_EMAIL")
ADMINS = [(admin_name, admin_email)] if admin_name and admin_email else []
MANAGERS = ADMINS

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Logging
log_file_path = resolve_env_path("DJANGO_LOG_FILE", "log.txt")
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': log_file_path,
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'main': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    }
}
