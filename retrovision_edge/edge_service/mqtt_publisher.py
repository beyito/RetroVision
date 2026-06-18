"""MQTT publisher for lightweight alert events."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from paho.mqtt import client as mqtt


class AlertPublisher:
    """Publishes security alerts to the central RetroVision MQTT topic.

    The publisher is intentionally best-effort. Connection and publish failures
    are logged, but they never raise into the video processing pipeline.
    """

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        client_id: str = "retrovision-edge-01",
        topic: str = "retrovision/edge/alerts",
        telemetry_topic: str = "retrovision/telemetry",
        keep_alive: int = 60,
        enabled: bool = True,
    ) -> None:
        """Initialize the MQTT publisher.

        Args:
            broker_host: MQTT broker host.
            broker_port: MQTT broker port.
            client_id: MQTT client identifier for this Edge node.
            topic: Topic where alert events are published.
            telemetry_topic: Topic where telemetry events are published.
            keep_alive: MQTT keepalive in seconds.
            enabled: If False, publishing becomes a no-op.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.topic = topic
        self.telemetry_topic = telemetry_topic
        self.keep_alive = keep_alive
        self.enabled = enabled

        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._lock = threading.Lock()

        if self.enabled:
            self._connect()

    def _connect(self) -> None:
        """Connect to the MQTT broker using a background network loop."""
        try:
            self._client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.connect(self.broker_host, self.broker_port, self.keep_alive)
            self._client.loop_start()
            self.logger.info(
                "AlertPublisher connected to %s:%s topic=%s",
                self.broker_host,
                self.broker_port,
                self.topic,
            )
        except Exception as exc:
            self._connected = False
            self.logger.warning("MQTT publisher unavailable: %s", exc)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        rc: int,
    ) -> None:
        """Handle MQTT connection result."""
        self._connected = rc == 0
        if not self._connected:
            self.logger.warning("MQTT publisher connection failed rc=%s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        """Track MQTT disconnections."""
        self._connected = False
        if rc != 0:
            self.logger.warning("MQTT publisher disconnected unexpectedly rc=%s", rc)

    def publish_alert(
        self,
        camera_id: str,
        risk_score: float,
        rules_triggered: Sequence[str],
        video_path: Optional[Path | str] = None,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Publish a security alert event.

        Args:
            camera_id: Stable identifier of the source camera.
            risk_score: Risk score in the inclusive range [0.0, 1.0].
            rules_triggered: Names of triggered rules.
            video_path: Optional local path or URI for the alert clip.
            timestamp: Event timestamp. Defaults to current UTC time.

        Returns:
            True if the publish call was accepted by the MQTT client.
        """
        if not self.enabled or self._client is None:
            return False

        event_time = timestamp or datetime.now(timezone.utc)
        payload = {
            "timestamp": event_time.isoformat(),
            "camera_id": camera_id,
            "risk_score": round(float(risk_score), 4),
            "rules_triggered": list(rules_triggered),
            "video_path": str(video_path) if video_path else None,
        }

        try:
            with self._lock:
                result = self._client.publish(
                    self.topic,
                    json.dumps(payload),
                    qos=1,
                    retain=False,
                )

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                self.logger.warning("MQTT publish failed rc=%s payload=%s", result.rc, payload)
                return False

            return True
        except Exception as exc:
            self.logger.warning("MQTT publish skipped after error: %s", exc)
            return False

    def publish_telemetry(
        self,
        camera_id: str,
        personas_entrantes: int,
        personas_salientes: int,
        personas_en_cola: int,
        tiempo_espera_promedio: float,
        tiempo_espera_estimado: float,
        presion_cola_ratio: float,
        alerta_cola_activa: bool,
        motivo_alerta_cola: str,
        heatmap_points: list[list[int]],
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """Publish a commercial telemetry and heatmap event.

        Returns:
            True if the publish call was accepted by the MQTT client.
        """
        if not self.enabled or self._client is None:
            return False

        event_time = timestamp or datetime.now(timezone.utc)
        payload = {
            "timestamp": event_time.isoformat(),
            "camera_id": camera_id,
            "personas_entrantes": int(personas_entrantes),
            "personas_salientes": int(personas_salientes),
            "personas_en_cola": int(personas_en_cola),
            "tiempo_espera_promedio": round(float(tiempo_espera_promedio), 2),
            "tiempo_espera_estimado": round(float(tiempo_espera_estimado), 2),
            "presion_cola_ratio": round(float(presion_cola_ratio), 4),
            "alerta_cola_activa": bool(alerta_cola_activa),
            "motivo_alerta_cola": str(motivo_alerta_cola or ""),
            "heatmap_points": list(heatmap_points),
        }

        try:
            with self._lock:
                result = self._client.publish(
                    self.telemetry_topic,
                    json.dumps(payload),
                    qos=1,
                    retain=False,
                )

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                self.logger.warning("MQTT telemetry publish failed rc=%s payload=%s", result.rc, payload)
                return False

            return True
        except Exception as exc:
            self.logger.warning("MQTT telemetry publish skipped after error: %s", exc)
            return False

    def release(self) -> None:
        """Stop the MQTT loop and release the client."""
        if self._client is None:
            return

        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception as exc:
            self.logger.debug("Error releasing MQTT publisher: %s", exc)
        finally:
            self._client = None
            self._connected = False
