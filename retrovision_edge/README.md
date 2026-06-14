# RetroVision - Sistema de Videovigilancia Inteligente

## 📋 Descripción General

**RetroVision** es un sistema de videovigilancia inteligente dual para tiendas físicas, enfocado en:
- **Analítica Comercial**: Conteo de clientes, tiempos de cola, mapas de calor, análisis de comportamiento
- **Seguridad**: Detección de anomalías, armas, alertas en tiempo real

**Paradigma**: Edge Computing + Arquitectura Distribuida basada en Eventos

**Estado Actual**: FASE 2 - PASO 2.3 (Risk Analytics & Memory) ✅

---

## 🏗️ Arquitectura de Tres Capas

```
┌─────────────────────────────────────────────────────────┐
│                   FRONTEND (SPA)                        │
│              React + TailwindCSS + WebSockets           │
│                (Dashboard de Control)                   │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND CENTRAL                        │
│        Django + DRF + PostgreSQL + Mosquitto MQTT       │
│            (Gestión, Base de Datos, Routing)           │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │ MQTT Events
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  MICROSERVICIO EDGE                     │
│   Python + OpenCV + YOLOv8 + MediaPipe + DeepSORT      │
│              (Procesamiento Local + AI)                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 FASE 1 - PASO 1.2: Integración de YOLOv8

Este directorio contiene el **Microservicio Edge** con soporte para detección inteligente de personas.

### Novedades en 1.2:
1. ✅ **ObjectDetector**: Clase dedicada a inferencia YOLOv8
2. ✅ **Filtro de Personas**: Detecta SOLO clase 0 (COCO dataset)
3. ✅ **DetectionPipeline**: Orquestador que coordina captura + detección
4. ✅ **Bounding Boxes**: Dibuja automáticamente sobre personas
5. ✅ **Estadísticas**: Monitoreo de inferencia en tiempo real
6. ✅ **Pose Estimation (FASE 1.3)**: Integración opcional de MediaPipe Pose para extraer 33 landmarks por persona detectada (model_complexity=0). Si `mediapipe` no está disponible, el pipeline continúa sin estimación de postura (se registra una advertencia).

### Novedades en FASE 2:
1. ✅ **BehaviorAnalyzer**: Calcula `risk_score` (0.0-1.0) analizando geometría de poses
   - Regla 1: Detección de manos ocultas/bolsillos (distancia muñecas-caderas)
   - Regla 2: Detección de inclinación/agacharse anormal
2. ✅ **RingBuffer**: Memoria circular que almacena 30 segundos de frames crudos en RAM
3. ✅ **AlertWriter**: Disparador asíncrono que exporta video (últimos 30s) como `.mp4` cuando `risk_score > 0.7`
   - Cooldown: 10 segundos entre alertas (evita spam)
   - Videos guardados en `alerts/` con nombre: `alert_YYYYMMDD_HHMMSS_risk-LEVEL_SCORE.mp4`
4. ✅ **Degradación Elegante**: Si algún componente falla, pipeline continúa funcionando en FASE 1

### Responsabilidades del Edge:
1. ✅ Capturar video desde cámara local (RTSP/Webcam)
2. ✅ Procesar frames de manera eficiente
3. ✅ **Ejecutar YOLOv8 para detección de personas**
4. ✅ Comunicarse SOLO a través de MQTT (próximas fases)
5. ✅ Mantener Ring Buffer en RAM para clips (próximas fases)

---

## 📁 Estructura del Proyecto

```
SW1_PROYECTO/
├── edge_service/                       # Paquete principal del Edge Service
│   ├── __init__.py                    # Exports públicos
│   ├── video_stream.py                # VideoStreamProcessor (captura)
│   ├── object_detector.py             # ObjectDetector (YOLOv8) ⭐ NUEVO 1.2
│   ├── detection_pipeline.py          # DetectionPipeline (orquestador) ⭐ NUEVO 1.2
│   ├── config.py                      # Configuración centralizada
│   ├── logger_config.py               # Setup de logging
│   └── exceptions.py                  # Excepciones personalizadas
│
├── tests/                             # Tests (para futuras fases)
├── logs/                              # Directorio de logs
│
├── main.py                            # Script de entrada (con YOLOv8)
├── requirements.txt                   # Dependencias Python (con ultralytics)
├── .env.example                       # Variables de entorno (template)
├── .gitignore                         # Git ignore
├── README.md                          # Este archivo
├── ARCHITECTURE.md                    # Decisiones de diseño (Fase 1.1)
└── INTEGRATION_PHASE_1_2.md           # Guía de integración YOLOv8 ⭐ NUEVO 1.2
```

---

## 🚀 Cómo Usar

### 1. Instalación de Dependencias

```bash
# Crear entorno virtual (recomendado)
python -m venv venv

