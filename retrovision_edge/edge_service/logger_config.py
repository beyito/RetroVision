"""
RetroVision Edge Service - Configuración de Logging

Módulo para configurar el sistema de logging centralizado.
"""

import logging
import logging.handlers
import os
from typing import Optional


def setup_logger(
    name: str,
    config_dict: dict,
) -> logging.Logger:
    """
    Configura un logger con manejo de archivos y consola.
    
    Args:
        name: Nombre del logger.
        config_dict: Diccionario con configuración (level, log_file, etc.).
        
    Returns:
        Logger configurado.
        
    Raises:
        OSError: Si no se puede crear el directorio de logs.
    """
    logger = logging.getLogger(name)
    
    # Evitar agregar handlers múltiples
    if logger.hasHandlers():
        return logger
    
    log_level = getattr(logging, config_dict.get('level', 'INFO'))
    logger.setLevel(log_level)
    
    # Crear directorio de logs si no existe
    log_dir = os.path.dirname(config_dict.get('log_file', 'logs/app.log'))
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            raise OSError(f"No se pudo crear directorio de logs: {e}") from e
    
    # Formato de logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para archivo (con rotación)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=config_dict.get('log_file', 'logs/app.log'),
        maxBytes=config_dict.get('max_bytes', 10 * 1024 * 1024),
        backupCount=config_dict.get('backup_count', 5),
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
