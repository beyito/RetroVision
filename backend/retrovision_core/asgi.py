"""ASGI config for RetroVision Core."""

import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "retrovision_core.settings")

application = get_asgi_application()
