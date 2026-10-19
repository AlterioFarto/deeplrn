"""WSGI entrypoint. Defaults to production settings; override DJANGO_SETTINGS_MODULE to change."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_wsgi_application()
