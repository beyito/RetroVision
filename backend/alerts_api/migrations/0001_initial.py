"""Initial schema for alerts_api."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Create the SecurityAlert model."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SecurityAlert",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("camera_id", models.CharField(db_index=True, max_length=128)),
                ("risk_score", models.FloatField()),
                ("rules_triggered", models.JSONField(blank=True, default=list)),
                ("video_path", models.CharField(blank=True, max_length=512, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["camera_id", "-timestamp"],
                        name="alerts_api_camera__2d9fd6_idx",
                    ),
                    models.Index(fields=["-risk_score"], name="alerts_api_risk_sc_221995_idx"),
                ],
            },
        ),
    ]
