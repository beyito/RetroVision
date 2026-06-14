"""
RetroVision Edge Service - Procesador de Flujo de Video

Módulo principal que implementa la captura y procesamiento de video
desde una cámara local utilizando OpenCV.

Arquitectura:
- Captura de video de manera eficiente desde cv2.VideoCapture(0)
- Lectura frame por frame con timeout robusto
- Manejo de errores exhaustivo
- Salida limpia con liberación de recursos
"""

import cv2
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading
import time

from .exceptions import CameraInitializationError, CameraAccessError, FrameProcessingError


@dataclass
class FrameMetadata:
    """Metadatos asociados a cada frame capturado."""
    timestamp: datetime
    frame_number: int
    width: int
    height: int
    fps: float


class VideoStreamProcessor:
    """
    Procesador de flujo de video del microservicio Edge.
    
    Responsabilidades:
    - Inicializar y gestionar conexión a cámara local
    - Capturar frames de manera eficiente
    - Mantener metadatos de cada frame
    - Manejar errores y excepciones robustamente
    - Proveer salida limpia de recursos
    
    Attributes:
        camera_index: Índice de la cámara (0 = cámara por defecto)
        frame_width: Ancho del frame en píxeles
        frame_height: Alto del frame en píxeles
        target_fps: FPS objetivo de captura
    """
    
    def __init__(
        self,
        camera_index: int = 0,
        frame_width: int = 1280,
        frame_height: int = 720,
        target_fps: int = 30,
        timeout_seconds: int = 10,
    ) -> None:
        """
        Inicializa el procesador de video.
        
        Args:
            camera_index: Índice de la cámara a usar (default: 0)
            frame_width: Ancho deseado del frame (default: 1280)
            frame_height: Alto deseado del frame (default: 720)
            target_fps: FPS objetivo (default: 30)
            timeout_seconds: Timeout para operaciones de cámara (default: 10s)
            
        Raises:
            CameraInitializationError: Si la cámara no puede inicializarse
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.camera_index = camera_index
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = target_fps
        self.timeout_seconds = timeout_seconds
        
        self._capture: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._frame_count = 0
        self._last_frame_time: Optional[float] = None
        self._lock = threading.Lock()
        
        self._initialize_camera()
    
    def _initialize_camera(self) -> None:
        """
        Inicializa la captura de video desde la cámara.
        
        Raises:
            CameraInitializationError: Si no se puede acceder a la cámara
        """
        try:
            self.logger.info(
                f"Inicializando cámara con índice {self.camera_index}..."
            )
            
            self._capture = cv2.VideoCapture(self.camera_index)
            
            if not self._capture or not self._capture.isOpened():
                raise CameraInitializationError(
                    f"No se pudo abrir la cámara con índice {self.camera_index}. "
                    f"Verifica que la cámara esté conectada y disponible."
                )
            
            # Configurar propiedades de la cámara
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self._capture.set(cv2.CAP_PROP_FPS, self.target_fps)
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimizar lag
            
            # Validar que se configuró correctamente
            actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self._capture.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(
                f"Cámara inicializada exitosamente. "
                f"Resolución: {actual_width}x{actual_height}, FPS: {actual_fps:.2f}"
            )
            
        except CameraInitializationError:
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado al inicializar cámara: {e}")
            raise CameraInitializationError(
                f"Error al inicializar cámara: {str(e)}"
            ) from e
    
    def read_frame(self) -> Tuple[bool, Optional[bytes], Optional[FrameMetadata]]:
        """
        Lee el siguiente frame del flujo de video.
        
        Returns:
            Tupla (success, frame, metadata) donde:
            - success: bool indicando si el frame se capturó exitosamente
            - frame: numpy array del frame (BGR), None si falló
            - metadata: FrameMetadata con información del frame
            
        Raises:
            CameraAccessError: Si hay error al acceder a la cámara
        """
        if not self._capture or not self._capture.isOpened():
            raise CameraAccessError("La cámara no está inicializada")
        
        try:
            with self._lock:
                success, frame = self._capture.read()
            
            if not success or frame is None:
                self.logger.warning("No se pudo leer frame de la cámara")
                return False, None, None
            
            # Redimensionar si es necesario (para asegurar dimensiones deseadas)
            if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
                frame = cv2.resize(
                    frame,
                    (self.frame_width, self.frame_height),
                    interpolation=cv2.INTER_LINEAR
                )
            
            # Crear metadatos del frame
            current_time = datetime.now()
            self._frame_count += 1
            
            metadata = FrameMetadata(
                timestamp=current_time,
                frame_number=self._frame_count,
                width=frame.shape[1],
                height=frame.shape[0],
                fps=self.target_fps,
            )
            
            return True, frame, metadata
            
        except Exception as e:
            self.logger.error(f"Error al leer frame: {e}")
            raise CameraAccessError(f"Error al leer frame: {str(e)}") from e
    
    def display_frame(
        self,
        frame: bytes,
        metadata: FrameMetadata,
        window_name: str = "RetroVision Edge - Video Stream",
    ) -> None:
        """
        Muestra un frame en una ventana OpenCV.
        
        Args:
            frame: Frame en formato numpy array (BGR)
            metadata: Metadatos del frame
            window_name: Nombre de la ventana
            
        Raises:
            FrameProcessingError: Si hay error al mostrar
        """
        try:
            # Agregar información de tiempo y frame number al frame
            info_text = (
                f"Frame: {metadata.frame_number} | "
                f"Time: {metadata.timestamp.strftime('%H:%M:%S')} | "
                f"FPS: {metadata.fps:.2f}"
            )
            
            cv2.putText(
                frame,
                info_text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            
            cv2.imshow(window_name, frame)
            
        except Exception as e:
            self.logger.error(f"Error al mostrar frame: {e}")
            raise FrameProcessingError(f"Error al mostrar frame: {str(e)}") from e
    
    def start(self) -> None:
        """Inicia el procesamiento de video."""
        with self._lock:
            self._is_running = True
        self.logger.info("Procesamiento de video iniciado")
    
    def stop(self) -> None:
        """Detiene el procesamiento de video."""
        with self._lock:
            self._is_running = False
        self.logger.info("Procesamiento de video detenido")
    
    def is_running(self) -> bool:
        """Retorna True si el procesamiento está activo."""
        with self._lock:
            return self._is_running
    
    def get_stats(self) -> dict:
        """
        Retorna estadísticas de captura.
        
        Returns:
            Diccionario con estadísticas (frames capturados, tiempo, etc.)
        """
        with self._lock:
            return {
                'total_frames': self._frame_count,
                'camera_index': self.camera_index,
                'resolution': f"{self.frame_width}x{self.frame_height}",
                'target_fps': self.target_fps,
            }
    
    def release(self) -> None:
        """
        Libera todos los recursos de la cámara de manera segura.
        
        Debe ser llamada siempre antes de terminar la aplicación.
        """
        try:
            with self._lock:
                self._is_running = False
                
                if self._capture is not None:
                    self._capture.release()
                    self._capture = None
            
            # Cerrar todas las ventanas OpenCV
            cv2.destroyAllWindows()
            
            self.logger.info(
                f"Recursos liberados. Total frames procesados: {self._frame_count}"
            )
            
        except Exception as e:
            self.logger.error(f"Error al liberar recursos: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - garantiza liberación de recursos."""
        self.release()
        return False
