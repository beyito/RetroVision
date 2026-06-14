"""
RetroVision Edge Service - FASE 1.3 Integration Guide

GUÍA DE INTEGRACIÓN: MediaPipe Pose + ROI pipeline

Este documento explica cómo se integró MediaPipe Pose en el pipeline y las consideraciones
operativas para su uso en dispositivos Edge.
"""

# 1. OBJETIVO

Añadir estimación de postura (pose) por persona detectada usando YOLOv8.
- Usar `mediapipe` Pose con `model_complexity=0` para minimizar latencia.
- Ejecutar Pose sólo sobre la ROI recortada del bbox de YOLO (reduce trabajo y falsos positivos).
- Traducir landmarks normalizados al sistema de coordenadas del frame original.

# 2. COMPONENTES NUEVOS

- `edge_service/posture_estimator.py`:
  - `PostureEstimator` encapsula MediaPipe Pose.
  - Métodos: `estimate(image_rgb) -> Optional[List[(x_norm,y_norm,vis)]]`,
    `norm_to_absolute(landmarks, roi_origin, roi_size) -> List[(x_px,y_px,vis)]`,
    `draw_landmarks_on_frame(frame, landmarks_abs)` y `release()`.
  - Inicializa con `model_complexity=0`, `min_detection_confidence=0.5`, `min_tracking_confidence=0.5`.

# 3. FLUJO DE DATOS (POSTURE ESTIMATION)

1. YOLOv8 detecta personas y retorna `Detection` con bbox (x1,y1,x2,y2).
2. Para cada `Detection` válida:
   - Clamp bbox dentro de límites del frame.
   - Rechazar ROI demasiado pequeño (ej: width<16 o height<16).
   - Recortar ROI del frame (BGR), convertir a RGB.
   - Llamar `PostureEstimator.estimate(roi_rgb)`.
   - Si hay landmarks normalizados, llamar `norm_to_absolute(..., roi_origin, (w,h))`.
   - Guardar lista de landmarks absolutos en `Detection.landmarks`.
   - Dibujar landmarks y conexiones sobre el frame principal con `draw_landmarks_on_frame()`.

# 4. CONSIDERACIONES PRÁCTICAS

- MediaPipe requiere `pip install mediapipe` (incluido en `requirements.txt`).
- Si `mediapipe` no está disponible, el pipeline inicializa sin estimador y continúa la detección de personas (se registra un warning).
- Evitar depender de atributos internos de librerías 3rd-party (ej. `model.imgsz`) — usar tamaños estáticos o APIs públicas.
- ROI demasiado pequeño produce resultados inconsistentes; el pipeline omite estimaciones en esos casos.

# 5. FORMATO DE SALIDA

- `Detection.landmarks`: Lista opcional de tuplas `(x_px, y_px, visibility)` con coordenadas absolutas en el frame principal.
- `DetectionResult` mantiene `detections` con `landmarks` presentes cuando fue posible estimarlos.

# 6. DEPURACIÓN

- Logs: `PostureEstimator` registra errores e inicialización.
- En caso de fallo en estimación para una detección, se captura la excepción y el pipeline continúa.

# 7. EJEMPLO RÁPIDO

```python
from edge_service import DetectionPipeline

pipeline = DetectionPipeline(camera_index=0, draw_detections=True)
with pipeline:
    while pipeline.is_running():
        success, frame, metadata, result = pipeline.process_frame()
        if not success:
            break
        pipeline.display_frame_with_info(frame, metadata, result)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

pipeline.print_stats()
```

# 8. NOTAS FINALES

- Esta integración prioriza robustez y compatibilidad en Edge: modelos ligeros y validaciones de ROI.
- Próximos pasos: añadir tracking (DeepSORT) y fusión temporal de landmarks para mejorar estabilidad.
