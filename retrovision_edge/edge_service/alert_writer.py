"""
RetroVision Edge Service - Alert Video Writer

Módulo para exportar clips de video de forma asíncrona cuando se dispara
una alerta de alto riesgo.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import numpy as np
import cv2


class AlertWriter:
    """
    Escritor de alertas (videos) de forma asíncrona.
    
    Cuando se detecta un evento de riesgo, exporta los frames del RingBuffer
    a un archivo .mp4. Utiliza threading para no bloquear el pipeline en
    tiempo real.
    
    Attributes:
        alerts_dir: Directorio donde guardar videos
        cooldown_seconds: Tiempo mínimo entre alertas (evita spam)
        codec: Codec de video (MJPEG o H264)
        fps: Fotogramas por segundo para el video guardado
    """
    
    def __init__(
        self,
        alerts_dir: str = "alerts",
        cooldown_seconds: float = 30.0,
        fps: int = 30,
        backend_api_base_url: str = "",
        edge_node_id: str = "",
        edge_api_key: str = "",
        camera_id: str = "",
    ) -> None:
        """
        Inicializa el escritor de alertas.
        
        Args:
            alerts_dir: Directorio para guardar videos
            cooldown_seconds: Tiempo de enfriamiento entre alertas
            fps: Fotogramas por segundo para el video exportado
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.alerts_dir = Path(alerts_dir)
        self.cooldown_seconds = cooldown_seconds
        self.fps = fps
        self.backend_api_base_url = backend_api_base_url
        self.edge_node_id = edge_node_id
        self.edge_api_key = edge_api_key
        self.camera_id = camera_id
        
        # Crear directorio de alertas si no existe
        self.alerts_dir.mkdir(parents=True, exist_ok=True)
        
        # Control de cooldown
        self._last_alert_time: Optional[float] = None
        self._cooldown_lock = threading.Lock()
        
        # Thread activo para escribir video
        self._write_thread: Optional[threading.Thread] = None
        self._write_thread_stop = False
        
        self.logger.info(f"AlertWriter inicializado en {self.alerts_dir} (cooldown: {cooldown_seconds}s)")
    
    def is_alert_ready(self) -> bool:
        """
        Retorna True si ya pasó el cooldown desde la última alerta.
        
        Returns:
            bool indicando si se puede disparar una nueva alerta
        """
        with self._cooldown_lock:
            if self._last_alert_time is None:
                return True
            
            elapsed = time.time() - self._last_alert_time
            return elapsed >= self.cooldown_seconds
    
    def write_alert_async(
        self,
        frames: List[np.ndarray],
        risk_score: float,
        triggered_rules: Optional[List[str]] = None,
        zona: str = "",
    ) -> Optional[Path]:
        """
        Exporta frames a un archivo .mp4 de forma asíncrona.
        
        Lanza un thread separado para escribir el video sin bloquear
        el pipeline en tiempo real.
        
        Args:
            frames: Lista de frames a guardar
            risk_score: Score de riesgo que disparó la alerta
            triggered_rules: Reglas que dispararon la alerta
            zona: Nombre de la zona donde ocurrió la amenaza
            
        Returns:
            True si la alerta se inició exitosamente, False si está en cooldown
        """
        if not self.is_alert_ready():
            self.logger.debug("Alerta en cooldown, ignorando")
            return None
        
        # Actualizar tiempo de última alerta
        with self._cooldown_lock:
            self._last_alert_time = time.time()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        risk_level = self._get_risk_level(risk_score)
        filename = f"alert_{timestamp}_risk-{risk_level}_{risk_score:.2f}.mp4"
        filepath = self.alerts_dir / filename

        # Lanzar thread para escribir video
        self._write_thread = threading.Thread(
            target=self._write_video_thread,
            args=(frames, risk_score, triggered_rules or [], filepath, zona),
            daemon=True,
        )
        self._write_thread.start()
        
        return filepath
    
    def _write_video_thread(
        self,
        frames: List[np.ndarray],
        risk_score: float,
        triggered_rules: List[str],
        filepath: Path,
        zona: str = "",
    ) -> None:
        """
        Thread worker que escribe el video a disco.
        
        Args:
            frames: Lista de frames
            risk_score: Score de riesgo
            triggered_rules: Reglas disparadas
        """
        try:
            if not frames:
                self.logger.warning("No hay frames para guardar")
                return
            
            # Obtener dimensiones del primer frame
            height, width = frames[0].shape[:2]
            
            # Inicializar VideoWriter
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # MPEG-4 codec
            out = cv2.VideoWriter(
                str(filepath),
                fourcc,
                self.fps,
                (width, height),
            )
            
            if not out.isOpened():
                self.logger.error(f"No se pudo abrir VideoWriter para {filepath}")
                return
            
            # Escribir frames
            frames_written = 0
            for frame in frames:
                out.write(frame)
                frames_written += 1
            
            out.release()
            
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            self.logger.info(
                f"Alerta guardada: {filepath.name} "
                f"({frames_written} frames, {file_size_mb:.1f} MB, "
                f"reglas: {', '.join(triggered_rules)})"
            )
            
            # Subida directa a S3 mediante URL pre-firmada
            if self.backend_api_base_url and self.edge_node_id and self.edge_api_key:
                threading.Thread(
                    target=self._request_presigned_url_and_upload,
                    args=(filepath, risk_score, triggered_rules, zona),
                    daemon=True
                ).start()
            
        except Exception as e:
            self.logger.error(f"Error escribiendo video de alerta: {e}")

    def _request_presigned_url_and_upload(self, filepath: Path, risk_score: float, rules: List[str], zona: str = "") -> None:
        """Solicita una URL pre-firmada al backend y sube el video directamente a S3 (PUT)."""
        try:
            import json
            from urllib import request, error
            
            # 1. Solicitar URL pre-firmada del backend
            url = f"{self.backend_api_base_url.rstrip('/')}/api/alerts/presigned-url/"
            payload = {
                "camera_id": self.camera_id,
                "filename": filepath.name,
                "risk_score": float(risk_score),
                "rules_triggered": list(rules),
                "timestamp": datetime.now().isoformat(),
                "zona": zona
            }
            
            headers = {
                "X-Edge-Node-Id": self.edge_node_id,
                "X-Edge-Api-Key": self.edge_api_key,
                "Content-Type": "application/json"
            }
            
            self.logger.info(f"Solicitando URL pre-firmada de S3 para {filepath.name}...")
            
            body = json.dumps(payload).encode("utf-8")
            req = request.Request(url, data=body, headers=headers, method="POST")
            
            with request.urlopen(req, timeout=15) as response:
                res_content = response.read().decode("utf-8")
                res_data = json.loads(res_content)
                
            presigned_url = res_data.get("presigned_url")
            alert_id = res_data.get("alert_id")
            
            if not presigned_url:
                self.logger.error("No se recibió una URL pre-firmada en la respuesta del backend.")
                return
                
            # 2. Subir directamente a S3 (PUT HTTP)
            self.logger.info(f"Subiendo video directamente a S3 (PUT) para Alerta #{alert_id}...")
            
            with open(filepath, "rb") as f:
                file_data = f.read()
                
            put_headers = {
                "Content-Type": "video/mp4"
            }
            
            put_req = request.Request(presigned_url, data=file_data, headers=put_headers, method="PUT")
            with request.urlopen(put_req, timeout=60) as put_response:
                self.logger.info(f"Subida S3 completada con éxito. Código HTTP: {put_response.status}")
                
        except error.HTTPError as exc:
            self.logger.error(f"Fallo al subir a S3 (HTTPError {exc.code}): {exc.read().decode('utf-8', errors='ignore')}")
        except Exception as e:
            self.logger.error(f"Error al solicitar URL pre-firmada y subir: {e}")
    
    def _get_risk_level(self, risk_score: float) -> str:
        """
        Convierte risk_score a nivel de riesgo.
        
        Args:
            risk_score: Score entre 0.0 y 1.0
            
        Returns:
            String con nivel: LOW, MEDIUM, HIGH, CRITICAL
        """
        if risk_score < 0.2:
            return "LOW"
        elif risk_score < 0.4:
            return "MEDIUM"
        elif risk_score < 0.7:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def wait_for_pending(self, timeout_seconds: float = 10.0) -> bool:
        """
        Espera a que termine el thread de escritura actual.
        
        Args:
            timeout_seconds: Tiempo máximo de espera
            
        Returns:
            True si se completó, False si timeout
        """
        if self._write_thread is None:
            return True
        
        self._write_thread.join(timeout=timeout_seconds)
        return not self._write_thread.is_alive()
    
    def get_alerts_dir(self) -> Path:
        """Retorna el directorio de alertas."""
        return self.alerts_dir
    
    def list_alerts(self) -> List[Path]:
        """
        Lista todos los archivos de alerta guardados.
        
        Returns:
            Lista de rutas a archivos .mp4
        """
        return sorted(self.alerts_dir.glob("alert_*.mp4"))
    
    def get_alerts_stats(self) -> dict:
        """
        Retorna estadísticas de alertas.
        
        Returns:
            Dict con información de alertas guardadas
        """
        alerts = self.list_alerts()
        total_size_mb = sum(f.stat().st_size for f in alerts) / (1024 * 1024)
        
        return {
            "total_alerts": len(alerts),
            "total_size_mb": total_size_mb,
            "alerts_dir": str(self.alerts_dir),
        }
    
    def cleanup_old_alerts(self, max_age_hours: int = 24) -> int:
        """
        Elimina alertas más antiguas que max_age_hours.
        
        Args:
            max_age_hours: Máxima edad en horas
            
        Returns:
            Número de archivos eliminados
        """
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        for alert_file in self.list_alerts():
            file_age = current_time - alert_file.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    alert_file.unlink()
                    deleted_count += 1
                    self.logger.info(f"Alerta antigua eliminada: {alert_file.name}")
                except Exception as e:
                    self.logger.error(f"Error eliminando {alert_file.name}: {e}")
        
        return deleted_count
    
    def release(self) -> None:
        """Libera recursos y espera a que termine el thread de escritura."""
        self._write_thread_stop = True
        if self._write_thread and self._write_thread.is_alive():
            self._write_thread.join(timeout=5.0)
        self.logger.info("AlertWriter liberado")
