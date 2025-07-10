# -*- coding: utf-8 -*-

import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key")

ENV = os.environ.get("DJANGO_ENV", "development").lower()

# Allowed hosts from environment
raw_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(",") if host.strip()]

if ENV == "production":
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    DEBUG = True
    if not ALLOWED_HOSTS:
        ALLOWED_HOSTS = ["*"]

if ENV == "production" and not ALLOWED_HOSTS:
    raise Exception("DJANGO_ALLOWED_HOSTS must be set in production environment.")

# Use BigAutoField as the default primary key type everywhere unless overridden
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Application definition
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

MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tickets.urls'

WSGI_APPLICATION = 'tickets.wsgi.application'

# Database configuration
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
USE_TZ = True
# USE_L10N is deprecated in Django 5.0+ but harmless if left in
USE_L10N = True

# Static and media files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, os.environ.get("DJANGO_STATIC_ROOT", "staticfiles"))
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, os.environ.get("DJANGO_MEDIA_ROOT", "media"))

# Auth settings
LOGIN_REDIRECT_URL = "/inbox/"
LOGIN_URL = "/"

# Django Crispy Forms
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Admins & Managers
admin_name = os.environ.get("DJANGO_ADMIN_NAME")
admin_email = os.environ.get("DJANGO_ADMIN_EMAIL")
ADMINS = [(admin_name, admin_email)] if admin_name and admin_email else []
MANAGERS = [(admin_name, admin_email)] if admin_name and admin_email else []

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_NOTIFICATIONS_TO = os.environ.get("DJANGO_TICKET_EMAIL_NOTIFICATIONS_TO", "")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
DEFAULT_NOTIFICATIONS_TO_EMAIL = EMAIL_NOTIFICATIONS_TO

# Logging configuration
log_file_path = os.environ.get("DJANGO_LOG_FILE", os.path.join(BASE_DIR, "log.txt"))

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
