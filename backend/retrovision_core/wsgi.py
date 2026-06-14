"""WSGI config for RetroVision Core."""

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "retrovision_core.settings")

application = get_wsgi_application()
