"""
RetroVision Edge Service - Video Ring Buffer

Módulo para almacenar frames en una memoria circular (ring buffer).
Mantiene los últimos N segundos de video en RAM para exportación rápida
en caso de evento de riesgo.
"""

import logging
from typing import Optional, Tuple, Deque
from collections import deque
from dataclasses import dataclass

import numpy as np

@dataclass
class BufferStats:
    """Estadísticas del ring buffer."""
    current_size: int  # Frames almacenados
    max_size: int  # Capacidad máxima
    memory_usage_mb: float  # Uso estimado de memoria
    utilization_percent: float  # Porcentaje de uso


class RingBuffer:
    """
    Buffer circular para almacenar frames de video.
    
    Utiliza collections.deque con maxlen para automáticamente descartar
    los frames más antiguos cuando se alcanza la capacidad.
    
    Optimizado para Edge: almacena frames originales (sin anotaciones)
    de forma eficiente en RAM.
    
    Attributes:
        max_size: Número máximo de frames a almacenar
        fps: Fotogramas por segundo (para cálculos informativos)
        retention_seconds: Segundos de video almacenado
    """
    
    def __init__(
        self,
        fps: int = 30,
        retention_seconds: int = 30,
    ) -> None:
        """
        Inicializa el ring buffer.
        
        Args:
            fps: Fotogramas por segundo de la cámara
            retention_seconds: Segundos de video a retener (default: 30)
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.fps = fps
        self.retention_seconds = retention_seconds
        
        # Calcular capacidad máxima
        self.max_size = fps * retention_seconds
        
        # Buffer circular: deque automáticamente descarta frames viejos
        self._buffer: Deque[np.ndarray] = deque(maxlen=self.max_size)
        
        self.logger.info(
            f"RingBuffer inicializado: {self.max_size} frames "
            f"({retention_seconds}s @ {fps}fps)"
        )
    
    def add_frame(self, frame: np.ndarray) -> None:
        """
        Añade un frame al buffer.
        
        Si el buffer está lleno, automáticamente descarta el frame más antiguo.
        
        Args:
            frame: Frame en formato numpy array (se copia para evitar referencias)
        """
        if frame is None or frame.size == 0:
            self.logger.warning("Se intentó añadir un frame inválido")
            return
        
        # Copiar frame para evitar problemas con modificaciones posteriores
        frame_copy = frame.copy()
        self._buffer.append(frame_copy)
    
    def get_frames(self) -> list[np.ndarray]:
        """
        Retorna una lista de todos los frames en el buffer.
        
        Returns:
            Lista de frames en orden cronológico (más antiguos primero)
        """
        return list(self._buffer)
    
    def get_latest_n_frames(self, n: int) -> list[np.ndarray]:
        """
        Retorna los últimos N frames del buffer.
        
        Args:
            n: Número de frames a retornar
            
        Returns:
            Lista de los últimos N frames (puede ser menor si no hay suficientes)
        """
        return list(self._buffer)[-n:] if n > 0 else []
    
    def clear(self) -> None:
        """Limpia todos los frames del buffer."""
        self._buffer.clear()
        self.logger.info("RingBuffer limpiado")
    
    def get_stats(self) -> BufferStats:
        """
        Retorna estadísticas del buffer.
        
        Returns:
            BufferStats con información de uso
        """
        current_size = len(self._buffer)
        
        # Estimar uso de memoria
        memory_usage_mb = 0.0
        if current_size > 0:
            # Estimar tamaño de frame: height * width * 3 bytes (BGR)
            sample_frame = list(self._buffer)[0]
            frame_size_bytes = sample_frame.nbytes
            total_bytes = frame_size_bytes * current_size
            memory_usage_mb = total_bytes / (1024 * 1024)  # Convertir a MB
        
        utilization = (current_size / self.max_size * 100) if self.max_size > 0 else 0
        
        return BufferStats(
            current_size=current_size,
            max_size=self.max_size,
            memory_usage_mb=memory_usage_mb,
            utilization_percent=utilization
        )
    
    def print_stats(self) -> None:
        """Imprime estadísticas formateadas."""
        stats = self.get_stats()
        self.logger.info(
            f"RingBuffer Stats: {stats.current_size}/{stats.max_size} frames "
            f"({stats.utilization_percent:.1f}% full, {stats.memory_usage_mb:.1f} MB)"
        )
    
    def is_full(self) -> bool:
        """Retorna True si el buffer está lleno."""
        return len(self._buffer) >= self.max_size
    
    def __len__(self) -> int:
        """Retorna el número de frames en el buffer."""
        return len(self._buffer)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.clear()
        return False
