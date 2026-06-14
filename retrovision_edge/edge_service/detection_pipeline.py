"""
RetroVision Edge Service - Pipeline de Detección

Módulo que orquesta el flujo completo de captura de video + detección de objetos.
Responsabilidad: Coordinar VideoStreamProcessor, ObjectDetector, PostureEstimator,
BehaviorAnalyzer, RingBuffer y AlertWriter.

Arquitectura FASE 2:
    Cámara → VideoStreamProcessor → ObjectDetector → PostureEstimator → 
    BehaviorAnalyzer → RingBuffer (almacena frames) → 
    Dibujar + Mostrar + (Alerta si risk > 0.7)
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
import time
import cv2

from .video_stream import VideoStreamProcessor, FrameMetadata
from .object_detector import ObjectDetector, DetectionResult, Detection
from .exceptions import RetroVisionEdgeException, FrameProcessingError
from .posture_estimator import PostureEstimator
from .risk_analyzer import BehaviorAnalyzer
from .video_buffer import RingBuffer
from .alert_writer import AlertWriter
from .mqtt_publisher import AlertPublisher


@dataclass
class PipelineStats:
    """Estadísticas del pipeline de detección."""
    total_frames: int = 0
    frames_with_detections: int = 0
    total_persons_detected: int = 0
    avg_inference_time_ms: float = 0.0
    avg_fps: float = 0.0


class DetectionPipeline:
    """
    Pipeline completo de captura y detección.
    
    Responsabilidades:
    - Capturar frames desde cámara
    - Procesar con YOLOv8
    - Dibujar bounding boxes
    - Mantener estadísticas
    - Logging de eventos
    
    Attributes:
        video_processor: VideoStreamProcessor para captura
        object_detector: ObjectDetector para inferencia
        draw_detections: Si dibuja bounding boxes en frame
    """
    
    def __init__(
        self,
        camera_index: int = 0,
        frame_width: int = 1280,
        frame_height: int = 720,
        target_fps: int = 30,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        draw_detections: bool = True,
        mqtt_enabled: bool = True,
        mqtt_broker_host: str = "localhost",
        mqtt_broker_port: int = 1883,
        mqtt_client_id: str = "retrovision-edge-01",
        mqtt_topic: str = "retrovision/edge/alerts",
        mqtt_keep_alive: int = 60,
        camera_id: str = "camera-01",
    ) -> None:
        """
        Inicializa el pipeline de detección.
        
        Args:
            camera_index: Índice de cámara (default: 0)
            frame_width: Ancho del frame (default: 1280)
            frame_height: Alto del frame (default: 720)
            target_fps: FPS objetivo (default: 30)
            model_name: Nombre del modelo YOLOv8 (default: yolov8n.pt)
            confidence_threshold: Umbral de confianza (default: 0.5)
            draw_detections: Si dibuja bounding boxes (default: True)
            
        Raises:
            RetroVisionEdgeException: Si hay error al inicializar
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = target_fps
        self.draw_detections = draw_detections
        self.camera_id = camera_id
        self._mqtt_config = {
            "enabled": mqtt_enabled,
            "broker_host": mqtt_broker_host,
            "broker_port": mqtt_broker_port,
            "client_id": mqtt_client_id,
            "topic": mqtt_topic,
            "keep_alive": mqtt_keep_alive,
        }
        
        self._video_processor: Optional[VideoStreamProcessor] = None
        self._object_detector: Optional[ObjectDetector] = None
        self._posture_estimator: Optional[PostureEstimator] = None
        self._behavior_analyzer: Optional[BehaviorAnalyzer] = None
        self._ring_buffer: Optional[RingBuffer] = None
        self._alert_writer: Optional[AlertWriter] = None
        self._alert_publisher: Optional[AlertPublisher] = None
        self._stats = PipelineStats()
        self._inference_times = []
        self._is_running = False
        
        self._initialize_pipeline(model_name, confidence_threshold)
    
    def _initialize_pipeline(
        self,
        model_name: str,
        confidence_threshold: float,
    ) -> None:
        """
        Inicializa los componentes del pipeline.
        
        Args:
            model_name: Nombre del modelo YOLO
            confidence_threshold: Umbral de confianza
            
        Raises:
            RetroVisionEdgeException: Si hay error en inicialización
        """
        try:
            self.logger.info("Inicializando pipeline de detección...")
            
            # Inicializar video processor
            self._video_processor = VideoStreamProcessor(
                camera_index=self.camera_index,
                frame_width=self.frame_width,
                frame_height=self.frame_height,
                target_fps=self.target_fps,
            )
            
            # Inicializar object detector
            self._object_detector = ObjectDetector(
                model_name=model_name,
                confidence_threshold=confidence_threshold,
                device="cpu",
            )

            # Inicializar estimador de postura (MediaPipe). Si falla,
            # continuamos sin estimación de postura pero registramos la falla.
            try:
                self._posture_estimator = PostureEstimator(model_complexity=0)
            except Exception as e:
                self._posture_estimator = None
                self.logger.warning(f"PostureEstimator no inicializado: {e}")
            
            # Inicializar analizador de comportamiento (FASE 2)
            try:
                self._behavior_analyzer = BehaviorAnalyzer()
            except Exception as e:
                self._behavior_analyzer = None
                self.logger.warning(f"BehaviorAnalyzer no inicializado: {e}")
            
            # Inicializar ring buffer (FASE 2) - CORREGIDO self.target_fps
            try:
                self._ring_buffer = RingBuffer(fps=self.target_fps, retention_seconds=30)
            except Exception as e:
                self._ring_buffer = None
                self.logger.warning(f"RingBuffer no inicializado: {e}")
            
            # Inicializar alert writer (FASE 2)
            try:
                self._alert_writer = AlertWriter(alerts_dir="alerts", cooldown_seconds=10.0)
            except Exception as e:
                self._alert_writer = None
                self.logger.warning(f"AlertWriter no inicializado: {e}")

            # Inicializar publicador MQTT (FASE 3)
            try:
                self._alert_publisher = AlertPublisher(**self._mqtt_config)
            except Exception as e:
                self._alert_publisher = None
                self.logger.warning(f"AlertPublisher no inicializado: {e}")
            
            self.logger.info("Pipeline de detección inicializado exitosamente (FASE 2)")
            
        except Exception as e:
            self.logger.error(f"Error al inicializar pipeline: {e}")
            self.release()
            raise
    
    def start(self) -> None:
        """Inicia el pipeline."""
        self._video_processor.start()
        self._is_running = True
        self.logger.info("Pipeline iniciado")
    
    def stop(self) -> None:
        """Detiene el pipeline."""
        self._is_running = False
        self._video_processor.stop()
        self.logger.info("Pipeline detenido")
    
    def is_running(self) -> bool:
        """Retorna True si el pipeline está activo."""
        return self._is_running
    
    def process_frame(
        self,
    ) -> Tuple[bool, Optional[bytes], Optional[FrameMetadata], Optional[DetectionResult]]:
        """
        Procesa un frame completo: captura → detección → dibuja.
        
        Returns:
            Tupla (success, frame, frame_metadata, detection_result) donde:
            - success: bool indicando éxito
            - frame: numpy array del frame (con bounding boxes si detect)
            - frame_metadata: FrameMetadata del frame
            - detection_result: DetectionResult con detecciones
            
        Raises:
            FrameProcessingError: Si hay error en procesamiento
        """
        try:
            # 1. Capturar frame
            success, frame, metadata = self._video_processor.read_frame()
            
            if not success or frame is None:
                return False, None, None, None
            
            # 2. Ejecutar detección
            detection_result = self._object_detector.detect(frame)
            
            # 3. Actualizar estadísticas
            self._stats.total_frames += 1
            self._stats.total_persons_detected += detection_result.count()
            
            if detection_result.count() > 0:
                self._stats.frames_with_detections += 1
            
            self._inference_times.append(detection_result.inference_time_ms)
            
            # Mantener promedio de últimos 30 frames
            if len(self._inference_times) > 30:
                self._inference_times.pop(0)
            self._stats.avg_inference_time_ms = sum(
                self._inference_times
            ) / len(self._inference_times)
            
            # 4. Dibujar detecciones si está habilitado
            frame_to_display = frame.copy()
            if self.draw_detections and detection_result.count() > 0:
                # Primero dibujar bounding boxes
                frame_to_display = self._object_detector.draw_detections(
                    frame,
                    detection_result.detections,
                )

                # Luego, para cada detección, intentar estimar postura y dibujar
                if self._posture_estimator is not None:
                    for det in detection_result.detections:
                        try:
                            x1, y1, x2, y2 = det.x1, det.y1, det.x2, det.y2

                            # Validar límites y recortar ROI
                            h_frame, w_frame = frame.shape[0], frame.shape[1]
                            x1c = max(0, min(x1, w_frame - 1))
                            y1c = max(0, min(y1, h_frame - 1))
                            x2c = max(x1c + 1, min(x2, w_frame))
                            y2c = max(y1c + 1, min(y2, h_frame))

                            roi_w = x2c - x1c
                            roi_h = y2c - y1c

                            # Evitar ROIs demasiado pequeños
                            if roi_w < 16 or roi_h < 16:
                                continue

                            roi_bgr = frame[y1c:y2c, x1c:x2c]
                            if roi_bgr is None or roi_bgr.size == 0:
                                continue

                            # MediaPipe espera RGB
                            roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

                            lm_norm = self._posture_estimator.estimate(roi_rgb)
                            if not lm_norm:
                                # No landmarks detectados
                                det.landmarks = None
                                continue

                            lm_abs = self._posture_estimator.norm_to_absolute(
                                lm_norm, (x1c, y1c), (roi_w, roi_h)
                            )

                            # Guardar landmarks absolutos en la detección
                            det.landmarks = lm_abs

                            # Dibujar sobre el frame principal
                            self._posture_estimator.draw_landmarks_on_frame(
                                frame_to_display, lm_abs
                            )
                        except Exception as e:
                            self.logger.debug(f"Posture estimation failed for detection: {e}")
            
            # FASE 2: Análisis de Riesgo y Disparador de Alertas
            # 5. Guardar frame en ring buffer (FASE 2)
            if self._ring_buffer is not None:
                self._ring_buffer.add_frame(frame)
            
            # 6. Analizar riesgo por cada detección (FASE 2)
            if self._behavior_analyzer is not None and self._alert_writer is not None:
                high_risk_detected = False
                for det in detection_result.detections:
                    try:
                        # Analizar comportamiento basado en landmarks
                        analysis = self._behavior_analyzer.analyze(det.landmarks)
                        det.risk_score = analysis.risk_score
                        
                        # Si hay alto riesgo, disparar alerta
                        if analysis.risk_score > 0.7:
                            high_risk_detected = True
                            self.logger.warning(
                                f"ALERTA: Risk Score CRÍTICO {analysis.risk_score:.2f} "
                                f"Reglas: {', '.join(analysis.rules_triggered)}"
                            )
                    except Exception as e:
                        self.logger.debug(f"Risk analysis failed for detection: {e}")
                
                # Si se detectó alto riesgo y el alert writer está listo, guardar video
                if high_risk_detected and self._alert_writer.is_alert_ready():
                    try:
                        frames_to_save = self._ring_buffer.get_frames()
                        if frames_to_save:
                            max_risk = max(det.risk_score for det in detection_result.detections)
                            rules = list(set(
                                rule
                                for det in detection_result.detections
                                for _ in ([1] if det.risk_score > 0.7 else [])
                                for rule in self._behavior_analyzer.analyze(det.landmarks).rules_triggered
                            ))
                            
                            video_path = self._alert_writer.write_alert_async(
                                frames_to_save,
                                risk_score=max_risk,
                                triggered_rules=rules,
                            )

                            if self._alert_publisher is not None:
                                self._alert_publisher.publish_alert(
                                    camera_id=self.camera_id,
                                    risk_score=max_risk,
                                    rules_triggered=rules,
                                    video_path=video_path,
                                )
                    except Exception as e:
                        self.logger.error(f"Error disparando alerta: {e}")
            
            return True, frame_to_display, metadata, detection_result
            
        except Exception as e:
            self.logger.error(f"Error procesando frame: {e}")
            raise FrameProcessingError(f"Error en pipeline: {str(e)}") from e
    
    def display_frame_with_info(
        self,
        frame: bytes,
        metadata: FrameMetadata,
        detection_result: Optional[DetectionResult] = None,
        window_name: str = "RetroVision Edge - Detection Pipeline",
    ) -> None:
        """
        Muestra frame con información de video y detección.
        
        Args:
            frame: Frame a mostrar
            metadata: Metadatos del frame
            detection_result: Resultado de detección (opcional)
            window_name: Nombre de la ventana
        """
        import cv2
        
        # Frame info
        info_text = (
            f"Frame: {metadata.frame_number} | "
            f"Time: {metadata.timestamp.strftime('%H:%M:%S')} | "
            f"FPS: {metadata.fps:.1f}"
        )
        
        # Detections info
        if detection_result:
            detections_text = (
                f"Persons: {detection_result.count()} | "
                f"Inference: {detection_result.inference_time_ms:.1f}ms"
            )
        else:
            detections_text = "No detections"
        
        # Dibujar textos
        cv2.putText(
            frame,
            info_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),  # Verde
            2,
        )
        
        cv2.putText(
            frame,
            detections_text,
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),  # Cyan
            2,
        )
        
        cv2.imshow(window_name, frame)
    
    def get_stats(self) -> PipelineStats:
        """Retorna estadísticas del pipeline."""
        return self._stats
    
    def print_stats(self) -> None:
        """Imprime estadísticas formateadas."""
        stats = self._stats
        
        self.logger.info("=" * 60)
        self.logger.info("ESTADÍSTICAS DEL PIPELINE")
        self.logger.info("=" * 60)
        self.logger.info(f"Total frames procesados: {stats.total_frames}")
        self.logger.info(f"Frames con detecciones: {stats.frames_with_detections}")
        self.logger.info(f"Total personas detectadas: {stats.total_persons_detected}")
        self.logger.info(f"Promedio inferencia: {stats.avg_inference_time_ms:.2f}ms")
        
        if stats.total_frames > 0:
            detection_rate = (stats.frames_with_detections / stats.total_frames) * 100
            self.logger.info(f"Tasa de detección: {detection_rate:.1f}%")
        
        self.logger.info("=" * 60)
    
    def release(self) -> None:
        """
        Libera todos los recursos del pipeline.
        """
        try:
            if self._video_processor:
                self._video_processor.release()
                self._video_processor = None
            
            if self._object_detector:
                self._object_detector.release()
                self._object_detector = None
            
            if self._posture_estimator:
                try:
                    self._posture_estimator.release()
                except Exception:
                    pass
                self._posture_estimator = None
            
            if self._behavior_analyzer:
                self._behavior_analyzer = None
            
            if self._ring_buffer:
                try:
                    self._ring_buffer.clear()
                except Exception:
                    pass
                self._ring_buffer = None
            
            if self._alert_writer:
                try:
                    self._alert_writer.wait_for_pending(timeout_seconds=5.0)
                    self._alert_writer.release()
                except Exception:
                    pass
                self._alert_writer = None

            if self._alert_publisher:
                try:
                    self._alert_publisher.release()
                except Exception:
                    pass
                self._alert_publisher = None
            
            self._is_running = False
            self.logger.info("Pipeline liberado correctamente (FASE 2)")
            
        except Exception as e:
            self.logger.error(f"Error al liberar pipeline: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False
