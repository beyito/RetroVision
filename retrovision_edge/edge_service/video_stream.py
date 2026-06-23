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
from pathlib import Path
from typing import Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
import threading
import time
import numpy as np
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
    - Inicializar y gestionar conexión a webcam, stream RTSP o archivo
    - Capturar frames de manera eficiente
    - Mantener metadatos de cada frame
    - Manejar errores y excepciones robustamente
    - Proveer salida limpia de recursos
    
    Attributes:
        camera_index: Índice de la cámara (compatibilidad hacia atrás)
        video_source: Fuente de video normalizada (webcam, RTSP o archivo)
        frame_width: Ancho del frame en píxeles
        frame_height: Alto del frame en píxeles
        target_fps: FPS objetivo de captura
    """
    
    def __init__(
        self,
        camera_index: int = 0,
        video_source: Optional[Union[int, str]] = None,
        frame_width: int = 1280,
        frame_height: int = 720,
        target_fps: int = 30,
        timeout_seconds: int = 10,
    ) -> None:
        """
        Inicializa el procesador de video.
        
        Args:
            camera_index: Índice de la cámara a usar (default: 0)
            video_source: Fuente de video. Puede ser:
                - int: webcam local
                - str RTSP: rtsp://...
                - str path: ruta a archivo de video
            frame_width: Ancho deseado del frame (default: 1280)
            frame_height: Alto deseado del frame (default: 720)
            target_fps: FPS objetivo (default: 30)
            timeout_seconds: Timeout para operaciones de cámara (default: 10s)
            
        Raises:
            CameraInitializationError: Si la cámara no puede inicializarse
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.camera_index = camera_index
        self.video_source = self._normalize_video_source(
            video_source if video_source is not None else camera_index
        )
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.target_fps = target_fps
        self.timeout_seconds = timeout_seconds
        
        self._capture: Optional[cv2.VideoCapture] = None
        self._is_running = False
        self._frame_count = 0
        self._last_frame_time: Optional[float] = None
        self._lock = threading.Lock()
        
        # Variables para captura en hilo de fondo (evita acumulación de lag)
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_success = False
        self._capture_thread: Optional[threading.Thread] = None
        self._thread_lock = threading.Lock()
        
        self._initialize_camera()

    @staticmethod
    def _normalize_video_source(video_source: Union[int, str]) -> Union[int, str]:
        """Normaliza la fuente de video manteniendo compatibilidad con webcam local."""
        if isinstance(video_source, int):
            return video_source

        normalized = str(video_source).strip()
        if normalized == "":
            return 0

        try:
            return int(normalized)
        except ValueError:
            return normalized

    def _describe_video_source(self) -> str:
        """Retorna una descripción legible de la fuente configurada."""
        if isinstance(self.video_source, int):
            return f"webcam local (índice {self.video_source})"

        lower_source = self.video_source.lower()
        if lower_source.startswith("rtsp://"):
            return f"stream RTSP ({self.video_source})"

        return f"archivo de video ({self.video_source})"
    
    def _initialize_camera(self) -> None:
        """
        Inicializa la captura de video desde la fuente configurada.
        
        Raises:
            CameraInitializationError: Si no se puede acceder a la fuente
        """
        try:
            source_description = self._describe_video_source()
            self.logger.info(f"Inicializando fuente de video: {source_description}...")
            
            self._capture = cv2.VideoCapture(self.video_source)
            
            if not self._capture or not self._capture.isOpened():
                raise CameraInitializationError(
                    f"No se pudo abrir la fuente de video configurada: {source_description}. "
                    "Verifica que la webcam, stream RTSP o archivo estén disponibles."
                )
            
            # Configurar propiedades cuando la fuente es webcam o RTSP.
            # En archivos, OpenCV puede ignorar estas propiedades o romper el timing natural.
            if not self._is_video_file_source():
                self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
                self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
                self._capture.set(cv2.CAP_PROP_FPS, self.target_fps)
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimizar lag
            
            actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self._capture.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(
                f"Fuente de video inicializada exitosamente. "
                f"Resolución: {actual_width}x{actual_height}, FPS: {actual_fps:.2f}"
            )
            
        except CameraInitializationError:
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado al inicializar la fuente de video: {e}")
            raise CameraInitializationError(
                f"Error al inicializar fuente de video: {str(e)}"
            ) from e

    def _is_video_file_source(self) -> bool:
        """Retorna True si la fuente parece ser un archivo de video local."""
        if isinstance(self.video_source, int):
            return False

        lower_source = self.video_source.lower()
        if lower_source.startswith(("rtsp://", "http://", "https://")):
            return False

        return Path(self.video_source).suffix.lower() in {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".wmv",
            ".m4v",
        }
    
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray], Optional[FrameMetadata]]:
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
            raise CameraAccessError("La fuente de video no está inicializada")
        
        try:
            if self._is_video_file_source():
                with self._lock:
                    success, frame = self._capture.read()
            else:
                with self._thread_lock:
                    success = self._latest_success
                    frame = self._latest_frame
                
                # Pequeña espera en el primer frame si el hilo de fondo aún no ha arrancado
                if (not success or frame is None) and self._is_running:
                    time.sleep(0.05)
                    with self._thread_lock:
                        success = self._latest_success
                        frame = self._latest_frame
            
            if not success or frame is None:
                self.logger.warning("No se pudo leer frame de la fuente de video")
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
        
        # Iniciar hilo de captura en tiempo real si no es un archivo local
        if not self._is_video_file_source():
            with self._thread_lock:
                self._latest_frame = None
                self._latest_success = False
            self._capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
            self._capture_thread.start()
            self.logger.info("Hilo de captura en tiempo real iniciado para vaciado de buffer")
            
        self.logger.info("Procesamiento de video iniciado")
    
    def _capture_worker(self) -> None:
        """Hilo de fondo que lee continuamente de VideoCapture para vaciar el buffer de OpenCV."""
        self.logger.info("Iniciando bucle de captura en tiempo real (background)...")
        while True:
            with self._lock:
                if not self._is_running:
                    break
            
            try:
                if self._capture and self._capture.isOpened():
                    success, frame = self._capture.read()
                    if success and frame is not None:
                        with self._thread_lock:
                            self._latest_frame = frame
                            self._latest_success = True
                    else:
                        time.sleep(0.005)
                else:
                    time.sleep(0.1)
            except Exception as e:
                self.logger.warning(f"Error en hilo de lectura de cámara: {e}")
                time.sleep(0.1)
        self.logger.info("Hilo de captura en tiempo real finalizado.")
    
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
                'video_source': self.video_source,
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
            
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=2.0)
                self._capture_thread = None
                
            with self._lock:
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
