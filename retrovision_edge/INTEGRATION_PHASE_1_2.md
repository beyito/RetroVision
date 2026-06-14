"""
RetroVision Edge Service - FASE 1.2 Integration Guide

GUÍA DE INTEGRACIÓN: YOLOv8 Object Detection

Este documento explica cómo funciona la integración de YOLOv8 en el pipeline
y cómo los componentes trabajan juntos.
"""

# ============================================================================
# 1. ARQUITECTURA DE FASE 1.2
# ============================================================================

FLUJO DE DATOS:
    ┌─────────────┐
    │   Cámara    │
    └──────┬──────┘
           │ (RTSP/USB)
           ▼
    ┌──────────────────────┐
    │ VideoStreamProcessor │  (video_stream.py)
    │   - Lee frames       │
    │   - Metadatos        │
    └──────────┬───────────┘
               │ (frame + metadata)
               ▼
    ┌──────────────────────┐
    │  ObjectDetector      │  (object_detector.py)
    │   - YOLOv8n inference│
    │   - Filtra personas  │
    │   - Retorna DetRes   │
    └──────────┬───────────┘
               │ (detections)
               ▼
    ┌──────────────────────┐
    │ draw_detections()    │  (ObjectDetector method)
    │   - Dibuja BBoxes    │
    │   - Agrega etiquetas │
    └──────────┬───────────┘
               │ (frame anotado)
               ▼
    ┌──────────────────────┐
    │  display_frame()     │  (DetectionPipeline)
    │   - Muestra en CV2   │
    │   - Agrega info      │
    └──────────┬───────────┘
               │
               ▼
    ┌──────────────────────┐
    │    Monitor/Screen    │
    └──────────────────────┘

---

# ============================================================================
# 2. NUEVOS MÓDULOS Y CLASES
# ============================================================================

## 2.1 object_detector.py

CLASES PRINCIPALES:

### Detection (dataclass)
Representa UNA detección de objeto.

Atributos:
- x1, y1, x2, y2: Coordenadas del bounding box
- confidence: Score 0.0-1.0
- class_id: ID de la clase (0 = persona en COCO)
- class_name: Nombre legible ("person")

Métodos útiles:
- width(): Ancho del bbox
- height(): Alto del bbox
- area(): Área en píxeles²
- center(): Coordenadas del centro (x, y)

EJEMPLO:
    detection = Detection(
        x1=100, y1=200, x2=300, y2=500,
        confidence=0.85, class_id=0, class_name="person"
    )
    print(f"Ancho: {detection.width()}")  # 200
    print(f"Centro: {detection.center()}")  # (200, 350)

---

### DetectionResult (dataclass)
Resultado COMPLETO de detección en un frame.

Atributos:
- detections: Lista de Detection objects
- frame_shape: Tupla (height, width, channels)
- inference_time_ms: Tiempo de inferencia en ms
- model_name: Nombre del modelo usado

Métodos:
- count(): Cantidad de detecciones
- get_by_confidence(min_conf): Filtra por confianza

EJEMPLO:
    result = detector.detect(frame)
    print(f"Personas detectadas: {result.count()}")
    print(f"Tiempo inferencia: {result.inference_time_ms:.2f}ms")
    
    high_conf = result.get_by_confidence(min_confidence=0.7)

---

### ObjectDetector (clase principal)
Gestor de inferencia con YOLOv8.

Constructor:
    ObjectDetector(
        model_name="yolov8n.pt",
        confidence_threshold=0.5,
        device="cpu"
    )

Métodos públicos:

1. detect(frame: np.ndarray) -> DetectionResult
   - Realiza inferencia en el frame
   - Retorna solo PERSONAS (clase 0)
   - Tiempo: ~50ms en CPU para yolov8n

2. draw_detections(frame, detections, color, thickness) -> frame
   - Dibuja bounding boxes verdes sobre frame
   - Agrega etiqueta: "person 0.85"
   - Dibuja punto en el centro

3. get_model_info() -> dict
   - Retorna información del modelo

4. release()
   - Libera recursos del modelo

EJEMPLO COMPLETO:
    from edge_service import ObjectDetector
    import cv2
    import numpy as np
    
    # Cargar detector
    detector = ObjectDetector(model_name="yolov8n.pt")
    
    # Leer frame
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    # Detectar personas
    result = detector.detect(frame)
    
    # Dibujar
    frame_annotated = detector.draw_detections(
        frame, result.detections,
        color=(0, 255, 0),  # Verde en BGR
        thickness=2
    )
    
    # Mostrar
    cv2.imshow("Persons", frame_annotated)
    
    # Limpiar
    detector.release()

