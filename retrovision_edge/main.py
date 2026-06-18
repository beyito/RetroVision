"""
RetroVision Edge Service - Script Principal de Entrada

Punto de entrada para el microservicio Edge.
FASE 5: Analítica Espacial Compleja, Tracking, ROI y Heatmaps.
"""

import argparse
import sys
import logging
import signal
import cv2
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio padre al path para imports
EDGE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(EDGE_ROOT.parent))

from edge_service import (
    DetectionPipeline,
    EdgeServiceConfig,
    CameraInitializationError,
    CameraAccessError,
    FrameProcessingError,
)
from edge_service.logger_config import setup_logger


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="RetroVision Edge Service",
    )
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
    """Resuelve la ruta del archivo .env desde el argumento recibido."""
    candidate = Path(env_file_argument)
    if candidate.is_absolute():
        return candidate
    return EDGE_ROOT / candidate


def load_environment(env_file_argument: str) -> Path:
    """
    Carga variables de entorno desde el archivo indicado.

    Si el archivo no existe, se continúa con variables del entorno del proceso
    para mantener compatibilidad con ejecuciones existentes.
    """
    env_file_path = resolve_env_file(env_file_argument)
    if env_file_path.exists():
        load_dotenv(env_file_path, override=True)
    else:
        load_dotenv(EDGE_ROOT / ".env", override=False)
    return env_file_path


class EdgeServiceRunner:
    """
    Orquestador principal del microservicio Edge.
    """
    
    def __init__(self, env_file_path: Path) -> None:
        """Inicializa el runner del Edge Service."""
        self.env_file_path = env_file_path
        self.config = EdgeServiceConfig()
        self.config.validate()
        
        self.logger = setup_logger(
            'RetroVision.Edge',
            {
                'level': self.config.logging.level,
                'log_file': self.config.logging.log_file,
                'max_bytes': self.config.logging.max_bytes,
                'backup_count': self.config.logging.backup_count,
            }
        )
        
        self.pipeline: DetectionPipeline = None
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Configura handlers para señales del sistema."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        """
        Handler para Ctrl+C y terminación.
        """
        self.logger.info(f"Recibida señal {signum}. Deteniendo servicio...")
        self._cleanup()
        sys.exit(0)
    
    def run(self) -> None:
        """
        Inicia el loop principal de captura, detección y procesamiento.
        """
        try:
            self.logger.info("=" * 70)
            self.logger.info("RetroVision Edge Service - INICIANDO (FASE 5)")
            self.logger.info("Tracking + ROI Colas + Heatmaps")
            self.logger.info(f"Configuración cargada desde: {self.env_file_path}")
            self.logger.info("=" * 70)
            
            # Inicializar pipeline de detección
            self.pipeline = DetectionPipeline(
                camera_index=self.config.video.camera_index,
                video_source=self.config.video.video_source,
                frame_width=self.config.video.frame_width,
                frame_height=self.config.video.frame_height,
                target_fps=self.config.video.fps,
                model_name="yolov8n.pt",  # Nano model para Edge
                confidence_threshold=0.5,
                draw_detections=True,  # Dibujar bounding boxes e IDs
                mqtt_enabled=self.config.mqtt.enabled,
                mqtt_broker_host=self.config.mqtt.broker_host,
                mqtt_broker_port=self.config.mqtt.broker_port,
                mqtt_client_id=self.config.mqtt.client_id,
                mqtt_topic=self.config.mqtt.topic,
                mqtt_telemetry_topic=self.config.mqtt.telemetry_topic,
                roi_polygon=self.config.mqtt.roi_polygon,
                queue_wait_threshold=self.config.mqtt.queue_wait_threshold,
                mqtt_keep_alive=self.config.mqtt.keep_alive,
                camera_id=self.config.mqtt.camera_id,
            )
            
            self.pipeline.start()
            self.logger.info(
                "Iniciando detección y telemetría (presiona 'q' para salir)..."
            )
            
            # Loop principal de procesamiento
            frame_count = 0
            while self.pipeline.is_running():
                success, frame, metadata, detection_result = (
                    self.pipeline.process_frame()
                )
                
                if not success or frame is None:
                    self.logger.warning(
                        "Falló la lectura de frame, reintentando..."
                    )
                    continue
                
                # Mostrar frame con información
                self.pipeline.display_frame_with_info(
                    frame, metadata, detection_result
                )
                
                # Log de detecciones cada 30 frames
                frame_count += 1
                if frame_count % 30 == 0 and detection_result:
                    self.logger.info(
                        f"Frame {metadata.frame_number}: "
                        f"{detection_result.count()} personas detectadas | "
                        f"Inferencia: {detection_result.inference_time_ms:.2f}ms"
                    )
                
                # Esperar tecla 'q' para salir (1 ms timeout)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.logger.info("Usuario presionó 'q'. Saliendo...")
                    break
            
            # Estadísticas finales
            self.pipeline.print_stats()
            
        except CameraInitializationError as e:
            self.logger.error(f"Error de inicialización de cámara: {e}")
            sys.exit(1)
        except CameraAccessError as e:
            self.logger.error(f"Error de acceso a cámara: {e}")
            sys.exit(1)
        except FrameProcessingError as e:
            self.logger.error(f"Error en procesamiento: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error inesperado: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Limpia todos los recursos."""
        if self.pipeline:
            self.pipeline.release()
        
        self.logger.info("=" * 70)
        self.logger.info("RetroVision Edge Service - DETENIDO")
        self.logger.info("=" * 70)


if __name__ == '__main__':
    args = parse_args()
    env_file_path = load_environment(args.env_file)
    runner = EdgeServiceRunner(env_file_path=env_file_path)
    runner.run()
