"""
RetroVision Edge Service - Pipeline de Detección

Módulo que orquesta el flujo completo de captura de video + detección de objetos.
Responsabilidad: Coordinar VideoStreamProcessor, ObjectDetector, PostureEstimator,
BehaviorAnalyzer, RingBuffer, AlertWriter y AlertPublisher.
"""

import logging
import threading
import math
from typing import Optional, Tuple, Union
from dataclasses import dataclass
import time
import cv2
import numpy as np

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
    - Detección y tracking con YOLOv8
    - Dibujar bounding boxes y trazas
    - Analizar afluencia y ROI
    - Generar heatmap
    """
    
    def __init__(
        self,
        camera_index: int = 0,
        video_source: Optional[Union[int, str]] = None,
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
        mqtt_telemetry_topic: str = "retrovision/telemetry",
        roi_polygon: Optional[list] = None,
        queue_wait_threshold: float = 5.0,
        queue_roi_polygon: Optional[list] = None,
        queue_dwell_seconds: float = 2.0,
        queue_alert_people_threshold: int = 3,
        queue_alert_duration_seconds: float = 5.0,
        max_allowed_wait_seconds: float = 120.0,
        cashier_count: int = 1,
        service_rate_per_cashier_per_minute: float = 12.0,
        camera_id: str = "camera-01",
        counting_line: Optional[list] = None,
        counting_line_direction: str = "forward",
        custom_zones: Optional[list] = None,
        mqtt_keep_alive: int = 60,
        backend_api_base_url: str = "",
        edge_node_id: str = "",
        edge_api_key: str = "",
    ) -> None:
        """
        Inicializa el pipeline de detección.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.camera_index = camera_index
        self.video_source = video_source if video_source is not None else camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = target_fps
        self.draw_detections = draw_detections
        self.camera_id = camera_id
        
        # Phase 5 properties
        self.roi_polygon = roi_polygon or []
        self.queue_wait_threshold = queue_wait_threshold
        self.queue_roi_polygon = queue_roi_polygon or []
        self.custom_zones = custom_zones or []
        self.queue_dwell_seconds = queue_dwell_seconds
        self.queue_alert_people_threshold = queue_alert_people_threshold
        self.queue_alert_duration_seconds = queue_alert_duration_seconds
        self.max_allowed_wait_seconds = max_allowed_wait_seconds
        self.cashier_count = max(1, cashier_count)
        self.service_rate_per_cashier_per_minute = max(0.1, service_rate_per_cashier_per_minute)
        self.backend_api_base_url = backend_api_base_url
        self.edge_node_id = edge_node_id
        self.edge_api_key = edge_api_key
        
        # Trajectory trail history: track_id -> list of centroids
        self.trajectory_history = {}
        # Entry time in ROI: track_id -> float timestamp
        self.roi_entry_times = {}
        self.queue_candidate_since = {}
        self.queue_alert_started_at = None
        # Last seen time: track_id -> float timestamp
        self.last_seen_time = {}
        # Track already alerted rules to avoid repetitive anomalies: (track_id, rule) -> float timestamp
        self.alerted_track_rules = {}
        
        # Telemetry aggregators
        self.seen_track_ids = set()
        self.personas_entrantes_count = 0
        self.personas_salientes_count = 0
        self.recent_heatmap_points = []
        self.last_telemetry_publish_time = time.time()
        
        # Counting line properties & state for hysteresis & memory cleanup
        self.counting_line = counting_line or []
        self.counting_line_direction = counting_line_direction or "forward"
        self.track_sides = {}
        self.last_cross_frame = {}
        self.last_seen_frame = {}
        self.frame_counter = 0
        
        # Heatmap float32 accumulator
        self.heatmap_accumulator = np.zeros((frame_height, frame_width), dtype=np.float32)
        # ROI numpy polygon
        self.roi_poly_np = np.array(self.roi_polygon, dtype=np.int32).reshape((-1, 1, 2)) if self.roi_polygon else None
        self.queue_roi_poly_np = np.array(self.queue_roi_polygon, dtype=np.int32).reshape((-1, 1, 2)) if self.queue_roi_polygon else None
        
        self._mqtt_config = {
            "enabled": mqtt_enabled,
            "broker_host": mqtt_broker_host,
            "broker_port": mqtt_broker_port,
            "client_id": mqtt_client_id,
            "topic": mqtt_topic,
            "telemetry_topic": mqtt_telemetry_topic,
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
        self._latest_frame_lock = threading.Lock()
        self._latest_frame_jpeg: Optional[bytes] = None
        self._latest_raw_frame_jpeg: Optional[bytes] = None
        self._latest_raw_frame: Optional[np.ndarray] = None
        self._latest_annotated_frame: Optional[np.ndarray] = None
        
        self._initialize_pipeline(model_name, confidence_threshold)
    
    def _initialize_pipeline(
        self,
        model_name: str,
        confidence_threshold: float,
    ) -> None:
        """
        Inicializa los componentes del pipeline.
        """
        try:
            self.logger.info("Inicializando pipeline de detección...")
            
            # Inicializar video processor
            self._video_processor = VideoStreamProcessor(
                camera_index=self.camera_index,
                video_source=self.video_source,
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

            # Inicializar estimador de postura (MediaPipe)
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
            
            # Inicializar ring buffer (FASE 2)
            try:
                import os
                retention_val = int(os.getenv("BUFFER_DURATION", "10"))
                self._ring_buffer = RingBuffer(fps=self.target_fps, retention_seconds=retention_val)
            except Exception as e:
                self._ring_buffer = None
                self.logger.warning(f"RingBuffer no inicializado: {e}")
            
            # Inicializar alert writer (FASE 2)
            try:
                import os
                cooldown_val = float(os.getenv("ALERT_COOLDOWN_SECONDS", "30.0"))
                self._alert_writer = AlertWriter(
                    alerts_dir="alerts",
                    cooldown_seconds=cooldown_val,
                    backend_api_base_url=self.backend_api_base_url,
                    edge_node_id=self.edge_node_id,
                    edge_api_key=self.edge_api_key,
                    camera_id=self.camera_id,
                )
            except Exception as e:
                self._alert_writer = None
                self.logger.warning(f"AlertWriter no inicializado: {e}")

            # Inicializar publicador MQTT (FASE 3)
            try:
                self._alert_publisher = AlertPublisher(**self._mqtt_config)
            except Exception as e:
                self._alert_publisher = None
                self.logger.warning(f"AlertPublisher no inicializado: {e}")
            
            self.logger.info("Pipeline de detección inicializado exitosamente")
            
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

    def _ccw(self, A, B, C):
        """Devuelve True si los puntos A, B, C están en sentido antihorario."""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def _segments_intersect(self, A, B, C, D):
        """Verifica si el segmento AB intersecta con el segmento CD."""
        return self._ccw(A, C, D) != self._ccw(B, C, D) and self._ccw(A, B, C) != self._ccw(A, B, D)
        
    def process_frame(
        self,
    ) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata], Optional[DetectionResult]]:
        """
        Procesa un frame completo: captura → detección/tracking → dibuja → analíticas.
        """
        try:
            # 1. Capturar frame
            success, frame, metadata = self._video_processor.read_frame()
            
            if not success or frame is None:
                return False, None, None, None
            
            # 2. Ejecutar detección y tracking
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
                # Primero dibujar bounding boxes con IDs
                frame_to_display = self._object_detector.draw_detections(
                    frame,
                    detection_result.detections,
                )

                # Luego, para cada detección, intentar estimar postura y dibujar
                if self._posture_estimator is not None:
                    for det in detection_result.detections:
                        # Solo estimamos postura para personas
                        if det.class_name.lower() not in ("person", "people"):
                            continue
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
                                det.landmarks = None
                                continue

                            lm_abs = self._posture_estimator.norm_to_absolute(
                                lm_norm, (x1c, y1c), (roi_w, roi_h)
                            )

                            det.landmarks = lm_abs

                            # Dibujar sobre el frame principal
                            self._posture_estimator.draw_landmarks_on_frame(
                                frame_to_display, lm_abs
                            )
                        except Exception as e:
                            self.logger.debug(f"Posture estimation failed for detection: {e}")
            
            # --- PHASE 5: SPATIAL ANALYTICS AND TRACKING ---
            self.frame_counter += 1
            current_time = time.time()
            detected_track_ids = set()
            h_frame, w_frame = frame.shape[0], frame.shape[1]

            # 1. Scale custom zones to actual frame resolution
            scaled_custom_zones = []
            for zone in self.custom_zones:
                zone_name = zone.get("name", "Zona")
                normalized_poly = zone.get("polygon", [])
                if len(normalized_poly) >= 3:
                    abs_poly = []
                    for pt in normalized_poly:
                        abs_poly.append([int(pt[0] * w_frame), int(pt[1] * h_frame)])
                    abs_poly_np = np.array(abs_poly, dtype=np.int32).reshape((-1, 1, 2))
                    scaled_custom_zones.append((zone_name, abs_poly_np))

            # Draw custom zones
            for zone_name, poly_np in scaled_custom_zones:
                cv2.polylines(frame_to_display, [poly_np], isClosed=True, color=(255, 0, 255), thickness=2) # Purple
                if len(poly_np) > 0:
                    first_pt = poly_np[0][0]
                    cv2.putText(
                        frame_to_display,
                        zone_name,
                        (int(first_pt[0]), int(first_pt[1]) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 0, 255),
                        2,
                    )

            # Scale normalized counting line coordinates to actual frame resolution
            has_counting_line = len(self.counting_line) == 2
            if has_counting_line:
                P1 = (int(self.counting_line[0][0] * w_frame), int(self.counting_line[0][1] * h_frame))
                P2 = (int(self.counting_line[1][0] * w_frame), int(self.counting_line[1][1] * h_frame))

            # Draw ROI Queue Area polygon if active
            has_queue_roi = self.queue_roi_poly_np is not None and len(self.queue_roi_polygon) >= 3
            if has_queue_roi:
                cv2.polylines(frame_to_display, [self.queue_roi_poly_np], isClosed=True, color=(0, 165, 255), thickness=2)
                cv2.putText(
                    frame_to_display,
                    "ROI COLA",
                    (self.queue_roi_polygon[0][0], self.queue_roi_polygon[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 165, 255),
                    2,
                )

            # Process trajectories, ROI, custom zones and heatmap coordinates
            zone_counts = {z.get("name", "Zona"): 0 for z in self.custom_zones}
            for det in detection_result.detections:
                # Solo procesamos métricas comerciales y flujo espacial para personas
                if det.class_name.lower() not in ("person", "people"):
                    continue
                cx, cy = det.center()
                
                # Accumulate recent coordinates for database heatmap matrix
                self.recent_heatmap_points.append([int(cx), int(cy)])
                
                # Accumulate visual heatmap matrix
                cv2.circle(self.heatmap_accumulator, (int(cx), int(cy)), 25, 0.05, -1)

                # Check custom zones occupancy
                for zone_name, poly_np in scaled_custom_zones:
                    if cv2.pointPolygonTest(poly_np, (float(cx), float(cy)), False) >= 0:
                        zone_counts[zone_name] += 1

                if det.track_id is not None:
                    tid = det.track_id
                    detected_track_ids.add(tid)
                    self.last_seen_time[tid] = current_time
                    self.last_seen_frame[tid] = self.frame_counter

                    # Update Trajectory trail history
                    if tid not in self.trajectory_history:
                        self.trajectory_history[tid] = []
                    self.trajectory_history[tid].append((int(cx), int(cy)))
                    if len(self.trajectory_history[tid]) > 40:
                        self.trajectory_history[tid].pop(0)

                    # Draw trail line
                    trail = self.trajectory_history[tid]
                    if len(trail) > 1:
                        for i in range(1, len(trail)):
                            cv2.line(frame_to_display, trail[i-1], trail[i], (255, 0, 0), 2)  # Blue line

                    # Check queue ROI if active
                    if has_queue_roi:
                        inside = cv2.pointPolygonTest(self.queue_roi_poly_np, (float(cx), float(cy)), False) >= 0
                        if inside:
                            if tid not in self.queue_candidate_since:
                                self.queue_candidate_since[tid] = current_time
                            if tid not in self.roi_entry_times:
                                self.roi_entry_times[tid] = self.queue_candidate_since[tid]
                            
                            elapsed = current_time - self.queue_candidate_since[tid]
                            # Draw warning text on frame if waiting > threshold
                            if elapsed >= self.queue_dwell_seconds:
                                cv2.putText(
                                    frame_to_display,
                                    f"ID {tid} ESPERA: {elapsed:.1f}s",
                                    (det.x1, det.y1 - 25),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5,
                                    (0, 0, 255),
                                    2,
                                )
                        else:
                            if tid in self.queue_candidate_since:
                                self.queue_candidate_since.pop(tid)
                            if tid in self.roi_entry_times:
                                self.roi_entry_times.pop(tid)

                    # Calculate Traffic Flow (Line Crossing)
                    if has_counting_line:
                        # Determinant to check which side of directed segment P1->P2 centroid is on
                        side_val = (cx - P1[0]) * (P2[1] - P1[1]) - (cy - P1[1]) * (P2[0] - P1[0])
                        side = 1 if side_val >= 0 else -1

                        if tid not in self.track_sides:
                            self.track_sides[tid] = side
                        else:
                            prev_side = self.track_sides[tid]
                            # Only evaluate if trail history is at least 5 frames (flicker prevention)
                            if side != prev_side and len(trail) >= 5:
                                last_cross = self.last_cross_frame.get(tid, 0)
                                # 60 frame cooldown (~2 seconds hysteresis) to avoid duplicate counts
                                if self.frame_counter - last_cross > 60:
                                    P_curr = (int(cx), int(cy))
                                    P_prev = trail[-2] if len(trail) >= 2 else P_curr
                                    if self._segments_intersect(P_prev, P_curr, P1, P2):
                                        if side == 1:
                                            # Crossed from Side -1 to Side 1
                                            if self.counting_line_direction == "forward":
                                                self.personas_entrantes_count += 1
                                            else:
                                                self.personas_salientes_count += 1
                                        else:
                                            # Crossed from Side 1 to Side -1
                                            if self.counting_line_direction == "forward":
                                                self.personas_salientes_count += 1
                                            else:
                                                self.personas_entrantes_count += 1
                                        self.last_cross_frame[tid] = self.frame_counter
                            self.track_sides[tid] = side

            # Clean up missing track IDs (lost longer than 5 seconds)
            for tid in list(self.last_seen_time.keys()):
                if current_time - self.last_seen_time[tid] > 5.0:
                    self.last_seen_time.pop(tid)
                    if tid in self.trajectory_history:
                        self.trajectory_history.pop(tid)
                    if tid in self.queue_candidate_since:
                        self.queue_candidate_since.pop(tid)
                    if tid in self.roi_entry_times:
                        self.roi_entry_times.pop(tid)
                    
                    # Limpiar reglas alertadas asociadas al track_id
                    for key in list(self.alerted_track_rules.keys()):
                        if key[0] == tid:
                            self.alerted_track_rules.pop(key)

            # Memory cleanup: purge obsolete track IDs from sides & cross states after 50 frames of invisibility
            for tid in list(self.last_seen_frame.keys()):
                if self.frame_counter - self.last_seen_frame[tid] > 50:
                    self.last_seen_frame.pop(tid)
                    if tid in self.track_sides:
                        self.track_sides.pop(tid)
                    if tid in self.last_cross_frame:
                        self.last_cross_frame.pop(tid)

            # Draw visual counting line & direction arrow in OpenCV
            if has_counting_line:
                cv2.line(frame_to_display, P1, P2, (0, 255, 255), 3) # Yellow line
                dx = P2[0] - P1[0]
                dy = P2[1] - P1[1]
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0:
                    nx = -dy / dist
                    ny = dx / dist
                    if self.counting_line_direction == 'backward':
                        nx = -nx
                        ny = -ny
                    mid_x = (P1[0] + P2[0]) // 2
                    mid_y = (P1[1] + P2[1]) // 2
                    arrow_end_x = int(mid_x + nx * 40)
                    arrow_end_y = int(mid_y + ny * 40)
                    cv2.arrowedLine(frame_to_display, (mid_x, mid_y), (arrow_end_x, arrow_end_y), (0, 255, 255), 2, tipLength=0.3)
                    cv2.putText(
                        frame_to_display,
                        "ENTRADA",
                        (arrow_end_x + 5, arrow_end_y + 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 255),
                        2,
                    )

            # Draw visual Heatmap Blend Overlay
            if np.max(self.heatmap_accumulator) > 0:
                heatmap_norm = cv2.normalize(self.heatmap_accumulator, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
                frame_to_display = cv2.addWeighted(frame_to_display, 0.7, heatmap_color, 0.3, 0)

            # 4. Periodically publish commercial telemetry to MQTT every 1 second
            if current_time - self.last_telemetry_publish_time >= 1.0:
                # Calculate wait times inside ROI
                roi_waits = []
                for tid, entry_time in list(self.roi_entry_times.items()):
                    elapsed = current_time - entry_time
                    if elapsed >= self.queue_dwell_seconds:
                        roi_waits.append(elapsed)
                
                personas_en_cola = len(roi_waits)
                tiempo_espera_promedio = sum(roi_waits) / personas_en_cola if personas_en_cola > 0 else 0.0
                capacidad_personas_por_minuto = self.cashier_count * self.service_rate_per_cashier_per_minute
                tiempo_espera_estimado = (
                    (personas_en_cola / capacidad_personas_por_minuto) * 60.0
                    if capacidad_personas_por_minuto > 0
                    else 0.0
                )
                presion_cola_ratio = (
                    tiempo_espera_estimado / self.max_allowed_wait_seconds
                    if self.max_allowed_wait_seconds > 0
                    else 0.0
                )
                alert_conditions = []
                if has_queue_roi:
                    if personas_en_cola >= self.queue_alert_people_threshold:
                        alert_conditions.append(
                            f"cola>= {self.queue_alert_people_threshold} personas"
                        )
                    if tiempo_espera_promedio >= self.max_allowed_wait_seconds:
                        alert_conditions.append(
                            f"espera_promedio>= {self.max_allowed_wait_seconds:.0f}s"
                        )
                    if tiempo_espera_estimado >= self.max_allowed_wait_seconds:
                        alert_conditions.append(
                            f"espera_estimada>= {self.max_allowed_wait_seconds:.0f}s"
                        )

                if alert_conditions:
                    if self.queue_alert_started_at is None:
                        self.queue_alert_started_at = current_time
                else:
                    self.queue_alert_started_at = None

                alerta_cola_activa = (
                    self.queue_alert_started_at is not None
                    and (current_time - self.queue_alert_started_at) >= self.queue_alert_duration_seconds
                )
                motivo_alerta_cola = " | ".join(alert_conditions) if alerta_cola_activa else ""
                
                if self._alert_publisher is not None:
                    self._alert_publisher.publish_telemetry(
                        camera_id=self.camera_id,
                        personas_entrantes=self.personas_entrantes_count,
                        personas_salientes=self.personas_salientes_count,
                        personas_en_cola=personas_en_cola,
                        tiempo_espera_promedio=tiempo_espera_promedio,
                        tiempo_espera_estimado=tiempo_espera_estimado,
                        presion_cola_ratio=presion_cola_ratio,
                        alerta_cola_activa=alerta_cola_activa,
                        motivo_alerta_cola=motivo_alerta_cola,
                        heatmap_points=self.recent_heatmap_points,
                        sectores=zone_counts,
                    )
                
                self.recent_heatmap_points = []
                self.last_telemetry_publish_time = current_time

            # --- END PHASE 5 ---

            self._update_latest_raw_frame(frame)

            # 5. Guardar frame en ring buffer (FASE 2)
            if self._ring_buffer is not None:
                self._ring_buffer.add_frame(frame)

            self._update_latest_frame(frame_to_display)
            
            # 6. Analizar riesgo por cada detección (FASE 2)
            if self._behavior_analyzer is not None and self._alert_writer is not None:
                high_risk_detected = False
                rules_this_frame = {}  # track_id -> list of rules triggered in this frame
                
                for det in detection_result.detections:
                    is_weapon = det.class_name.lower() in ("knife", "scissors", "pistol", "handgun", "firearm", "gun", "rifle") or any(w in det.class_name.lower() for w in ("knife", "scissors", "pistol", "handgun", "firearm", "gun", "rifle"))
                    is_mask = det.class_name.lower() == "mask"
                    
                    det_rules = []
                    if is_weapon:
                        is_firearm = any(w in det.class_name.lower() for w in ("pistol", "handgun", "firearm", "gun", "rifle"))
                        if is_firearm:
                            det_rules.append("Presencia de Arma de Fuego")
                        else:
                            det_rules.append("Presencia de Arma Blanca")
                    elif is_mask:
                        det_rules.append("Persona Enmascarada")
                    elif det.class_name.lower() == "no-mask":
                        continue
                    elif det.landmarks:
                        try:
                            analysis = self._behavior_analyzer.analyze(det.landmarks)
                            det.risk_score = analysis.risk_score
                            if analysis.risk_score > 0.4:
                                det_rules.extend(analysis.rules_triggered)
                        except Exception as e:
                            self.logger.debug(f"Risk analysis failed for detection: {e}")
                    
                    if det_rules:
                        if is_weapon or is_mask:
                            det.risk_score = max(0.95, det.confidence)
                        
                        rules_this_frame[det.track_id] = det_rules
                        
                        # Filtrar las reglas que ya están en cooldown para este track
                        new_rules = []
                        for rule in det_rules:
                            key = (det.track_id, rule)
                            # Cooldown por anomalía y track ID (5 minutos = 300s)
                            if key in self.alerted_track_rules:
                                if current_time - self.alerted_track_rules[key] < 300.0:
                                    continue
                            new_rules.append(rule)
                        
                        if new_rules:
                            high_risk_detected = True
                            self.logger.debug(
                                f"ALERTA DE SEGURIDAD DETECTADA: Track ID {det.track_id} disparó {', '.join(new_rules)}"
                            )
                
                # Guardar video si se disparó alerta
                if high_risk_detected and self._alert_writer.is_alert_ready():
                    try:
                        frames_to_save = self._ring_buffer.get_frames()
                        if frames_to_save:
                            max_risk = max([det.risk_score for det in detection_result.detections] or [0.4])
                            rules = []
                            for tid, rlist in rules_this_frame.items():
                                rules.extend(rlist)
                            rules = list(set(rules))
                            
                            # Find which zone the threat was in
                            alert_zone = ""
                            for det in detection_result.detections:
                                if det.risk_score > 0.4:
                                    cx, cy = det.center()
                                    for zone_name, poly_np in scaled_custom_zones:
                                        if cv2.pointPolygonTest(poly_np, (float(cx), float(cy)), False) >= 0:
                                            alert_zone = zone_name
                                            break
                                    if alert_zone:
                                        break
                            
                            video_path = self._alert_writer.write_alert_async(
                                frames_to_save,
                                risk_score=max_risk,
                                triggered_rules=rules,
                                zona=alert_zone,
                            )
                            
                            if self._alert_publisher is not None:
                                self._alert_publisher.publish_alert(
                                    camera_id=self.camera_id,
                                    risk_score=max_risk,
                                    rules_triggered=rules,
                                    video_path=video_path,
                                    zona=alert_zone,
                                )
                            
                            self.logger.warning(
                                f"🔥 ¡ALERTA DE SEGURIDAD EMITIDA! Reglas: {', '.join(rules)} | Zona: {alert_zone or 'Ninguna'}"
                            )
                            
                            # Registrar tiempo de alerta para las reglas y objetos involucrados
                            for tid, rlist in rules_this_frame.items():
                                for rule in rlist:
                                    self.alerted_track_rules[(tid, rule)] = current_time
                    except Exception as e:
                        self.logger.error(f"Error disparando alerta: {e}")
            
            return True, frame_to_display, metadata, detection_result
            
        except Exception as e:
            self.logger.error(f"Error procesando frame: {e}")
            raise FrameProcessingError(f"Error en pipeline: {str(e)}") from e
    
    def display_frame_with_info(
        self,
        frame: np.ndarray,
        metadata: FrameMetadata,
        detection_result: Optional[DetectionResult] = None,
        window_name: str = "RetroVision Edge - Detection Pipeline",
    ) -> None:
        """
        Muestra frame con información de video y detección.
        """
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
        
        # Draw analytics stats overlay
        stats_text = f"In: {self.personas_entrantes_count} | Out: {self.personas_salientes_count}"
        cv2.putText(
            frame,
            stats_text,
            (10, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 165, 255),
            2,
        )
        
        cv2.imshow(window_name, frame)

    def _update_latest_frame(self, frame: np.ndarray) -> None:
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not success:
            return
        with self._latest_frame_lock:
            self._latest_frame_jpeg = encoded.tobytes()
            self._latest_annotated_frame = frame.copy()

    def get_latest_annotated_frame(self) -> Optional[np.ndarray]:
        """Retorna el último frame anotado de forma segura y eficiente (numpy array)."""
        with self._latest_frame_lock:
            return self._latest_annotated_frame

    def _update_latest_raw_frame(self, frame: np.ndarray) -> None:
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not success:
            return
        with self._latest_frame_lock:
            self._latest_raw_frame_jpeg = encoded.tobytes()
            self._latest_raw_frame = frame.copy()

    def get_latest_frame_jpeg(self) -> Optional[bytes]:
        with self._latest_frame_lock:
            return self._latest_raw_frame_jpeg or self._latest_frame_jpeg

    def get_resized_snapshot_jpeg(self) -> Optional[bytes]:
        with self._latest_frame_lock:
            if self._latest_raw_frame is None:
                raw_jpeg = self._latest_raw_frame_jpeg or self._latest_frame_jpeg
                if raw_jpeg:
                    nparr = np.frombuffer(raw_jpeg, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                else:
                    return None
            else:
                img = self._latest_raw_frame.copy()

        if img is None:
            return None

        h, w = img.shape[:2]
        if w > 800:
            new_w = 800
            new_h = int(h * (800 / w))
            img = cv2.resize(img, (new_w, new_h))

        success, encoded = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
        if success:
            return encoded.tobytes()
        return None
    
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
            self.logger.info("Pipeline liberado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error al liberar pipeline: {e}")

    def update_config(self, new_config: dict) -> None:
        """Actualiza la configuración geométrica y de reglas del pipeline en caliente."""
        if "camera_id" in new_config and new_config["camera_id"]:
            self.camera_id = new_config["camera_id"]
            
        self.logger.info("[%s] Actualizando configuración en caliente...", self.camera_id)
        
        # 1. Polígonos de ROI
        if "roi_polygon" in new_config:
            self.roi_polygon = new_config["roi_polygon"] or []
            self.roi_poly_np = np.array(self.roi_polygon, dtype=np.int32).reshape((-1, 1, 2)) if self.roi_polygon else None
            
        if "queue_roi_polygon" in new_config:
            self.queue_roi_polygon = new_config["queue_roi_polygon"] or []
            self.queue_roi_poly_np = np.array(self.queue_roi_polygon, dtype=np.int32).reshape((-1, 1, 2)) if self.queue_roi_polygon else None
            
        # 2. Línea de conteo
        if "counting_line" in new_config:
            self.counting_line = new_config["counting_line"] or []
        if "counting_line_direction" in new_config:
            self.counting_line_direction = new_config["counting_line_direction"] or "forward"
            
        # 3. Zonas personalizadas
        if "custom_zones" in new_config:
            self.custom_zones = new_config["custom_zones"] or []
            
        # 4. Parámetros de cola y límites
        if "queue_wait_threshold" in new_config:
            self.queue_wait_threshold = new_config["queue_wait_threshold"]
        if "queue_dwell_seconds" in new_config:
            self.queue_dwell_seconds = new_config["queue_dwell_seconds"]
        if "queue_alert_people_threshold" in new_config:
            self.queue_alert_people_threshold = new_config["queue_alert_people_threshold"]
        if "queue_alert_duration_seconds" in new_config:
            self.queue_alert_duration_seconds = new_config["queue_alert_duration_seconds"]
        if "max_allowed_wait_seconds" in new_config:
            self.max_allowed_wait_seconds = new_config["max_allowed_wait_seconds"]
        if "cashier_count" in new_config:
            self.cashier_count = max(1, new_config["cashier_count"])
        if "service_rate_per_cashier_per_minute" in new_config:
            self.service_rate_per_cashier_per_minute = max(0.1, new_config["service_rate_per_cashier_per_minute"])
            
        self.logger.info("[%s] Configuración en caliente aplicada exitosamente.", self.camera_id)
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False
