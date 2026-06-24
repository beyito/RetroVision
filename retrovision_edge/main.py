"""
RetroVision Edge Service - Script Principal de Entrada

Punto de entrada para el microservicio Edge.
"""

import argparse
import signal
import sys
import time
import threading
from pathlib import Path

import cv2
from dotenv import load_dotenv

from edge_service.camera_config_client import CameraConfigClient

EDGE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EDGE_ROOT.parent))

from edge_service import (  # noqa: E402
    CameraAccessError,
    CameraInitializationError,
    DetectionPipeline,
    EdgeControlApiServer,
    EdgeServiceConfig,
    FrameProcessingError,
)
from edge_service.logger_config import setup_logger  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RetroVision Edge Service")
    parser.add_argument(
        "--env-file",
        default=".env",
        help=(
            "Archivo .env a cargar antes de inicializar el servicio. "
            "Puede ser relativo a retrovision_edge o una ruta absoluta."
        ),
    )
    return parser.parse_args()


def resolve_env_file(env_file_argument: str) -> Path:
    candidate = Path(env_file_argument)
    if candidate.is_absolute():
        return candidate
    return EDGE_ROOT / candidate


def load_environment(env_file_argument: str) -> Path:
    env_file_path = resolve_env_file(env_file_argument)
    if env_file_path.exists():
        load_dotenv(env_file_path, override=True)
    else:
        load_dotenv(EDGE_ROOT / ".env", override=False)
    return env_file_path


