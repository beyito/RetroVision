"""Admin registration for alerts."""

from django.contrib import admin

from .models import Tenant, Store, EdgeNode, Camera, SecurityAlert


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "code", "is_active", "created_at")
    list_filter = ("tenant", "is_active")
    search_fields = ("name", "code", "tenant__name")


@admin.register(EdgeNode)
class EdgeNodeAdmin(admin.ModelAdmin):
    list_display = ("node_id", "display_name", "store", "control_api_base_url", "is_active", "updated_at")
    list_filter = ("store", "is_active")
    search_fields = ("node_id", "display_name", "control_api_base_url", "store__name", "store__tenant__name")
    readonly_fields = ("api_key",)


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    """Admin view for edge camera profiles."""

    list_display = ("camera_id", "display_name", "store", "edge_node", "queue_wait_threshold", "is_active", "updated_at")
    list_filter = ("is_active", "store", "edge_node")
    search_fields = ("camera_id", "display_name", "video_source", "store__name", "store__tenant__name")
    ordering = ("camera_id",)


@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    """Admin view for security alerts."""

    list_display = ("timestamp", "camera_id", "risk_score", "video_path")
    list_filter = ("camera_id", "timestamp")
    search_fields = ("camera_id", "video_path")
    ordering = ("-timestamp",)
