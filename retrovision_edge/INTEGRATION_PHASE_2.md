"""
RetroVision Edge Service - FASE 2 Integration Guide

GUÍA DE INTEGRACIÓN: Risk Analytics, Memory Buffer & Alert System

Este documento explica cómo funciona la FASE 2 (Lógica de Riesgo y Memoria Temporal)
y cómo los componentes trabajan en cadena.
"""

# 1. OBJETIVO FASE 2

Añadir inteligencia de riesgo al pipeline:
- Analizar comportamiento de cada persona detectada usando geometría de poses
- Mantener memoria circular (ring buffer) de 30 segundos de video crudo
- Cuando risk_score > 0.7, guardar automáticamente el video como evidencia
- Todo de forma asíncrona para no afectar los FPS en tiempo real

# 2. FLUJO DE DATOS (FASE 2)

```
Frame original (BGR)
    ↓
[VideoStreamProcessor] - Captura
    ↓
[ObjectDetector] - YOLOv8 detecta personas
    ↓
[PostureEstimator] - MediaPipe Pose (33 landmarks)
    ↓
[BehaviorAnalyzer] - Calcula risk_score (0.0-1.0)
    ↓
Detección con landmarks + risk_score
    ↓
┌─→ [RingBuffer] - Guarda frame crudo en memoria (últimos 30s)
│
└─→ Si risk_score > 0.7:
    [AlertWriter] - Extrae buffer y escribe .mp4 async
        ↓
    Archivo: alerts/alert_YYYYMMDD_HHMMSS_risk-LEVEL_SCORE.mp4
```

# 3. NUEVOS COMPONENTES

## 3.1 BehaviorAnalyzer (risk_analyzer.py)

Analiza landmarks y calcula un risk_score.

### Reglas Implementadas:

#### Regla 1: Manos Ocultas/Bolsillos (Hidden Hands)
- **Qué**: Detecta si las muñecas están muy cerca de las caderas
- **Por qué**: Comportamiento sospechoso (ocultando algo)
- **Cálculo**: Distancia normalizada entre (wrist_left + wrist_right) y (hip_left + hip_right)
- **Umbral**: < 15% de la altura del cuerpo = sospechoso
- **Contribución**: Máximo 0.6 al risk_score

#### Regla 2: Inclinación/Agacharse (Abnormal Posture)
- **Qué**: Detecta si el usuario se inclina excesivamente hacia adelante
- **Por qué**: Posible inspección de productos en estantes bajos (shoplifting)
- **Cálculo**: Desviación horizontal de la nariz respecto al eje de hombros
- **Umbral**: > 25% de desviación = anormal
- **Contribución**: Máximo 0.7 al risk_score

### Risk Score Formula:
```
risk_score = 0.4 * hidden_hands_score + 0.6 * abnormal_posture_score
```

### Uso:
```python
from edge_service import BehaviorAnalyzer

analyzer = BehaviorAnalyzer()
analysis = analyzer.analyze(landmarks)

print(f"Risk: {analysis.risk_score:.2f}")
print(f"Triggered rules: {analysis.rules_triggered}")
```

## 3.2 RingBuffer (video_buffer.py)

Buffer circular para almacenar 30 segundos de frames crudos en RAM.

### Característica:
- Capacidad: `fps * 30` frames
  - @ 30 FPS: 900 frames
  - @ 60 FPS: 1800 frames
- Memoria: ~150MB para 1280x720 RGB (30s @ 30fps)
- Mechanism: `collections.deque(maxlen=N)` (FIFO automático)

### Uso:
```python
from edge_service import RingBuffer

buffer = RingBuffer(fps=30, retention_seconds=30)

# Agregar frames
buffer.add_frame(frame_bgr)

# Obtener todos los frames para guardar
frames = buffer.get_frames()

# Estadísticas
stats = buffer.get_stats()
print(f"Buffer: {stats.current_size}/{stats.max_size} "
      f"({stats.utilization_percent:.1f}%, {stats.memory_usage_mb:.1f}MB)")
```