# Activar entorno
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias (incluye ultralytics y mediapipe para pose estimation)
pip install -r requirements.txt
```

**Nota**: La primera ejecución descargará automáticamente el modelo YOLOv8n (~6.3 MB).

### 2. Configurar Variables de Entorno (Opcional)

```bash
# Copiar template de configuración
cp .env.example .env

# Editar .env con tus valores (opcional, los defaults funcionan perfectamente)
# CAMERA_INDEX=0
# FRAME_WIDTH=1280
# FRAME_HEIGHT=720
# FPS=30
# LOG_LEVEL=INFO
```

### 3. Ejecutar el Servicio con Detección YOLOv8

```bash
python main.py
```

**Salida esperada:**
```
2026-06-12 10:15:30 - RetroVision.Edge - INFO - ======================================================================
2026-06-12 10:15:30 - RetroVision.Edge - INFO - RetroVision Edge Service - INICIANDO (FASE 1.2)
2026-06-12 10:15:30 - RetroVision.Edge - INFO - Captura de video + Detección YOLOv8
2026-06-12 10:15:30 - RetroVision.Edge - INFO - ======================================================================
2026-06-12 10:15:31 - RetroVision.Edge - INFO - [object_detector.py:95] - Cargando modelo YOLOv8: yolov8n.pt (device=cpu)...
2026-06-12 10:15:45 - RetroVision.Edge - INFO - [object_detector.py:108] - Modelo YOLOv8 cargado exitosamente. Resolución de entrada: 640
2026-06-12 10:15:45 - RetroVision.Edge - INFO - [detection_pipeline.py:72] - Pipeline de detección inicializado exitosamente
2026-06-12 10:15:45 - RetroVision.Edge - INFO - [detection_pipeline.py:85] - Pipeline iniciado
2026-06-12 10:15:45 - RetroVision.Edge - INFO - [main.py:85] - Iniciando detección (presiona 'q' para salir)...
2026-06-12 10:15:47 - RetroVision.Edge - INFO - [main.py:119] - Frame 30: 3 personas detectadas | Inferencia: 45.23ms
```

**En la pantalla verás:**
- Video en tiempo real desde tu cámara
- **Bounding boxes verdes** alrededor de personas detectadas
- Etiqueta con clase y confianza (ej: "person 0.85")
- Punto rojo en el centro de cada detección
 - Esqueleto y landmarks (si `mediapipe` está instalado): puntos y conexiones dibujadas sobre cada persona detectada
- Información en pantalla: FPS, frame number, cantidad de personas, tiempo de inferencia

### 4. Detener el Servicio

Presiona la tecla **'q'** en la ventana de video, o **Ctrl+C** en la terminal.

**Salida final:**
```
2026-06-12 10:15:60 - RetroVision.Edge - INFO - ============================================================
2026-06-12 10:15:60 - RetroVision.Edge - INFO - ESTADÍSTICAS DEL PIPELINE
2026-06-12 10:15:60 - RetroVision.Edge - INFO - ============================================================
2026-06-12 10:15:60 - RetroVision.Edge - INFO - Total frames procesados: 150
2026-06-12 10:15:60 - RetroVision.Edge - INFO - Frames con detecciones: 145
2026-06-12 10:15:60 - RetroVision.Edge - INFO - Total personas detectadas: 487
2026-06-12 10:15:60 - RetroVision.Edge - INFO - Promedio inferencia: 45.67ms
2026-06-12 10:15:60 - RetroVision.Edge - INFO - Tasa de detección: 96.7%
2026-06-12 10:15:60 - RetroVision.Edge - INFO - ============================================================
```

---

## 🏛️ Componentes Principales

### `VideoStreamProcessor` (video_stream.py)

**Clase central que encapsula toda la lógica de captura de video.**

**Métodos principales:**

| Método | Descripción |
|--------|-------------|
| `__init__()` | Inicializa la cámara con configuración |
| `read_frame()` | Lee el siguiente frame del flujo |
| `display_frame()` | Muestra frame en ventana OpenCV |
| `start()` / `stop()` | Controla ciclo de vida |
| `get_stats()` | Retorna estadísticas de captura |
| `release()` | Libera recursos de manera segura |

**Type Hints y Docstrings**: ✅ PEP-8 compliant

---

### `ObjectDetector` (object_detector.py) ⭐ NUEVO EN 1.2

**Clase dedicada a inferencia YOLOv8 para detección de personas.**

**Métodos principales:**

| Método | Descripción |
|--------|-------------|
| `__init__()` | Carga el modelo YOLOv8n |
| `detect(frame)` | Ejecuta inferencia, retorna `DetectionResult` |
| `draw_detections()` | Dibuja bounding boxes sobre el frame |
| `get_model_info()` | Información del modelo cargado |
| `release()` | Libera recursos del modelo |

**Características:**
- ✅ Filtro automático: Solo detecta PERSONAS (clase 0 en COCO)
- ✅ Inferencia rápida: ~45-50ms en CPU (yolov8n)
- ✅ Descarga automática del modelo en primera ejecución
- ✅ Manejo robusto de errores

**Dataclasses:**

```python
@dataclass
class Detection:
    """Una detección individual"""
    x1, y1, x2, y2: int           # Coordenadas del bbox
    confidence: float              # Score 0.0-1.0
    class_id: int                 # ID de clase
    class_name: str               # "person"
    
    def width(), height(), area(), center()  # Métodos útiles

