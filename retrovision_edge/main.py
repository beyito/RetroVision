"""
RetroVision Edge Service - Script Principal de Entrada

Punto de entrada para el microservicio Edge.
FASE 5: Analítica Espacial Compleja, Tracking, ROI y Heatmaps.
"""

import sys
import logging
import signal
import cv2
from pathlib import Path

# Agregar el directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from edge_service import (
    DetectionPipeline,
    EdgeServiceConfig,
    CameraInitializationError,
    CameraAccessError,
    FrameProcessingError,
)
from edge_service.logger_config import setup_logger


class EdgeServiceRunner:
    """
    Orquestador principal del microservicio Edge.
    """
    
    def __init__(self) -> None:
        """Inicializa el runner del Edge Service."""
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
            self.logger.info("=" * 70)
            
            # Inicializar pipeline de detección
            self.pipeline = DetectionPipeline(
                camera_index=self.config.video.camera_index,
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
    runner = EdgeServiceRunner()
    runner.run()
