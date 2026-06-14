"""
RetroVision Edge Service - Estimador de Postura con MediaPipe

Módulo dedicado a la estimación de postura (pose) usando MediaPipe.
Diseñado para uso en Edge: `model_complexity=0` por defecto.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np
import cv2

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except Exception as e:
    print(f"Error cargando MediaPipe: {e}")
    MEDIAPIPE_AVAILABLE = False

from .exceptions import ConfigurationError, FrameProcessingError

Landmark = Tuple[float, float, float]  # (x_abs, y_abs, visibility)


class PostureEstimator:
    """
    Estimador de postura basado en MediaPipe Pose.

    Uso:
        estimator = PostureEstimator(model_complexity=0)
        landmarks_norm = estimator.estimate(roi_rgb)
        landmarks_abs = estimator.norm_to_absolute(landmarks_norm, roi_origin, roi_size)
        estimator.draw_landmarks_on_frame(frame, landmarks_abs)
    """

    def __init__(
        self,
        model_complexity: int = 0,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

        if not MEDIAPIPE_AVAILABLE:
            raise ConfigurationError(
                "MediaPipe no está instalado o falló la importación. Ejecuta: pip install mediapipe"
            )

        try:
            self.mp = mp
            self.pose = self.mp.solutions.pose.Pose(
                model_complexity=model_complexity,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            self.connections = self.mp.solutions.pose.POSE_CONNECTIONS
            self.logger.info("MediaPipe Pose inicializado (model_complexity=%s)", model_complexity)
        except Exception as e:
            self.logger.error("Error inicializando MediaPipe Pose: %s", e)
            raise FrameProcessingError(f"No se pudo inicializar MediaPipe Pose: {e}") from e

    def estimate(self, image_rgb: np.ndarray) -> Optional[List[Tuple[float, float, float]]]:
        """
        Ejecuta MediaPipe sobre un ROI en formato RGB y devuelve landmarks normalizados
        relativos al ROI (x, y en 0..1, visibility).

        Args:
            image_rgb: Imagen RGB del ROI (numpy array)

        Returns:
            Lista de tuplas (x_norm, y_norm, visibility) o None si no hay landmarks
        """
        if image_rgb is None or image_rgb.size == 0:
            return None

        try:
            results = self.pose.process(image_rgb)
            if results.pose_landmarks is None:
                return None

            landmarks = []
            for lm in results.pose_landmarks.landmark:
                landmarks.append((lm.x, lm.y, lm.visibility))

            return landmarks
        except Exception as e:
            self.logger.error("Error durante estimación de postura: %s", e)
            return None

    def norm_to_absolute(
        self,
        landmarks_norm: List[Tuple[float, float, float]],
        roi_origin: Tuple[int, int],
        roi_size: Tuple[int, int],
    ) -> List[Landmark]:
        """
        Convierte landmarks normalizados (0..1) relativos al ROI a coordenadas
        absolutas en el frame original.

        Args:
            landmarks_norm: Lista de (x_norm, y_norm, visibility)
            roi_origin: (x_offset, y_offset) esquina superior izquierda del ROI
            roi_size: (width, height) del ROI

        Returns:
            Lista de landmarks en coordenadas absolutas: (x_abs, y_abs, visibility)
        """
        x_off, y_off = roi_origin
        w, h = roi_size
        abs_landmarks: List[Landmark] = []

        for x_norm, y_norm, vis in landmarks_norm:
            x_abs = int(x_off + max(0.0, min(1.0, x_norm)) * w)
            y_abs = int(y_off + max(0.0, min(1.0, y_norm)) * h)
            abs_landmarks.append((x_abs, y_abs, float(vis)))

        return abs_landmarks

    def draw_landmarks_on_frame(
        self,
        frame: np.ndarray,
        landmarks_abs: List[Landmark],
        color: Tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2,
        circle_radius: int = 3,
    ) -> None:
        """
        Dibuja los landmarks y conexiones sobre el frame principal.

        Args:
            frame: Frame BGR donde dibujar
            landmarks_abs: Lista de (x_abs, y_abs, visibility)
        """
        if not landmarks_abs:
            return

        try:
            # Dibujar puntos
            for (x, y, vis) in landmarks_abs:
                if x is None or y is None:
                    continue
                cv2.circle(frame, (int(x), int(y)), circle_radius, color, -1)

            # Dibujar conexiones usando MediaPipe POSE_CONNECTIONS
            for connection in self.connections:
                # connection may contain enums or ints; normalize to int indices
                try:
                    start_idx = int(connection[0].value)  # enum
                    end_idx = int(connection[1].value)
                except Exception:
                    try:
                        start_idx = int(connection[0])
                        end_idx = int(connection[1])
                    except Exception:
                        continue

                if start_idx < len(landmarks_abs) and end_idx < len(landmarks_abs):
                    x1, y1, v1 = landmarks_abs[start_idx]
                    x2, y2, v2 = landmarks_abs[end_idx]
                    if v1 > 0.1 and v2 > 0.1:
                        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
        except Exception as e:
            self.logger.error("Error dibujando landmarks: %s", e)
            # No propagar excepciones de dibujo

    def release(self) -> None:
        """Libera recursos de MediaPipe."""
        try:
            if hasattr(self, "pose") and self.pose is not None:
                self.pose.close()
                self.pose = None
                self.logger.info("MediaPipe Pose liberado")
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False