class EdgeServiceRunner:
    """Orquestador principal del microservicio edge."""

    def __init__(self, env_file_path: Path) -> None:
        self.env_file_path = env_file_path
        self.config = EdgeServiceConfig()
        self.config.validate()

        self.logger = setup_logger(
            "RetroVision.Edge",
            {
                "level": self.config.logging.level,
                "log_file": self.config.logging.log_file,
                "max_bytes": self.config.logging.max_bytes,
                "backup_count": self.config.logging.backup_count,
            },
        )

        self.pipeline: DetectionPipeline | None = None
        self.active_pipelines = {}
        self.control_api_server: EdgeControlApiServer | None = None
        self.control_mqtt_subscriber = None
        
        if self.config.mqtt.enabled:
            from edge_service.control_subscriber import EdgeControlMqttSubscriber
            self.control_mqtt_subscriber = EdgeControlMqttSubscriber(runner=self)

        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame) -> None:
        self.logger.info("Recibida senal %s. Deteniendo servicio...", signum)
        self._cleanup()
        sys.exit(0)

    def run(self) -> None:
        try:
            self.logger.info("=" * 70)
            self.logger.info("RetroVision Edge Service - INICIANDO")
            self.logger.info("Tracking + ROI Colas + Heatmaps + Snapshot API")
            self.logger.info("Configuracion cargada desde: %s", self.env_file_path)
            self.logger.info("=" * 70)

            if self.control_mqtt_subscriber:
                self.control_mqtt_subscriber.start()

            # Si sync_camera_config está habilitado, intentamos conectarnos al backend
            sync_enabled = self.config.backend_api.sync_camera_config
            edge_node_id = self.config.backend_api.edge_node_id
            edge_api_key = self.config.backend_api.edge_api_key
            
            remote_cameras = []
            if sync_enabled and edge_node_id and edge_api_key:
                self.logger.info("Conectando con backend para obtener configuración multicámara...")
                try:
                    client = CameraConfigClient(
                        base_url=self.config.backend_api.base_url,
                        edge_node_id=edge_node_id,
                        edge_api_key=edge_api_key,
                        timeout_seconds=self.config.backend_api.timeout_seconds,
                    )
                    remote_cameras = client.list_cameras()
                    self.logger.info("Encontradas %s cámaras activas vinculadas a este nodo.", len(remote_cameras))
                except Exception as exc:
                    self.logger.warning("Fallo al obtener configuración remota: %s. Se usará modo local.", exc)

            if sync_enabled and remote_cameras:
                self.logger.info("Iniciando en MODO MULTI-CÁMARA ONLINE...")

                # Iniciar hilos para cada cámara
                for cam in remote_cameras:
                    cam_id = cam.get("camera_id")
                    video_src = cam.get("video_source")
                    
                    # Intentar parsear a entero si es número (para webcams locales)
                    try:
                        video_src = int(video_src)
                    except (ValueError, TypeError):
                        pass
                    
                    roi_polygon = cam.get("roi_polygon") or self.config.mqtt.roi_polygon
                    queue_roi_polygon = cam.get("queue_roi_polygon") or roi_polygon
                    counting_line = cam.get("counting_line") or []
                    counting_line_direction = cam.get("counting_line_direction") or "forward"
                    custom_zones = cam.get("custom_zones") or []
                    
                    self.logger.info("Inicializando pipeline para %s (source: %s)...", cam_id, video_src)
                    pipeline = DetectionPipeline(
                        camera_index=0,
                        video_source=video_src,
                        frame_width=self.config.video.frame_width,
                        frame_height=self.config.video.frame_height,
                        target_fps=self.config.video.fps,
                        model_name=self.config.video.model_name,
                        confidence_threshold=0.5,
                        draw_detections=True,
                        mqtt_enabled=self.config.mqtt.enabled,
                        mqtt_broker_host=self.config.mqtt.broker_host,
                        mqtt_broker_port=self.config.mqtt.broker_port,
                        mqtt_client_id=f"{self.config.mqtt.client_id}-{cam_id}",
                        mqtt_topic=self.config.mqtt.topic,
                        mqtt_telemetry_topic=self.config.mqtt.telemetry_topic,
                        roi_polygon=roi_polygon,
                        queue_wait_threshold=cam.get("queue_wait_threshold", self.config.mqtt.queue_wait_threshold),
                        queue_roi_polygon=queue_roi_polygon,
                        queue_dwell_seconds=cam.get("queue_dwell_seconds", self.config.mqtt.queue_dwell_seconds),
                        queue_alert_people_threshold=cam.get("queue_alert_people_threshold", self.config.mqtt.queue_alert_people_threshold),
                        queue_alert_duration_seconds=cam.get("queue_alert_duration_seconds", self.config.mqtt.queue_alert_duration_seconds),
                        max_allowed_wait_seconds=cam.get("max_allowed_wait_seconds", self.config.mqtt.max_allowed_wait_seconds),
                        cashier_count=cam.get("cashier_count", self.config.mqtt.cashier_count),
                        service_rate_per_cashier_per_minute=cam.get("service_rate_per_cashier_per_minute", self.config.mqtt.service_rate_per_cashier_per_minute),
                        mqtt_keep_alive=self.config.mqtt.keep_alive,
                        camera_id=cam_id,
                        counting_line=counting_line,
                        counting_line_direction=counting_line_direction,
                        custom_zones=custom_zones,
                        backend_api_base_url=self.config.backend_api.base_url,
                        edge_node_id=edge_node_id,
                        edge_api_key=edge_api_key,
                    )
                    
                    t = threading.Thread(target=self._camera_thread_loop, args=(pipeline, cam_id, video_src), daemon=True)
                    t.start()
                    self.active_pipelines[cam_id] = {"pipeline": pipeline, "thread": t}

                self.logger.info("Multicámara corriendo. Presione 'q' para salir.")
                
                # Intentar API de control para la primera cámara si está habilitado
                if self.config.control_api.enabled and self.active_pipelines:
                    first_cam_id = list(self.active_pipelines.keys())[0]
                    self.control_api_server = EdgeControlApiServer(
                        pipeline=self.active_pipelines[first_cam_id]["pipeline"],
                        host=self.config.control_api.host,
                        port=self.config.control_api.port,
                        edge_node_id=self.config.backend_api.edge_node_id,
                        edge_api_key=self.config.backend_api.edge_api_key,
                    )
                    self.control_api_server.start()

                # Esperar hasta que se detengan o el usuario presione 'q'
                while any(p["pipeline"].is_running() for p in self.active_pipelines.values()):
                    for cam_id, item in self.active_pipelines.items():
                        pipeline = item["pipeline"]
                        video_src = pipeline.video_source
                        
                        is_local_cam = (
                            isinstance(video_src, int)
                            or str(video_src).isdigit()
                            or "local" in str(cam_id).lower()
                            or "local" in str(video_src).lower()
                            or "/dev/video" in str(video_src).lower()
                        )
                        
                        if is_local_cam:
                            annotated_frame = pipeline.get_latest_annotated_frame()
                            if annotated_frame is not None:
                                cv2.imshow(f"RetroVision Edge - {cam_id}", annotated_frame)
                                
                    key = cv2.waitKey(30) & 0xFF
                    if key == ord("q"):
                        self.logger.info("Cerrando multicámara...")
                        break
            else:
                self.logger.info("Iniciando en MODO LOCAL (Single-Camera/Webcam)...")
                self.pipeline = DetectionPipeline(
                    camera_index=self.config.video.camera_index,
                    video_source=self.config.video.video_source,
                    frame_width=self.config.video.frame_width,
                    frame_height=self.config.video.frame_height,
                    target_fps=self.config.video.fps,
                    model_name=self.config.video.model_name,
                    confidence_threshold=0.5,
                    draw_detections=True,
                    mqtt_enabled=self.config.mqtt.enabled,
                    mqtt_broker_host=self.config.mqtt.broker_host,
                    mqtt_broker_port=self.config.mqtt.broker_port,
                    mqtt_client_id=self.config.mqtt.client_id,
                    mqtt_topic=self.config.mqtt.topic,
                    mqtt_telemetry_topic=self.config.mqtt.telemetry_topic,
                    roi_polygon=self.config.mqtt.roi_polygon,
                    queue_wait_threshold=self.config.mqtt.queue_wait_threshold,
                    queue_roi_polygon=self.config.mqtt.queue_roi_polygon,
                    queue_dwell_seconds=self.config.mqtt.queue_dwell_seconds,
                    queue_alert_people_threshold=self.config.mqtt.queue_alert_people_threshold,
                    queue_alert_duration_seconds=self.config.mqtt.queue_alert_duration_seconds,
                    max_allowed_wait_seconds=self.config.mqtt.max_allowed_wait_seconds,
                    cashier_count=self.config.mqtt.cashier_count,
                    service_rate_per_cashier_per_minute=self.config.mqtt.service_rate_per_cashier_per_minute,
                    mqtt_keep_alive=self.config.mqtt.keep_alive,
                    camera_id=self.config.mqtt.camera_id,
                    counting_line=self.config.mqtt.counting_line,
                    counting_line_direction=self.config.mqtt.counting_line_direction,
                    custom_zones=self.config.mqtt.custom_zones,
                    backend_api_base_url=self.config.backend_api.base_url,
                    edge_node_id=self.config.backend_api.edge_node_id,
                    edge_api_key=self.config.backend_api.edge_api_key,
                )

                self.pipeline.start()

                if self.config.control_api.enabled:
                    self.control_api_server = EdgeControlApiServer(
                        pipeline=self.pipeline,
                        host=self.config.control_api.host,
                        port=self.config.control_api.port,
                        edge_node_id=self.config.backend_api.edge_node_id,
                        edge_api_key=self.config.backend_api.edge_api_key,
                    )
                    self.control_api_server.start()

                self.logger.info("Iniciando deteccion y telemetria (presiona 'q' para salir)...")

                frame_count = 0
                while self.pipeline.is_running():
                    success, frame, metadata, detection_result = self.pipeline.process_frame()

                    if not success or frame is None:
                        self.logger.warning("Fallo la lectura de frame, reintentando...")
                        continue

                    self.pipeline.display_frame_with_info(frame, metadata, detection_result)

                    frame_count += 1
                    if frame_count % 30 == 0 and detection_result:
                        self.logger.info(
                            "Frame %s: %s personas detectadas | Inferencia: %.2fms",
                            metadata.frame_number,
                            detection_result.count(),
                            detection_result.inference_time_ms,
                        )

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        self.logger.info("Usuario presiono 'q'. Saliendo...")
                        break

                self.pipeline.print_stats()

        except CameraInitializationError as exc:
            self.logger.error("Error de inicializacion de camara: %s", exc)
            sys.exit(1)
        except CameraAccessError as exc:
            self.logger.error("Error de acceso a camara: %s", exc)
            sys.exit(1)
        except FrameProcessingError as exc:
            self.logger.error("Error en procesamiento: %s", exc)
            sys.exit(1)
        except Exception as exc:
            self.logger.error("Error inesperado: %s", exc, exc_info=True)
            sys.exit(1)
        finally:
            self._cleanup()

    def _camera_thread_loop(self, pipeline: DetectionPipeline, camera_id: str, video_src: any) -> None:
        self.logger.info("Hilo iniciado para cámara: %s (origen: %s)", camera_id, video_src)
        pipeline.start()
        frame_count = 0
        try:
            while pipeline.is_running():
                success, frame, metadata, detection_result = pipeline.process_frame()
                if not success or frame is None:
                    time.sleep(0.03)  # Evitar saturación en caso de desconexión temporal
                    continue
                frame_count += 1
                if frame_count % 300 == 0:
                    self.logger.info("[%s] Frame %s procesado correctamente.", camera_id, metadata.frame_number)
        except Exception as e:
            self.logger.error("Error en hilo de cámara %s: %s", camera_id, e, exc_info=True)
        finally:
            pipeline.release()
            self.logger.info("Hilo de cámara %s detenido.", camera_id)

    def reload_camera(self, camera_id: str, new_config: dict) -> None:
        """Actualiza la configuración en caliente de la cámara especificada sin detener el hilo."""
        self.logger.info("Recibida solicitud de recarga para cámara: %s", camera_id)

        # 1. Buscar el pipeline activo (modo multi-cámara o modo local)
        pipeline = None
        if hasattr(self, "active_pipelines") and self.active_pipelines:
            if camera_id in self.active_pipelines:
                pipeline = self.active_pipelines[camera_id]["pipeline"]
        elif self.pipeline:
            pipeline = self.pipeline

        if pipeline:
            pipeline.update_config(new_config)
            self.logger.info("Recarga en caliente aplicada con éxito para la cámara: %s", camera_id)
        else:
            self.logger.warning("No se encontró ningún pipeline activo para la cámara %s para aplicar la configuración.", camera_id)

    def _cleanup(self) -> None:
        if self.control_mqtt_subscriber:
            self.control_mqtt_subscriber.stop()
            self.control_mqtt_subscriber = None
        if self.control_api_server:
            self.control_api_server.stop()
            self.control_api_server = None
        if self.pipeline:
            self.pipeline.release()
            self.pipeline = None
        if hasattr(self, "active_pipelines") and self.active_pipelines:
            for cam_id, item in self.active_pipelines.items():
                try:
                    item["pipeline"].stop()
                    item["pipeline"].release()
                except Exception:
                    pass
            self.active_pipelines.clear()

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        self.logger.info("=" * 70)
        self.logger.info("RetroVision Edge Service - DETENIDO")
        self.logger.info("=" * 70)


if __name__ == "__main__":
    args = parse_args()
    env_file_path = load_environment(args.env_file)
    runner = EdgeServiceRunner(env_file_path=env_file_path)
    runner.run()
