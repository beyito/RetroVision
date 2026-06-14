"""Application configuration for alerts_api."""

from django.apps import AppConfig


class AlertsApiConfig(AppConfig):
    """Django app config for central alert persistence."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "alerts_api"
