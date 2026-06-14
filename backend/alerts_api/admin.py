"""Admin registration for alerts."""

from django.contrib import admin

from .models import SecurityAlert


@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    """Admin view for security alerts."""

    list_display = ("timestamp", "camera_id", "risk_score", "video_path")
    list_filter = ("camera_id", "timestamp")
    search_fields = ("camera_id", "video_path")
    ordering = ("-timestamp",)