@dataclass
class DetectionResult:
    """Resultado completo de un frame"""
    detections: List[Detection]
    frame_shape: Tuple
    inference_time_ms: float
    model_name: str
```

---

### `DetectionPipeline` (detection_pipeline.py) ⭐ NUEVO EN 1.2

**Orquestador que coordina VideoStreamProcessor + ObjectDetector.**

**Métodos principales:**

| Método | Descripción |
|--------|-------------|
| `process_frame()` | Captura → Detección → Dibuja → Retorna frame anotado |
| `display_frame_with_info()` | Muestra frame con estadísticas en tiempo real |
| `start()` / `stop()` | Control de ciclo de vida |
| `get_stats()` | Estadísticas acumuladas del pipeline |
| `print_stats()` | Imprime reporte formateado |
| `release()` | Libera ambos componentes |

**Estadísticas disponibles:**

```python
stats = pipeline.get_stats()
# stats.total_frames              # Total procesados
# stats.frames_with_detections    # Frames con ≥1 persona
# stats.total_persons_detected    # Suma de todas personas
# stats.avg_inference_time_ms     # Promedio YOLOv8
# stats.avg_fps                   # FPS promedio
```

---

### `EdgeServiceConfig` (config.py)

**Gestión centralizada de configuración.**

- Lee variables de entorno
- Valida parámetros
- Proporciona defaults sensatos

```python
from edge_service import EdgeServiceConfig

config = EdgeServiceConfig()
config.validate()

print(config.video.frame_width)  # 1280
print(config.mqtt.broker_host)   # localhost
```

---

### `setup_logger()` (logger_config.py)

**Logger centralizado con rotación de archivos.**

- Escribe en archivo + consola simultáneamente
- Rotación automática de logs (10 MB)
- Formato de timestamp consistente

---

## 🛡️ Manejo de Errores

El código implementa una jerarquía de excepciones personalizada:

```
RetroVisionEdgeException (base)
├── CameraInitializationError
├── CameraAccessError
├── FrameProcessingError
└── ConfigurationError
```

**Ejemplo:**

```python
try:
    processor = VideoStreamProcessor(camera_index=0)