## 3.3 AlertWriter (alert_writer.py)

Escritor asíncrono de alertas (videos de evidencia).

### Características:
- **Async**: Thread daemon para no bloquear main pipeline
- **Cooldown**: 10 segundos entre alertas (evita spam de disco)
- **Formato**: MPEG-4 `.mp4` a 30 FPS (configurable)
- **Naming**: `alert_YYYYMMDD_HHMMSS_risk-LEVEL_SCORE.mp4`
  - LEVEL: LOW, MEDIUM, HIGH, CRITICAL
  - SCORE: Risk score con 2 decimales

### Uso:
```python
from edge_service import AlertWriter

writer = AlertWriter(alerts_dir="alerts", cooldown_seconds=10.0)

# Verificar si está listo para una nueva alerta
if writer.is_alert_ready():
    # Guardar frames de forma asíncrona
    writer.write_alert_async(
        frames=buffer.get_frames(),
        risk_score=0.85,
        triggered_rules=["hidden_hands", "abnormal_posture"]
    )

# Limpiar alertas antiguas
deleted = writer.cleanup_old_alerts(max_age_hours=24)

# Estadísticas
stats = writer.get_alerts_stats()
print(f"Total alerts: {stats['total_alerts']}")
print(f"Size: {stats['total_size_mb']:.1f}MB")
```

# 4. INTEGRACIÓN EN DETECTION PIPELINE

## 4.1 Inicialización

El `DetectionPipeline` inicializa automáticamente todos los componentes FASE 2:

```python
from edge_service import DetectionPipeline

pipeline = DetectionPipeline(
    camera_index=0,
    frame_width=1280,
    frame_height=720,
    target_fps=30,
    model_name="yolov8n.pt",
    confidence_threshold=0.5,
    draw_detections=True
)

with pipeline:
    while pipeline.is_running():
        success, frame, metadata, result = pipeline.process_frame()
        if success:
            pipeline.display_frame_with_info(frame, metadata, result)
```

## 4.2 Proceso por Frame

En cada `process_frame()`:

1. Capturar frame original
2. Detectar personas con YOLOv8
3. Estimar postura con MediaPipe (landmarks)
4. **[FASE 2]** Guardar frame en RingBuffer
5. **[FASE 2]** Para cada persona:
   - Analizar comportamiento → risk_score
   - Dibujar risk_score en frame (debugging)
   - Si risk > 0.7 y cooldown listo:
     → Disparar alert export asíncrono
6. Dibujar bounding boxes y esqueleto
7. Retornar frame anotado

## 4.3 Detección de `Detection`

Cada `Detection` ahora incluye:

```python
@dataclass
class Detection:
    x1, y1, x2, y2: int
    confidence: float
    class_id: int
    class_name: str
    landmarks: Optional[List[Tuple[int, int, float]]] = None
    risk_score: float = 0.0  # ← FASE 2
```

# 5. ARCHIVOS GENERADOS

## 5.1 Directorio de Alertas

```
alerts/
├── alert_20260612_101530_risk-HIGH_0.72.mp4    (30 segundos de video)
├── alert_20260612_101630_risk-CRITICAL_0.85.mp4
└── alert_20260612_101730_risk-MEDIUM_0.45.mp4
```

## 5.2 Nombre de Archivo

Formato: `alert_YYYYMMDD_HHMMSS_risk-LEVEL_SCORE.mp4`

- `YYYYMMDD_HHMMSS`: Timestamp exacto del evento
- `LEVEL`: Risk level (LOW/MEDIUM/HIGH/CRITICAL)
- `SCORE`: Risk score con 2 decimales (0.00-1.00)

# 6. COOLDOWN MECHANISM

Para evitar colapsar el disco duro:

