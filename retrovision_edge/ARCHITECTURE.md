"""
RetroVision Edge Service - Guía Arquitectónica

PROPÓSITO:
Documentación de decisiones arquitectónicas, patrones de diseño y consideraciones
de performance para el Microservicio Edge.
"""

# ============================================================================
# 1. DECISIONES ARQUITECTÓNICAS
# ============================================================================

## 1.1 Separación en Módulos

DECISIÓN: Dividir el código en módulos separados por responsabilidad

MÓDULOS:
- video_stream.py: Lógica de captura y procesamiento (NÚCLEO)
- config.py: Gestión de configuración
- logger_config.py: Configuración de logging
- exceptions.py: Excepciones personalizadas

BENEFICIOS:
✓ Testabilidad: Cada módulo es testeable independientemente
✓ Mantenibilidad: Cambios localizados a su responsabilidad
✓ Reutilización: Fácil importar y usar en otros proyectos
✓ Escalabilidad: Preparado para agregar módulos adicionales (MQTT, AI, etc.)

---

## 1.2 Uso de Type Hints

DECISIÓN: Type hints en todos los métodos públicos

VENTAJAS:
✓ IDE autocomplete mejorado
✓ Detección temprana de bugs (con mypy)
✓ Documentación viva del código
✓ Mejor para data scientists y ML engineers

EJEMPLO:
    def read_frame(self) -> Tuple[bool, Optional[bytes], Optional[FrameMetadata]]:
        ...

---

## 1.3 Context Manager Pattern

DECISIÓN: Implementar __enter__ y __exit__ para VideoStreamProcessor

VENTAJA:
Garantiza liberación de recursos incluso si hay excepciones

ANTES (sin context manager):
    processor = VideoStreamProcessor()
    try:
        # código
    finally:
        processor.release()  # Fácil olvidar esto

DESPUÉS (con context manager):
    with VideoStreamProcessor() as processor:
        # código
        # Se libera automáticamente sin necesidad de try/finally

---

## 1.4 Thread Safety con Locks

DECISIÓN: Usar threading.Lock() para proteger estado compartido

RAZÓN:
Preparación futura para múltiples threads (UI thread, MQTT thread, etc.)

CÓDIGO:
    def read_frame(self):
        with self._lock:
            success, frame = self._capture.read()

---

# ============================================================================
# 2. PATRONES DE DISEÑO
# ============================================================================

## 2.1 Factory Pattern (implícito en config.py)

EdgeServiceConfig crea instancias de VideoConfig, RingBufferConfig, etc.

---

## 2.2 Singleton Pattern (Logger)

El logger se crea una sola vez y se reutiliza en todo el módulo

---

## 2.3 Dataclass Pattern (FrameMetadata)

Uso de @dataclass para estructuras inmutables de datos

VENTAJA:
- Código más limpio que __init__
- Automatic __repr__, __eq__
- Type hints integrados

---

# ============================================================================
# 3. CONSIDERACIONES DE PERFORMANCE
# ============================================================================

## 3.1 Minimizar Lag de Captura

# En _initialize_camera():
self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

EFECTO: Evita que OpenCV acumule frames no procesados en buffer
RESULTADO: Frame más frescos, menor latencia

---

## 3.2 Redimensionamiento Eficiente

# En read_frame():
if frame.shape[1] != self.frame_width or frame.shape[0] != self.frame_height:
    frame = cv2.resize(frame, (self.frame_width, self.frame_height),
                       interpolation=cv2.INTER_LINEAR)

RAZÓN:
- INTER_LINEAR es lo suficientemente rápido para video en tiempo real
- INTER_CUBIC/LANCZOS4 son más lentos (usar solo si es crítico)
- Configurar resolución en cámara es mejor que redimensionar en software

---

## 3.3 Memory Management

FRAME SIZE:
- 1280x720 @ 3 bytes (BGR) = ~2.76 MB por frame
- A 30 FPS = ~82.8 MB/s (justifica cv2.CAP_PROP_BUFFERSIZE=1)

FUTURE: Ring Buffer de 30 segundos
- 30 segundos * 30 FPS = 900 frames
- 900 * 2.76 MB = ~2.48 GB (requiere cuidadosa gestión)

---

# ============================================================================
# 4. EDGE CASES Y ROBUSTEZ
# ============================================================================

## 4.1 Cámara Desconectada

MANEJO:
    if not self._capture or not self._capture.isOpened():
        raise CameraAccessError("La cámara no está inicializada")

---

## 4.2 Lectura de Frame Falló

MANEJO:
    success, frame = self._capture.read()
    
    if not success or frame is None:
        return False, None, None
        # El llamador puede decidir reintentar o actuar

---

## 4.3 Dimensiones Inesperadas

