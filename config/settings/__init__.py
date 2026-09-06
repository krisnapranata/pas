"""
Package settings — pick environment berdasarkan DJANGO_ENV.

Untuk kompatibilitas, impor `config.settings` tetap jalan dengan memilih
environment default lewat DJANGO_ENV (default: development di laptop).
"""

import os

ENV = os.getenv("DJANGO_ENV", os.getenv("DJANGO_SETTINGS_MODULE", "development"))

if "production" in ENV.lower():
    from .production import *  # noqa: F403
else:
    from .development import *  # noqa: F403
