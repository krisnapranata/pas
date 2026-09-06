"""
Django settings development (laptop).

Jalankan dengan:
    DJANGO_SETTINGS_MODULE=config.settings.development python manage.py runserver

atau set DJANGO_ENV=development di .env / environment.
"""

from .base import *  # noqa: F403
from .base import os  # noqa: F401

DEBUG = True

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# Email ke console selama development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
