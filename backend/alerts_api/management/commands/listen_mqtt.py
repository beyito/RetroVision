"""MQTT subscriber that persists Edge alert events into PostgreSQL."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from paho.mqtt import client as mqtt

from alerts_api.models import SecurityAlert


LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """Listen to Edge alert events and save them using the Django ORM."""

    help = "Subscribe to retrovision/edge/alerts and retrovision/telemetry and persist records."

    def add_arguments(self, parser: Any) -> None:
        """Add optional MQTT connection arguments."""
        parser.add_argument("--host", default=settings.MQTT_BROKER_HOST)
        parser.add_argument("--port", type=int, default=settings.MQTT_BROKER_PORT)
        parser.add_argument("--topic", default=settings.MQTT_ALERTS_TOPIC)
        parser.add_argument("--telemetry-topic", default=settings.MQTT_TELEMETRY_TOPIC)
        parser.add_argument("--client-id", default="retrovision-core-alerts-api")

    def handle(self, *args: Any, **options: Any) -> None:
        """Start the MQTT network loop forever."""
        host = options["host"]
        port = options["port"]
        topic = options["topic"]
        telemetry_topic = options["telemetry_topic"]
        client_id = options["client_id"]

        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        client.on_connect = self._on_connect(topic, telemetry_topic)
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect

        self.stdout.write(self.style.NOTICE(f"Connecting to MQTT broker {host}:{port}"))
        client.connect(host, port, keepalive=60)
        client.loop_forever(retry_first_connection=True)

    def _on_connect(self, topic: str, telemetry_topic: str):
        """Build an on_connect callback bound to multiple topics."""

        def callback(client: mqtt.Client, userdata: Any, flags: Any, rc: int) -> None:
            if rc == 0:
                self.stdout.write(self.style.SUCCESS("Connected to MQTT broker"))
                client.subscribe([(topic, 1), (telemetry_topic, 1)])
                self.stdout.write(self.style.NOTICE(f"Subscribed to {topic} and {telemetry_topic}"))
                return

            LOGGER.error("MQTT connection failed with rc=%s", rc)

        return callback

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Log MQTT disconnections."""
        if rc != 0:
            LOGGER.warning("Unexpected MQTT disconnection rc=%s", rc)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Persist data from an MQTT JSON payload based on the topic."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic
            
            if topic == settings.MQTT_ALERTS_TOPIC:
                alert = SecurityAlert.objects.create(
                    timestamp=self._parse_timestamp(payload.get("timestamp")),
                    camera_id=str(payload["camera_id"]),
                    risk_score=float(payload["risk_score"]),
                    rules_triggered=self._parse_rules(payload.get("rules_triggered")),
                    video_path=payload.get("video_path") or None,
                )
                LOGGER.info("SecurityAlert saved id=%s camera_id=%s", alert.id, alert.camera_id)
                
                # Broadcast to channels group
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        "security_alerts",
                        {
                            "type": "alert_message",
                            "alert": {
                                "id": alert.id,
                                "timestamp": alert.timestamp.isoformat(),
                                "camera_id": alert.camera_id,
                                "risk_score": alert.risk_score,
                                "rules_triggered": alert.rules_triggered,
                                "video_path": alert.video_path,
                                "created_at": alert.created_at.isoformat() if alert.created_at else None,
                            }
                        }
                    )
                    LOGGER.info("SecurityAlert broadcasted to WebSocket group")
            elif topic == settings.MQTT_TELEMETRY_TOPIC:
                from alerts_api.models import Telemetria_Afluencia, Heatmaps
                timestamp = self._parse_timestamp(payload.get("timestamp"))
                camera_id = str(payload["camera_id"])
                
                # Create telemetry record
                personas_entrantes = int(payload.get("personas_entrantes", 0))
                personas_salientes = int(payload.get("personas_salientes", 0))
                personas_en_cola = int(payload.get("personas_en_cola", 0))
                tiempo_espera_promedio = float(payload.get("tiempo_espera_promedio", 0.0))
                
                telemetry = Telemetria_Afluencia.objects.create(
                    timestamp=timestamp,
                    camera_id=camera_id,
                    personas_entrantes=personas_entrantes,
                    personas_salientes=personas_salientes,
                    personas_en_cola=personas_en_cola,
                    tiempo_espera_promedio=tiempo_espera_promedio,
                )
                LOGGER.info("Telemetria_Afluencia saved id=%s camera_id=%s", telemetry.id, telemetry.camera_id)
                
                # Create heatmap record
                heatmap_points = payload.get("heatmap_points", [])
                heatmap = Heatmaps.objects.create(
                    timestamp=timestamp,
                    camera_id=camera_id,
                    coordenadas_json={"points": heatmap_points},
                )
                LOGGER.info("Heatmap saved id=%s camera_id=%s", heatmap.id, heatmap.camera_id)
        except KeyError as exc:
            LOGGER.warning("MQTT message missing required field: %s", exc)
        except json.JSONDecodeError:
            LOGGER.warning("Invalid JSON payload on topic %s", msg.topic)
        except Exception:
            LOGGER.exception("Failed to persist MQTT message")

    def _parse_timestamp(self, raw_timestamp: Any):
        """Parse an ISO-8601 timestamp or return the current time."""
        if not raw_timestamp:
            return timezone.now()

        parsed = parse_datetime(str(raw_timestamp))
        if parsed is None:
            return timezone.now()

        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())

        return parsed

    def _parse_rules(self, raw_rules: Any) -> list[str]:
        """Normalize rules_triggered to a list of strings."""
        if raw_rules is None:
            return []
        if isinstance(raw_rules, list):
            return [str(rule) for rule in raw_rules]
        return [str(raw_rules)]
