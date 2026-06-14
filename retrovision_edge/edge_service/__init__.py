"""
RetroVision Edge Service - Paquete Principal

Microservicio Edge para captura y procesamiento local de video con detección de objetos.
"""

__version__ = "0.3.0"  # FASE 2 - Lógica de Riesgo y Memoria Temporal
__author__ = "RetroVision Team"

from .video_stream import VideoStreamProcessor, FrameMetadata
from .config import EdgeServiceConfig
from .exceptions import (
    RetroVisionEdgeException,
    CameraInitializationError,
    CameraAccessError,
    FrameProcessingError,
)
from .object_detector import ObjectDetector, Detection, DetectionResult
from .detection_pipeline import DetectionPipeline, PipelineStats
from .posture_estimator import PostureEstimator
from .risk_analyzer import BehaviorAnalyzer, RiskAnalysis
from .video_buffer import RingBuffer, BufferStats
from .alert_writer import AlertWriter
from .mqtt_publisher import AlertPublisher

__all__ = [
    # Phase 1: Core
    'VideoStreamProcessor',
    'FrameMetadata',
    'EdgeServiceConfig',
    'RetroVisionEdgeException',
    'CameraInitializationError',
    'CameraAccessError',
    'FrameProcessingError',
    'ObjectDetector',
    'Detection',
    'DetectionResult',
    'DetectionPipeline',
    'PipelineStats',
    # Phase 2: Risk & Memory
    'PostureEstimator',
    'BehaviorAnalyzer',
    'RiskAnalysis',
    'RingBuffer',
    'BufferStats',
    'AlertWriter',
    'AlertPublisher',
]
