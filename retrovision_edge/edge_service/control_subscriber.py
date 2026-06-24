"""MQTT subscriber for reverse snapshot commands from RetroVision Cloud."""

from __future__ import annotations

import json
import base64
import logging
import threading
from typing import Any, Optional
from paho.mqtt import client as mqtt


class EdgeControlMqttSubscriber:
    """Subscribes to snapshot requests and publishes base64 compressed snapshots."""

    def __init__(self, runner: Any) -> None:
        self.runner = runner
        self.config = runner.config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.edge_node_id = self.config.backend_api.edge_node_id
        
        self.broker_host = self.config.mqtt.broker_host
        self.broker_port = self.config.mqtt.broker_port
        self.keep_alive = self.config.mqtt.keep_alive
        
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the subscription in a background MQTT loop."""
        if not self.edge_node_id:
            self.logger.warning("EDGE_NODE_ID no configurado. No se iniciará el suscriptor de control.")
            return

        try:
            client_id = f"retrovision-edge-control-{self.edge_node_id}"
            self._client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect

            self._client.connect(self.broker_host, self.broker_port, self.keep_alive)
            self._client.loop_start()
            self.logger.info(
                "EdgeControlMqttSubscriber iniciado y conectando a %s:%s",
                self.broker_host,
                self.broker_port,
            )
        except Exception as exc:
            self.logger.error("Error al iniciar suscriptor MQTT de control: %s", exc)

    def stop(self) -> None:
        """Stop the background loop and disconnect."""
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
                self.logger.info("EdgeControlMqttSubscriber detenido.")
            except Exception as exc:
                self.logger.debug("Error deteniendo suscriptor MQTT de control: %s", exc)
            finally:
                self._client = None
                self._connected = False

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Any,
        rc: int,
    ) -> None:
        """Handle connection and subscribe to topics."""
        self._connected = rc == 0
        if self._connected:
            snapshot_topic = f"retrovision/edge/{self.edge_node_id}/snapshot/request"
            config_topic = f"retrovision/edge/{self.edge_node_id}/config/update"
            client.subscribe([(snapshot_topic, 1), (config_topic, 1)])
            self.logger.info(
                "EdgeControlMqttSubscriber conectado. Suscrito a topics: %s y %s",
                snapshot_topic,
                config_topic,
            )
        else:
            self.logger.warning("Fallo en la conexión del suscriptor de control rc=%s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, rc: int) -> None:
        self._connected = False
        if rc != 0:
            self.logger.warning("Suscriptor MQTT de control desconectado inesperadamente rc=%s", rc)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Handle incoming snapshot or configuration reload requests."""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode("utf-8"))

            if "config/update" in topic:
                camera_id = payload.get("camera_id")
                if not camera_id:
                    self.logger.warning("Mensaje de recarga de configuración recibido sin camera_id.")
                    return
                self.logger.info("Mensaje de recarga de configuración recibido para la cámara: %s", camera_id)
                if hasattr(self.runner, "reload_camera"):
                    t = threading.Thread(
                        target=self.runner.reload_camera,
                        args=(camera_id, payload),
                        daemon=True
                    )
                    t.start()
                else:
                    self.logger.warning("El runner no tiene el método 'reload_camera' disponible.")
                return

            # Snapshot request logic
            camera_id = payload.get("camera_id")
            correlation_id = payload.get("correlation_id")

            if not correlation_id:
                self.logger.warning("Mensaje de snapshot request recibido sin correlation_id.")
                return

            self.logger.info(
                "Solicitud de snapshot recibida para camera_id=%s, correlation_id=%s",
                camera_id,
                correlation_id,
            )

            # Buscar pipeline correspondiente
            pipeline = self._find_pipeline(camera_id)
            
            response_topic = f"retrovision/cloud/{self.edge_node_id}/snapshot/response"
            response_payload = {"correlation_id": correlation_id}

            if pipeline is None:
                response_payload["error"] = f"Cámara {camera_id} no encontrada en este nodo."
            else:
                # Obtener snapshot redimensionado y comprimido
                jpeg_bytes = pipeline.get_resized_snapshot_jpeg()
                if not jpeg_bytes:
                    response_payload["error"] = "No hay frames disponibles para esta cámara."
                else:
                    img_b64 = base64.b64encode(jpeg_bytes).decode("utf-8")
                    response_payload["image_base64"] = img_b64

            # Publicar respuesta
            client.publish(response_topic, json.dumps(response_payload), qos=1)
            self.logger.info(
                "Respuesta de snapshot enviada para correlation_id=%s a topic=%s",
                correlation_id,
                response_topic,
            )

        except json.JSONDecodeError:
            self.logger.warning("Payload JSON inválido en topic de control.")
        except Exception as exc:
            self.logger.error("Error procesando mensaje de control: %s", exc, exc_info=True)

    def _find_pipeline(self, camera_id: Optional[str]) -> Any:
        """Find the pipeline corresponding to camera_id using safe attribute checks."""
        # Modo multi-cámara
        if hasattr(self.runner, "active_pipelines") and self.runner.active_pipelines:
            if camera_id in self.runner.active_pipelines:
                return self.runner.active_pipelines[camera_id]["pipeline"]
            if not camera_id:
                # Por defecto retornar la primera cámara activa
                first_key = list(self.runner.active_pipelines.keys())[0]
                return self.runner.active_pipelines[first_key]["pipeline"]

        # Modo cámara única
        if hasattr(self.runner, "pipeline") and self.runner.pipeline:
            # Si camera_id es vacío o coincide
            if not camera_id or self.runner.pipeline.camera_id == camera_id:
                return self.runner.pipeline

        return None