except CameraInitializationError as e:
    logger.error(f"Cámara no disponible: {e}")
    sys.exit(1)
```

---

## 🔄 Context Manager (Uso Recomendado)

Para garantizar la liberación de recursos:

```python
from edge_service import VideoStreamProcessor

with VideoStreamProcessor(camera_index=0) as processor:
    processor.start()
    # ... procesar frames ...
    # Al salir del contexto, se liberan automáticamente los recursos
```

---

## 📊 Metadata de Frames

Cada frame capturado incluye metadatos:

```python
@dataclass
class FrameMetadata:
    timestamp: datetime       # Momento exacto de captura
    frame_number: int        # Número secuencial del frame
    width: int              # Ancho en píxeles
    height: int             # Alto en píxeles
    fps: float              # FPS configurado
```

---

## 🔮 Próximas Fases (Roadmap)

### ✅ FASE 1 - PASO 1.1: Base del Edge Service (COMPLETADO)
- ✅ Captura eficiente de video desde cámara
- ✅ Metadatos de frames
- ✅ Manejo robusto de errores

### ✅ FASE 1 - PASO 1.2: Integración YOLOv8 (COMPLETADO)
- ✅ ObjectDetector con YOLOv8n
- ✅ Filtro de personas (clase 0)
- ✅ DetectionPipeline orquestador
- ✅ Bounding boxes en tiempo real
- ✅ Estadísticas de inferencia

### ✅ FASE 1 - PASO 1.3: Pose Estimation con MediaPipe (COMPLETADO)
- ✅ PostureEstimator con model_complexity=0
- ✅ 33 landmarks por persona
- ✅ Dibujo de esqueleto
- ✅ Traducción de coordenadas

### ✅ FASE 2: Lógica de Riesgo y Memoria Temporal (COMPLETADO)
- ✅ PASO 2.1: BehaviorAnalyzer (risk scoring geométrico)
- ✅ PASO 2.2: RingBuffer (30 segundos de video crudo en RAM)
- ✅ PASO 2.3: AlertWriter (export async de alertas con cooldown)

### FASE 3: Ring Buffer + MQTT
- Implementar circular buffer (`collections.deque`)
- Almacenamiento de 30 segundos de video crudo en RAM
- Exportación a clip .mp4 en caso de anomalía
- Publicación de eventos MQTT al backend

### FASE 2: Análisis Avanzado
- DeepSORT para tracking persistente de personas
- MediaPipe para detección de postura corporal
- Cálculo de Risk Score continuo
- Detección de comportamientos anómalos

### FASE 3: Backend Central
- API REST Django para recibir eventos
- PostgreSQL para almacenamiento centralizado
- Eclipse Mosquitto broker para eventos MQTT
- WebSockets para comunicación en tiempo real

### FASE 4: Frontend
- Panel de control React
- Visualización de heatmaps
- Alertas instantáneas
- Métricas de vendedores

---

## 🧪 Testing

Estructura para tests (próximas fases):

```bash
# Ejecutar tests
pytest tests/

# Con coverage
pytest tests/ --cov=edge_service
```

---

## 📝 Estándares de Código

✅ **Cumplidos:**
- Type Hints en todos los métodos
- Docstrings PEP-257 en clases y métodos
- Logging estructurado
- Excepciones personalizadas
- Context managers para recursos
- Thread-safety con locks
- PEP-8 (line length, naming conventions)

---

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| `CameraInitializationError` | Verifica que la cámara esté conectada y disponible |
| `Permission denied` en logs | Crea directorio `logs/` manualmente |
| Bajo FPS en captura | Reduce resolución o sube de hardware |
| Ventana cerrada abruptamente | Revisa logs en `logs/edge_service.log` |

---

## 📄 Licencia

Proyecto de grado - RetroVision Team

---

## 👥 Contribuidores

- **Arquitecto de Software**: [Tu nombre]
- **Especialista Edge Computing**: [Tu nombre]

---

## 📞 Contacto y Soporte

Para reportar bugs o sugerencias, abre un issue en el repositorio.

---

**Última actualización**: Junio 12, 2026
**Versión**: 0.2.0 (Phase 1 - Step 1.2: YOLOv8 Integration)
