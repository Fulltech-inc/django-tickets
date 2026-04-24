# -*- coding: utf-8 -*-

import os
from decouple import config

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = config("DJANGO_SECRET_KEY", "dev-secret-key")

ENV = config("DJANGO_ENV", "development").lower()

# Allowed hosts from environment
raw_hosts = config("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [host.strip() for host in raw_hosts.split(",") if host.strip()]

if ENV == "production":
    DEBUG = False
    # Only set these to True if you're using HTTPS — which you're not (based on http://5.189.181.199:8000 in your original message).
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
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
    'django_apscheduler', 
    'django_cleanup.apps.CleanupConfig',
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
STATIC_ROOT = os.path.join(BASE_DIR, config("DJANGO_STATIC_ROOT", "staticfiles"))
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, config("DJANGO_MEDIA_ROOT", "media"))

# Auth settings
LOGIN_REDIRECT_URL = "/inbox/"
LOGIN_URL = "/"

# Django Crispy Forms
CRISPY_TEMPLATE_PACK = 'bootstrap3'

# Email configuration - Marketmavens
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config("DJANGO_EMAIL_HOST", "")
# EMAIL_PORT = config("DJANGO_EMAIL_SMTP_PORT", "")
# EMAIL_USE_TLS = False
# EMAIL_USE_SSL = True
# EMAIL_HOST_USER = config("DJANGO_EMAIL_HOST_USER", "")
# EMAIL_HOST_PASSWORD = config("DJANGO_EMAIL_HOST_PASSWORD", "")
# EMAIL_TIMEOUT = 10

# Email configuration - POSB
EMAIL_HOST = config("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = config("DJANGO_EMAIL_SMTP_PORT", "")
EMAIL_USE_TLS = False
EMAIL_HOST_USER = config("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = config("DJANGO_EMAIL_HOST_PASSWORD", "")

SITE_BASE_URL = config("SITE_BASE_URL_HOST", "http://127.0.0.1:8000")
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"


# Logging configuration
log_file_path = config("DJANGO_LOG_FILE", os.path.join(BASE_DIR, "log.txt"))

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
            'level': 'DEBUG',
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
