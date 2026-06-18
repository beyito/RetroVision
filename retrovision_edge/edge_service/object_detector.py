"""
RetroVision Edge Service - Detector de Objetos con YOLOv8

Módulo dedicado a la detección de objetos utilizando YOLOv8.
Responsabilidad: Inferencia de modelos y filtrado de detecciones.

Nota: Solo detecta PERSONAS (clase 0 en dataset COCO).
Futuras extensiones: armas, comportamientos anómalos, etc.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import cv2

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from .exceptions import (
    RetroVisionEdgeException,
    ConfigurationError,
    FrameProcessingError,
)


@dataclass
class Detection:
    """
    Representa una detección única de objeto.
    
    Attributes:
        x1: Coordenada X superior izquierda del bounding box
        y1: Coordenada Y superior izquierda del bounding box
        x2: Coordenada X inferior derecha del bounding box
        y2: Coordenada Y inferior derecha del bounding box
        confidence: Score de confianza (0.0 - 1.0)
        class_id: ID de la clase detectada (0=persona en COCO)
        class_name: Nombre legible de la clase
    """
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int
    class_name: str
    track_id: Optional[int] = None
    # Landmarks result from posture estimator: list of (x_abs, y_abs, visibility)
    landmarks: Optional[List[Tuple[int, int, float]]] = None
    # Risk score from BehaviorAnalyzer (0.0-1.0)
    risk_score: float = 0.0
    
    def width(self) -> int:
        """Retorna el ancho del bounding box."""
        return self.x2 - self.x1
    
    def height(self) -> int:
        """Retorna el alto del bounding box."""
        return self.y2 - self.y1
    
    def area(self) -> int:
        """Retorna el área del bounding box."""
        return self.width() * self.height()
    
    def center(self) -> Tuple[int, int]:
        """Retorna el centro del bounding box."""
        cx = (self.x1 + self.x2) // 2
        cy = (self.y1 + self.y2) // 2
        return (cx, cy)


@dataclass
class DetectionResult:
    """
    Resultado completo de una detección en un frame.
    
    Attributes:
        detections: Lista de Detection objects
        frame_shape: Forma del frame (height, width, channels)
        inference_time_ms: Tiempo de inferencia en milisegundos
        model_name: Nombre del modelo utilizado
    """
    detections: List[Detection]
    frame_shape: Tuple[int, int, int]
    inference_time_ms: float
    model_name: str
    
    def count(self) -> int:
        """Retorna cantidad de detecciones."""
        return len(self.detections)
    
    def get_by_confidence(self, min_confidence: float = 0.5) -> List[Detection]:
        """Filtra detecciones por confianza mínima."""
        return [d for d in self.detections if d.confidence >= min_confidence]


class ObjectDetector:
    """
    Detector de objetos utilizando YOLOv8.
    
    Responsabilidades:
    - Cargar modelo YOLOv8 (nano para Edge)
    - Realizar inferencia en frames
    - Filtrar detecciones (solo personas)
    - Retornar resultados en formato estructurado
    
    Attributes:
        model_name: Nombre del modelo YOLOv8 a usar
        confidence_threshold: Umbral mínimo de confianza para detecciones
        device: Dispositivo de ejecución ('cpu', 'gpu', 'mps')
    """
    
    WEAPON_CLASSES = {"knife", "scissors", "pistol", "handgun", "firearm", "gun", "rifle"}
    
    # Solo detectar personas
    TARGET_CLASS_ID = 0
    TARGET_CLASS_NAME = "person"
    
    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        device: str = "cpu",
    ) -> None:
        """
        Inicializa el detector de objetos.
        
        Args:
            model_name: Nombre del modelo YOLOv8 ('yolov8n', 'yolov8s', etc.)
                       La extensión '.pt' se agrega automáticamente
            confidence_threshold: Umbral mínimo de confianza (0.0 - 1.0)
            device: Dispositivo de ejecución ('cpu', 'gpu', 'mps', 'cuda')
            
        Raises:
            ConfigurationError: Si YOLO no está disponible
            FrameProcessingError: Si el modelo no se puede cargar
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if not YOLO_AVAILABLE:
            raise ConfigurationError(
                "Ultralytics no está instalado. "
                "Ejecuta: pip install ultralytics"
            )
        
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.device = device
        self._model = None
        
        self._load_model()
    
    def _load_model(self) -> None:
        """
        Carga el modelo YOLOv8 desde ultralytics.
        
        Raises:
            FrameProcessingError: Si el modelo no se puede descargar o cargar
        """
        try:
            self.logger.info(
                f"Cargando modelo YOLOv8: {self.model_name} (device={self.device})..."
            )
            
            self._model = YOLO(self.model_name)
            
            if self._model is None:
                raise FrameProcessingError(
                    f"No se pudo cargar el modelo {self.model_name}"
                )
            
            # Validar que el modelo se cargó correctamente
            self._model.to(self.device)
            
            self.logger.info(
                f"Modelo YOLOv8 cargado exitosamente. "
                f"Resolución de entrada: {640}"
            )
            
        except Exception as e:
            self.logger.error(f"Error al cargar modelo YOLOv8: {e}")
            raise FrameProcessingError(
                f"No se pudo cargar el modelo YOLOv8: {str(e)}"
            ) from e
    
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Realiza detección de objetos en un frame.
        
        Args:
            frame: Frame en formato numpy array (BGR de OpenCV)
            
        Returns:
            DetectionResult con detecciones filtradas (solo personas)
            
        Raises:
            FrameProcessingError: Si la inferencia falla
        """
        if self._model is None:
            raise FrameProcessingError("El modelo no ha sido cargado")
        
        if frame is None or frame.size == 0:
            raise FrameProcessingError("Frame inválido o vacío")
        
        try:
            # Realizar inferencia (retorna lista con resultados)
            import time
            start_time = time.perf_counter()
            
            # Ejecutar track con un umbral bajo de confianza para capturar armas,
            # luego aplicaremos el umbral dinámico por clase en _process_results.
            conf_val = min(0.40, self.confidence_threshold)
            # conf_val = 0.10

            results = self._model.track(
                source=frame,
                persist=True,
                conf=conf_val,
                verbose=False,  # No imprimir en console
                device=self.device,
            )
            
            inference_time = (time.perf_counter() - start_time) * 1000  # ms
            
            # Procesar resultados
            detections = self._process_results(results, frame.shape)
            
            return DetectionResult(
                detections=detections,
                frame_shape=frame.shape,
                inference_time_ms=inference_time,
                model_name=self.model_name,
            )
            
        except Exception as e:
            self.logger.error(f"Error durante inferencia: {e}")
            raise FrameProcessingError(f"Error en detección: {str(e)}") from e
    
    def _process_results(
        self,
        results,
        frame_shape: Tuple[int, int, int],
    ) -> List[Detection]:
        """
        Procesa resultados de YOLO y filtra solo personas.
        
        Args:
            results: Resultados del modelo YOLO
            frame_shape: Forma del frame (height, width, channels)
            
        Returns:
            Lista de Detection objects filtrados
        """
        detections = []
        
        if not results or len(results) == 0:
            return detections
        
        result = results[0]  # Primer (único) frame
        
        if result.boxes is None or len(result.boxes) == 0:
            return detections
        
        # Iterar sobre detecciones
        for box in result.boxes:
            # Obtener valores
            coords = box.xyxy[0].cpu().numpy()  # [x1, y1, x2, y2]
            confidence = float(box.conf[0].cpu().numpy())
            class_id = int(box.cls[0].cpu().numpy())
            
            # Obtener nombre de clase dinámicamente desde el modelo
            class_name = "unknown"
            if hasattr(result, "names") and result.names and class_id in result.names:
                class_name = result.names[class_id]
            else:
                class_name = {0: "person", 43: "knife", 76: "scissors"}.get(class_id, "unknown")
            
            # Normalizar nombre para comparación
            class_name_lower = class_name.lower()
            
            is_person = class_name_lower in ("person", "people")
            is_weapon = class_name_lower in self.WEAPON_CLASSES or any(w in class_name_lower for w in self.WEAPON_CLASSES)
            is_mask = class_name_lower in ("mask", "no-mask")
            
            if not (is_person or is_weapon or is_mask):
                continue
            
            # Aplicar umbral de confianza específico por clase
            if is_person:
                if confidence < self.confidence_threshold:
                    continue
            else:
                if confidence < 0.50:
                    continue
            
            # Convertir coordenadas a enteros y validar límites
            x1, y1, x2, y2 = self._validate_coordinates(
                coords, frame_shape
            )
            
            # Obtener ID de track si existe
            track_id = None
            if box.id is not None:
                try:
                    track_id = int(box.id[0].cpu().numpy())
                except Exception:
                    pass
            
            detection = Detection(
                x1=int(x1),
                y1=int(y1),
                x2=int(x2),
                y2=int(y2),
                confidence=confidence,
                class_id=class_id,
                class_name=class_name,
                track_id=track_id,
            )
            
            detections.append(detection)
        
        return detections
    
    def _validate_coordinates(
        self,
        coords: np.ndarray,
        frame_shape: Tuple[int, int, int],
    ) -> Tuple[float, float, float, float]:
        """
        Valida que las coordenadas estén dentro del frame.
        
        Args:
            coords: Array de 4 elementos [x1, y1, x2, y2]
            frame_shape: Forma del frame
            
        Returns:
            Tupla de coordenadas validadas
        """
        x1, y1, x2, y2 = coords
        height, width = frame_shape[0], frame_shape[1]
        
        # Limitar a bordes del frame
        x1 = max(0, min(x1, width - 1))
        y1 = max(0, min(y1, height - 1))
        x2 = max(x1 + 1, min(x2, width))
        y2 = max(y1 + 1, min(y2, height))
        
        return x1, y1, x2, y2
    
    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        color: Tuple[int, int, int] = (0, 255, 0),  # Verde en BGR
        thickness: int = 2,
        font_scale: float = 0.7,
    ) -> np.ndarray:
        """
        Dibuja bounding boxes sobre el frame.
        
        Args:
            frame: Frame en formato numpy array
            detections: Lista de Detection objects
            color: Color BGR para bounding boxes (default: verde)
            thickness: Grosor de las líneas
            font_scale: Escala de fuente para el texto
            
        Returns:
            Frame con bounding boxes dibujados
        """
        frame_copy = frame.copy()
        
        for detection in detections:
            # Color dinámico: rojo para amenazas (armas, máscara), color estándar (verde) para personas y no-máscara
            is_weapon_det = detection.class_name.lower() in self.WEAPON_CLASSES or any(w in detection.class_name.lower() for w in self.WEAPON_CLASSES)
            is_mask_threat = detection.class_name.lower() == "mask"
            det_color = (0, 0, 255) if (is_weapon_det or is_mask_threat) else color

            # Dibujar rectángulo
            cv2.rectangle(
                frame_copy,
                (detection.x1, detection.y1),
                (detection.x2, detection.y2),
                det_color,
                thickness,
            )
            
            # Preparar texto con clase y confianza
            if detection.track_id is not None:
                label = f"ID: {detection.track_id} | {detection.class_name} {detection.confidence:.2f}"
            else:
                label = f"{detection.class_name} {detection.confidence:.2f}"
            
            # Obtener tamaño del texto para background
            text_size = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
            )[0]
            
            # Dibujar background para texto
            cv2.rectangle(
                frame_copy,
                (detection.x1, detection.y1 - text_size[1] - 4),
                (detection.x1 + text_size[0], detection.y1),
                det_color,
                -1,  # Relleno
            )
            
            # Dibujar texto
            cv2.putText(
                frame_copy,
                label,
                (detection.x1, detection.y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (0, 0, 0),  # Negro
                thickness,
            )
            
            # Opcional: Dibujar punto en el centro
            cx, cy = detection.center()
            cv2.circle(frame_copy, (cx, cy), 3, det_color, -1)
        
        return frame_copy
    
    def get_model_info(self) -> dict:
        """
        Retorna información del modelo.
        
        Returns:
            Diccionario con información del modelo
        """
        if self._model is None:
            return {"status": "not_loaded"}
        
        return {
            "model_name": self.model_name,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "target_class": self.TARGET_CLASS_NAME,
            "input_size": 640,
        }
    
    def release(self) -> None:
        """
        Libera recursos del modelo.
        """
        if self._model is not None:
            self._model = None
            self.logger.info("Modelo YOLOv8 liberado")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False
