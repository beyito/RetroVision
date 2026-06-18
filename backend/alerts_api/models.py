"""Database models for RetroVision security alerts."""

import secrets

from django.db import models


def generate_api_key() -> str:
    """Genera API keys estables para edge nodes."""
    return secrets.token_urlsafe(32)


class Tenant(models.Model):
    """Customer company that owns one or more stores."""

    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Store(models.Model):
    """Physical store or branch belonging to a tenant."""

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="stores")
    name = models.CharField(max_length=128)
    code = models.SlugField(max_length=128, unique=True)
    address = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tenant__name", "name"]
        unique_together = [("tenant", "name")]

    def __str__(self) -> str:
        return f"{self.tenant.name} / {self.name}"


class EdgeNode(models.Model):
    """Trusted edge node installed in a store."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="edge_nodes")
    node_id = models.CharField(max_length=128, unique=True, db_index=True)
    display_name = models.CharField(max_length=128, blank=True, default="")
    control_api_base_url = models.CharField(max_length=255, blank=True, default="http://host.docker.internal:8081")
    api_key = models.CharField(max_length=128, unique=True, editable=False, default=generate_api_key)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["node_id"]

    @property
    def is_authenticated(self) -> bool:
        """Compatibilidad con permisos DRF basados en usuario autenticado."""
        return True

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.display_name or self.node_id


class Camera(models.Model):
    """Camera profile used by edge nodes and dashboards."""

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="cameras",
        null=True,
        blank=True,
    )
    edge_node = models.ForeignKey(
        EdgeNode,
        on_delete=models.SET_NULL,
        related_name="cameras",
        null=True,
        blank=True,
    )
    camera_id = models.CharField(max_length=128, unique=True, db_index=True)
    display_name = models.CharField(max_length=128, blank=True, default="")
    video_source = models.CharField(max_length=512, blank=True, default="")
    roi_polygon = models.JSONField(default=list, blank=True)
    queue_wait_threshold = models.FloatField(default=5.0)
    queue_roi_polygon = models.JSONField(default=list, blank=True)
    queue_dwell_seconds = models.FloatField(default=2.0)
    queue_alert_people_threshold = models.PositiveIntegerField(default=3)
    queue_alert_duration_seconds = models.FloatField(default=5.0)
    max_allowed_wait_seconds = models.FloatField(default=120.0)
    cashier_count = models.PositiveIntegerField(default=1)
    service_rate_per_cashier_per_minute = models.FloatField(default=12.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["camera_id"]
        indexes = [
            models.Index(fields=["store", "camera_id"], name="alerts_api__store_i_9f5ee7_idx"),
        ]

    def __str__(self) -> str:
        return self.display_name or self.camera_id


class SecurityAlert(models.Model):
    """Security alert emitted by an Edge camera node.

    Attributes:
        timestamp: Event timestamp reported by the Edge service or assigned by Django.
        camera_id: Stable identifier of the source camera.
        risk_score: Risk score in the inclusive range [0.0, 1.0].
        rules_triggered: Rule names that contributed to the alert.
        video_path: Optional local path or URI to the generated alert clip.
    """

    timestamp = models.DateTimeField(db_index=True)
    camera_id = models.CharField(max_length=128, db_index=True)
    risk_score = models.FloatField()
    rules_triggered = models.JSONField(default=list, blank=True)
    video_path = models.CharField(max_length=512, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Model metadata."""

        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["camera_id", "-timestamp"]),
            models.Index(fields=["-risk_score"]),
        ]

    def __str__(self) -> str:
        """Return a readable alert representation."""
        return f"{self.camera_id} | {self.risk_score:.2f} | {self.timestamp.isoformat()}"


class Telemetria_Afluencia(models.Model):
    """Store customer traffic flow data from cameras."""
    timestamp = models.DateTimeField(db_index=True)
    camera_id = models.CharField(max_length=128, db_index=True)
    personas_entrantes = models.IntegerField(default=0)
    personas_salientes = models.IntegerField(default=0)
    personas_en_cola = models.IntegerField(default=0)
    tiempo_espera_promedio = models.FloatField(default=0.0)
    tiempo_espera_estimado = models.FloatField(default=0.0)
    presion_cola_ratio = models.FloatField(default=0.0)
    alerta_cola_activa = models.BooleanField(default=False)
    motivo_alerta_cola = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.camera_id} | In: {self.personas_entrantes} | Out: {self.personas_salientes} | {self.timestamp.isoformat()}"


class Heatmaps(models.Model):
    """Store raw or generated heat matrix coordinate data."""
    timestamp = models.DateTimeField(db_index=True)
    camera_id = models.CharField(max_length=128, db_index=True)
    coordenadas_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.camera_id} | Heatmap | {self.timestamp.isoformat()}"