1. Primera alerta con risk > 0.7:
   - `is_alert_ready()` → True
   - Inicia export asíncrono
   - Registra `_last_alert_time`

2. Siguientes 10 segundos:
   - `is_alert_ready()` → False
   - Ignora nuevas alertas (logging DEBUG)

3. Después de 10 segundos:
   - `is_alert_ready()` → True nuevamente

## Configuración:
```python
AlertWriter(alerts_dir="alerts", cooldown_seconds=10.0)
```

# 7. THREADING & PERFORMANCE

### Async Write (No FPS Impact)
- Export runs in daemon thread
- Main pipeline continues unblocked
- Puede escribirse a disco mientras pipeline captura frames

### Memory Efficiency
- Frame copy only on add to buffer
- Ring buffer uses deque (efficient circular buffer)
- Alerts cleaned up automatically by age

### Logs
```
2026-06-12 10:15:47 - RetroVision.Edge - WARNING - ALERTA: Risk Score CRÍTICO 0.85 Reglas: hidden_hands, abnormal_posture
2026-06-12 10:15:47 - RetroVision.Edge - INFO - Alerta guardada: alert_20260612_101547_risk-CRITICAL_0.85.mp4 (900 frames, 125.3 MB, reglas: hidden_hands, abnormal_posture)
```

# 8. DEGRADACIÓN ELEGANTE (Graceful Degradation)

Si algún componente falla en inicialización:

- PostureEstimator falla → Pipeline continúa sin pose (detection sin landmarks)
- BehaviorAnalyzer falla → Pipeline continúa sin risk scores (detection.risk_score = 0.0)
- RingBuffer falla → Pipeline continúa sin alertas
- AlertWriter falla → Pipeline continúa sin export async

**Result**: Siempre funciona detection básica (FASE 1), FASE 2 es opcional.

# 9. DEBUGGING & MONITORING

### Logs en INFO
- Inicialización de componentes
- Alertas disparadas (con detalles)
- Archivos guardados (tamaño, duración)

### Logs en DEBUG
- Risk analysis por detección
- Cooldown rechazos
- ROI demasiado pequeños

### Logs en WARNING
- Detecciones con risk_score > 0.7 (ALERTA)
- Fallos en inicialización (pero continúa)

# 10. EJEMPLO COMPLETO

```python
import sys
import signal
from edge_service import DetectionPipeline
import cv2

def signal_handler(sig, frame):
    print("Presionando 'q' o Ctrl+C para salir...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Crear pipeline con FASE 2 integrada
pipeline = DetectionPipeline(camera_index=0, draw_detections=True)

try:
    pipeline.start()
    
    while pipeline.is_running():
        success, frame, metadata, result = pipeline.process_frame()
        
        if not success:
            break
        
        # Mostrar frame con info
        pipeline.display_frame_with_info(frame, metadata, result)
        
        # Información de riesgo
        for det in result.detections:
            if det.risk_score > 0.7:
                print(f"  ⚠️ RIESGO ALTO: {det.risk_score:.2f}")
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
except Exception as e:
    print(f"Error: {e}")

finally:
    # Mostrar estadísticas
    pipeline.print_stats()
    
    # Estadísticas de alertas
    if hasattr(pipeline, '_alert_writer') and pipeline._alert_writer:
        alerts_stats = pipeline._alert_writer.get_alerts_stats()
        print(f"\nAlertas guardadas: {alerts_stats['total_alerts']}")
        print(f"Tamaño total: {alerts_stats['total_size_mb']:.1f}MB")
    
    # Limpiar
    pipeline.release()
    cv2.destroyAllWindows()
```

# 11. PRÓXIMOS PASOS

### FASE 3: Tracking Persistente
- DeepSORT para seguimiento de personas entre frames
- Mantener ID temporal de personas
- Agregar historia de comportamiento

### FASE 4: Backend Integration
- Publicar alertas a MQTT
- Sincronización con base de datos central
- Dashboard en tiempo real