---

## 2.2 detection_pipeline.py

CLASE: DetectionPipeline
Orquestador que coordina VideoStreamProcessor + ObjectDetector.

Constructor:
    DetectionPipeline(
        camera_index=0,
        frame_width=1280,
        frame_height=720,
        target_fps=30,
        model_name="yolov8n.pt",
        confidence_threshold=0.5,
        draw_detections=True
    )

Métodos principales:

1. start() / stop()
   Inicia/detiene el pipeline

2. process_frame() -> (success, frame, metadata, detection_result)
   Ejecuta ciclo completo:
   - Captura frame
   - Ejecuta detección
   - Actualiza estadísticas
   - Dibuja si está habilitado
   - Retorna frame anotado

3. display_frame_with_info(frame, metadata, detection_result)
   Muestra frame con:
   - Frame number, timestamp, FPS
   - Cantidad de personas, tiempo de inferencia
   - Bounding boxes

4. get_stats() -> PipelineStats
   Retorna estadísticas acumuladas

5. print_stats()
   Imprime reporte formateado

6. is_running() -> bool

7. release()
   Libera ambos componentes

EJEMPLO DE USO:
    from edge_service import DetectionPipeline
    import cv2
    
    # Crear pipeline
    pipeline = DetectionPipeline(
        camera_index=0,
        model_name="yolov8n.pt",
        draw_detections=True
    )
    
    pipeline.start()
    
    while pipeline.is_running():
        success, frame, metadata, result = pipeline.process_frame()
        
        if success:
            pipeline.display_frame_with_info(
                frame, metadata, result
            )
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    pipeline.print_stats()
    pipeline.release()

---

## 2.3 Actualización: video_stream.py
NO HA CAMBIADO. VideoStreamProcessor sigue funcionando igual,
ahora simplemente consume ObjectDetector en la capa superior.

---

# ============================================================================
# 3. FILTRO DE PERSONAS (CLASE 0)
# ============================================================================

COCO Dataset - Clase 0 es "person".

YOLOv8 retorna TODAS las clases detectadas. ObjectDetector filtra:

    for box in results[0].boxes:
        class_id = int(box.cls[0])
        
        # FILTRO: Solo clase 0 (personas)
        if class_id != 0:
            continue

RESULTADO: Solo bounding boxes de personas en el frame.

FUTURAS EXTENSIONES (Fase 2):
- class_id == 15: Para detectar armas (depende del modelo/dataset)
- class_id == 2: Para detectar vehículos (si es necesario)
- Etc.

---

# ============================================================================
# 4. COORDINACIÓN: FASE 1.1 vs FASE 1.2
# ============================================================================

FASE 1.1 (VideoStreamProcessor):
    ✓ Captura de video eficiente
    ✓ Metadatos de frames
    ✓ Thread-safe
    ✓ Context manager
    └─ Objetivo: Datos de entrada confiables

FASE 1.2 (ObjectDetector + DetectionPipeline):
    ✓ Inferencia YOLOv8
    ✓ Filtro de personas
    ✓ Dibujo de bounding boxes
    ✓ Estadísticas de detección
    └─ Objetivo: Añadir inteligencia AI

INTEGRACIÓN:
    Pipeline = VideoStreamProcessor + ObjectDetector
    Pipeline es un "orquestador" que los coordina.

VideoStreamProcessor SIGUE INTACTO:
    - Puedes usarlo sin DetectionPipeline si lo necesitas
    - Puedes usarlo sin ObjectDetector
    - Separación de responsabilidades

---

# ============================================================================
# 5. DESCARGAR EL MODELO YOLOV8
# ============================================================================

PRIMERA EJECUCIÓN:
    - Ultralytics descarga automáticamente yolov8n.pt
    - ~6.3 MB (nano model, más pequeño para Edge)
    - Se guarda en: ~/.yolov8/

TIEMPO DE DESCARGA:
    - Primera vez: Depende de velocidad de internet
    - Siguientes veces: Usa cache local

MODELOS DISPONIBLES:
    - yolov8n.pt   (~6.3 MB)  - RECOMENDADO PARA EDGE
    - yolov8s.pt   (~22 MB)   - Más preciso
    - yolov8m.pt   (~49 MB)   - Más preciso aún
    - yolov8l.pt   (~83 MB)   - Lento para Edge
    - yolov8x.pt   (130 MB)   - Muy lento para Edge

