"""Database models for RetroVision security alerts."""

from django.db import models


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