MANEJO:
    actual_width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if actual_width != requested_width:
        # Log warning y continuar (o fallar si es crítico)

---

# ============================================================================
# 5. LOGGING Y DEBUGGING
# ============================================================================

## 5.1 Niveles de Log

INFO: Eventos normales de operación (startup, shutdown, stats)
WARNING: Situaciones anormales pero recuperables (frame fail, reintentos)
ERROR: Errores que requieren atención (init fails, crashes)
DEBUG: Información de debugging (frame timestamps, latency)

---

## 5.2 Archivo de Logs

UBICACIÓN: logs/edge_service.log
ROTACIÓN: 10 MB máximo por archivo, 5 backups
FORMATO: timestamp - logger - level - [file:lineno] - message

---

# ============================================================================
# 6. EXTENSIBILIDAD FUTURA
# ============================================================================

## 6.1 Próxima Fase: MQTT Integration

Ring Buffer → MQTTPublisher → Backend

    processor = VideoStreamProcessor(...)
    mqtt_client = MQTTClient(config.mqtt)
    
    while processor.is_running():
        success, frame, metadata = processor.read_frame()
        if detect_anomaly(frame):  # YOLOv8 en fase 2
            mqtt_client.publish_alert(metadata)

---

## 6.2 Próxima Fase: AI Models

from ultralytics import YOLO
from mediapipe import solutions

model = YOLO('yolov8n.pt')
results = model(frame)

---

## 6.3 Próxima Fase: Ring Buffer

from collections import deque

self.ring_buffer = deque(
    maxlen=int(fps * buffer_duration_seconds)
)

self.ring_buffer.append(frame)

if anomaly_detected:
    save_clip_from_ring_buffer()

---

# ============================================================================
# 7. TESTING STRATEGY (Próximas Fases)
# ============================================================================

tests/
├── test_video_stream.py
│   ├── test_initialization_success
│   ├── test_initialization_invalid_camera
│   ├── test_read_frame
│   ├── test_context_manager
│   └── test_thread_safety
│
├── test_config.py
│   ├── test_config_from_env
│   ├── test_config_validation
│   └── test_defaults
│
└── integration/
    ├── test_end_to_end_capture
    └── test_release_resources

---

# ============================================================================
# 8. DEPLOYMENT CONSIDERATIONS
# ============================================================================

## 8.1 Requisitos del Sistema

MÍNIMO:
- Python 3.8+
- Cámara USB o integrada
- 512 MB RAM (sin ring buffer)
- 50 MB disk para logs

RECOMENDADO:
- Python 3.10+
- Cámara 1080p 30fps
- 2 GB RAM (con ring buffer 30s)
- SSD para logs rápidos

---

## 8.2 Linux/Raspberry Pi

En Pi, es posible que necesites:
    sudo usermod -a -G video $USER
    sudo apt-get install python3-opencv

---

## 8.3 Docker (Futura)

Dockerfile consideraciones:
- Base image: python:3.10-slim
- Instalar libSM6 para OpenCV GUI
- Volume mount para logs
- ENV PYTHONUNBUFFERED=1

---

# ============================================================================
# 9. MONITOREO Y OBSERVABILIDAD
# ============================================================================

## 9.1 Métricas a Recolectar

- Frames por segundo (FPS actual vs target)
- Frame drop rate
- Latencia promedio de captura
- Uso de CPU y memoria
- Uptime del servicio
- Errores y excepciones

---

## 9.2 Health Check

    def health_check(self) -> dict:
        stats = self.get_stats()
        return {
            'status': 'healthy' if self.is_running() else 'down',
            'uptime': self.uptime(),
            'frame_drop_rate': self.calculate_drop_rate(),
            ...
        }

---

# ============================================================================
# 10. CHECKLIST DE CALIDAD DE CÓDIGO
# ============================================================================

✅ Type Hints en métodos públicos
✅ Docstrings PEP-257 (Google style)
✅ Excepciones personalizadas
✅ Logging apropiado
✅ Context manager para recursos
✅ Thread safety
✅ Error handling exhaustivo
✅ Validación de configuración
✅ PEP-8 compliance
✅ No imports no utilizados
✅ Nombres descriptivos de variables
✅ Métodos privados con _underscore
✅ Comentarios para lógica compleja
✅ README con ejemplos

---

# ============================================================================
# REFERENCIAS Y RECURSOS
# ============================================================================

- OpenCV Best Practices: https://docs.opencv.org/
- PEP 8 - Style Guide: https://pep8.org/
- Type Hints: https://docs.python.org/3/library/typing.html
- Context Managers: https://docs.python.org/3/reference/compound_stmts.html#with
- Threading: https://docs.python.org/3/library/threading.html

---

FIN DE DOCUMENTACIÓN ARQUITECTÓNICA
Última actualización: Junio 12, 2026
"""