PARA EDGE COMPUTING: Usar yolov8n.pt (nano)
- Velocidad: ~50ms CPU / ~20ms GPU
- Precisión: Suficiente para detección de personas
- Tamaño: Solo 6.3 MB

---

# ============================================================================
# 6. TIPO DE DATOS Y FLUJO DE CV2
# ============================================================================

FRAME FORMAT en OpenCV:
    - Type: numpy.ndarray
    - Shape: (height, width, 3)
    - Channels: BGR (not RGB!) importante
    - Dtype: uint8 (0-255 por canal)

FLUJO:
    cv2.VideoCapture() → frame BGR
    ↓
    ObjectDetector.detect() (recibe BGR, YOLOv8 lo maneja)
    ↓
    draw_detections() (dibuja sobre BGR)
    ↓
    cv2.imshow() (muestra BGR)

NOTA: YOLOv8 internamente convierte BGR → RGB si es necesario.

---

# ============================================================================
# 7. CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ============================================================================

Se mantienen igual que Fase 1.1:

    CAMERA_INDEX=0
    FRAME_WIDTH=1280
    FRAME_HEIGHT=720
    FPS=30
    LOG_LEVEL=INFO

NUEVAS PARA FUTURO (no en main.py aún):
    YOLO_MODEL_NAME=yolov8n.pt
    YOLO_CONFIDENCE_THRESHOLD=0.5
    YOLO_DEVICE=cpu

---

# ============================================================================
# 8. ERRORES COMUNES Y SOLUCIONES
# ============================================================================

ERROR: "ModuleNotFoundError: No module named 'ultralytics'"
SOLUCIÓN: pip install ultralytics

ERROR: "Model not found" en primera ejecución
SOLUCIÓN: Conecta a internet, Ultralytics descarga automáticamente

ERROR: Bajo FPS en CPU
SOLUCIÓN: Usa yolov8n.pt (nano), o reduce resolución de frame

ERROR: CUDA/GPU no disponible
SOLUCIÓN: Se fallback a CPU automáticamente (cambiar device="cpu")

ERROR: Memory leak si se usa en loop sin release()
SOLUCIÓN: Asegúrate de llamar a detector.release() o usar context manager

---

# ============================================================================
# 9. ESTADÍSTICAS Y MONITOREO
# ============================================================================

PipelineStats retorna:
    - total_frames: Total de frames procesados
    - frames_with_detections: Frames con ≥1 persona
    - total_persons_detected: Suma de todas las personas
    - avg_inference_time_ms: Promedio de inferencia YOLOv8
    - avg_fps: FPS promedio de captura

INTERPRETACIÓN:

    Total frames procesados: 1500
    Frames con detecciones: 1450 (96.7%)
    Total personas detectadas: 5824
    Promedio inferencia: 47.3ms
    Tasa de detección: 96.7%

Esto significa:
    - Flujo constante sin drops
    - Casi siempre hay personas en el FOV
    - Promedio de 3.88 personas por frame detectado
    - YOLOv8n tarda ~47ms en CPU

---

# ============================================================================
# 10. PRÓXIMAS FASES
# ============================================================================

FASE 1.3: Ring Buffer + MQTT
    - Almacenar últimos 30 segundos en RAM
    - Publicar eventos de "anomalía" a MQTT
    - En detección anómala: guardar clip .mp4

FASE 2: Análisis Avanzado
    - DeepSORT tracking (personas)
    - MediaPipe pose estimation
    - Risk Score calculation
    - Conteo y estadísticas de tiendas

FASE 3: Backend Central
    - API Django para recibir eventos
    - PostgreSQL para métricas
    - WebSockets para streaming

FASE 4: Frontend
    - Dashboard React
    - Heatmaps en tiempo real
    - Alertas en pantalla

---

# ============================================================================
# 11. REFERENCIAS Y RECURSOS
# ============================================================================

YOLOv8 Documentation:
    https://docs.ultralytics.com/

COCO Dataset Classes:
    https://cocodataset.org/

OpenCV Drawing:
    https://docs.opencv.org/3.4/d6/d6e/group__imgproc__draw.html

NumPy Array Operations:
    https://numpy.org/doc/stable/reference/arrays.ndarray.html

---

FIN DE GUÍA DE INTEGRACIÓN
Última actualización: Junio 12, 2026
Versión: Phase 1 - Step 1.2
"""
