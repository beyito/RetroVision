"""
RetroVision Edge Service - Excepciones Personalizadas

Módulo que define las excepciones específicas del microservicio Edge.
"""


class RetroVisionEdgeException(Exception):
    """Excepción base para el microservicio Edge."""
    pass


class CameraInitializationError(RetroVisionEdgeException):
    """Se lanza cuando no se puede inicializar la cámara."""
    pass


class CameraAccessError(RetroVisionEdgeException):
    """Se lanza cuando hay un error al acceder a la cámara."""
    pass


class FrameProcessingError(RetroVisionEdgeException):
    """Se lanza cuando hay un error al procesar frames."""
    pass


class ConfigurationError(RetroVisionEdgeException):
    """Se lanza cuando hay un error de configuración."""
    pass
