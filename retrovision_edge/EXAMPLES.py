"""
RetroVision Edge Service - Ejemplos de Uso

Este archivo contiene ejemplos prácticos de cómo usar los componentes
del microservicio Edge de RetroVision.
"""

# ============================================================================
# EJEMPLO 1: Uso Básico de ObjectDetector
# ============================================================================

"""
Ejecutar inferencia YOLOv8 directamente sobre un frame.
"""

def example_1_basic_object_detection():
    import cv2
    from edge_service import ObjectDetector
    
    # Crear detector
    detector = ObjectDetector(
        model_name="yolov8n.pt",
        confidence_threshold=0.5,
    )
    
    # Capturar un frame
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    if ret:
        # Ejecutar detección
        result = detector.detect(frame)
        
        print(f"Personas detectadas: {result.count()}")
        print(f"Tiempo de inferencia: {result.inference_time_ms:.2f}ms")
        
        # Dibujar bounding boxes
        frame_annotated = detector.draw_detections(frame, result.detections)
        
        # Mostrar
        cv2.imshow("Detections", frame_annotated)
        cv2.waitKey(0)
    
    detector.release()
    cap.release()
    cv2.destroyAllWindows()


# ============================================================================
# EJEMPLO 2: Uso Avanzado de ObjectDetector con Filtrado
# ============================================================================

"""
Detectar personas con confianza mínima y acceder a sus propiedades.
"""

def example_2_advanced_detection():
    import cv2
    from edge_service import ObjectDetector
    
    detector = ObjectDetector(
        model_name="yolov8n.pt",
        confidence_threshold=0.4,  # Umbral más bajo
    )
    
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    if ret:
        result = detector.detect(frame)
        
        # Filtrar por confianza
        high_conf_detections = result.get_by_confidence(min_confidence=0.7)
        
        print(f"Total detecciones: {result.count()}")
        print(f"Detecciones con confianza > 0.7: {len(high_conf_detections)}")
        
        # Iterar sobre detecciones
        for detection in high_conf_detections:
            print(f"  - Persona en ({detection.x1}, {detection.y1})")
            print(f"    Tamaño: {detection.width()}x{detection.height()} px")
            print(f"    Área: {detection.area()} px²")
            print(f"    Centro: {detection.center()}")
            print(f"    Confianza: {detection.confidence:.2f}")
    
    detector.release()
    cap.release()


# ============================================================================
# EJEMPLO 3: Uso del DetectionPipeline (Recomendado)
# ============================================================================

"""
Usar el pipeline completo que coordina captura + detección.
Este es el uso RECOMENDADO para flujo de producción.
"""

def example_3_detection_pipeline():
    import cv2
    from edge_service import DetectionPipeline
    
    # Crear pipeline
    pipeline = DetectionPipeline(
        camera_index=0,
        frame_width=1280,
        frame_height=720,
        target_fps=30,
        model_name="yolov8n.pt",
        confidence_threshold=0.5,
        draw_detections=True,  # Dibujar automáticamente
    )
    
    pipeline.start()
    
    frame_count = 0
    
    try:
        while pipeline.is_running():
            # Procesar un frame completo
            success, frame, metadata, detection_result = pipeline.process_frame()
            
            if not success:
                continue
            
            # Mostrar con información
            pipeline.display_frame_with_info(frame, metadata, detection_result)
            
            # Log cada 30 frames
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"Frame {metadata.frame_number}: "
                      f"{detection_result.count()} personas | "
                      f"{detection_result.inference_time_ms:.1f}ms")
            
            # Salir con 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.print_stats()
        pipeline.release()
        cv2.destroyAllWindows()


# ============================================================================
# EJEMPLO 4: Usar Context Manager (RECOMENDADO para Seguridad)
# ============================================================================

"""
Context manager automáticamente libera recursos incluso si hay excepciones.
"""

def example_4_context_manager():
    import cv2
    from edge_service import DetectionPipeline
    
    # Context manager: se libera automáticamente
    with DetectionPipeline(
        camera_index=0,
        model_name="yolov8n.pt"
    ) as pipeline:
        pipeline.start()
        
        while pipeline.is_running():
            success, frame, metadata, result = pipeline.process_frame()
            
            if not success:
                continue
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Al salir del with block, se libera automáticamente
        # Incluso si hay excepción


# ============================================================================
# EJEMPLO 5: Obtener Estadísticas del Pipeline
# ============================================================================

"""
Monitorear en tiempo real el rendimiento del pipeline.
"""

def example_5_pipeline_statistics():
    import cv2
    from edge_service import DetectionPipeline
    
    pipeline = DetectionPipeline(
        camera_index=0,
        model_name="yolov8n.pt"
    )
    
    pipeline.start()
    
    frame_count = 0
    
    try:
        while pipeline.is_running():
            success, frame, metadata, result = pipeline.process_frame()
            
            if not success:
                continue
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            frame_count += 1
            
            # Mostrar estadísticas cada 60 frames
            if frame_count % 60 == 0:
                stats = pipeline.get_stats()
                
                print(f"\n--- Estadísticas actuales ---")
                print(f"Total frames: {stats.total_frames}")
                print(f"Frames con detecciones: {stats.frames_with_detections}")
                print(f"Total personas: {stats.total_persons_detected}")
                print(f"Promedio inferencia: {stats.avg_inference_time_ms:.2f}ms")
                
                if stats.total_frames > 0:
                    det_rate = (stats.frames_with_detections / stats.total_frames) * 100
                    print(f"Tasa de detección: {det_rate:.1f}%")
                    print(f"Promedio personas/frame: "
                          f"{stats.total_persons_detected / stats.frames_with_detections:.2f}")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        print("\n--- Estadísticas Finales ---")
        pipeline.print_stats()
        pipeline.release()
        cv2.destroyAllWindows()


# ============================================================================
# EJEMPLO 6: Guardar Frames con Detecciones
# ============================================================================

"""
Guardar frames que contengan personas detectadas.
"""

def example_6_save_detections():
    import cv2
    import os
    from edge_service import DetectionPipeline
    
    # Crear directorio para guardar
    output_dir = "detected_frames"
    os.makedirs(output_dir, exist_ok=True)
    
    pipeline = DetectionPipeline(
        camera_index=0,
        model_name="yolov8n.pt"
    )
    
    pipeline.start()
    
    try:
        while pipeline.is_running():
            success, frame, metadata, result = pipeline.process_frame()
            
            if not success:
                continue
            
            # Si hay detecciones, guardar
            if result.count() > 0:
                filename = (f"{output_dir}/frame_{metadata.frame_number:06d}_"
                           f"{result.count()}persons.jpg")
                cv2.imwrite(filename, frame)
                
                print(f"Guardado: {filename} "
                      f"({result.count()} personas, "
                      f"confianza promedio: {sum(d.confidence for d in result.detections) / result.count():.2f})")
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.release()
        cv2.destroyAllWindows()
        print(f"\nFrames guardados en: {output_dir}")


# ============================================================================
# EJEMPLO 7: Procesar Solo Frames de Alta Confianza
# ============================================================================

"""
Procesar frames solo cuando la confianza promedio es alta.
Útil para filtrar falsos positivos.
"""

def example_7_high_confidence_processing():
    import cv2
    from edge_service import DetectionPipeline
    
    pipeline = DetectionPipeline(
        camera_index=0,
        model_name="yolov8n.pt",
        confidence_threshold=0.3,  # Bajo para detectar más
    )
    
    pipeline.start()
    
    try:
        while pipeline.is_running():
            success, frame, metadata, result = pipeline.process_frame()
            
            if not success:
                continue
            
            if result.count() > 0:
                # Calcular confianza promedio
                avg_confidence = (
                    sum(d.confidence for d in result.detections) / result.count()
                )
                
                # Solo procesar si confianza promedio > 0.7
                if avg_confidence > 0.7:
                    print(f"Alta confianza detectada: {avg_confidence:.2f} "
                          f"({result.count()} personas)")
                    
                    # Aquí puedes hacer algo especial
                    # Ej: guardar, alertar, etc.
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.release()
        cv2.destroyAllWindows()


# ============================================================================
# EJEMPLO 8: Medir Rendimiento del Pipeline
# ============================================================================

"""
Medir y reportar rendimiento en tiempo real.
"""

def example_8_performance_monitoring():
    import cv2
    import time
    from edge_service import DetectionPipeline
    
    pipeline = DetectionPipeline(
        camera_index=0,
        model_name="yolov8n.pt"
    )
    
    pipeline.start()
    
    frame_times = []
    start_time = time.time()
    
    try:
        while pipeline.is_running():
            frame_start = time.perf_counter()
            
            success, frame, metadata, result = pipeline.process_frame()
            
            frame_elapsed = (time.perf_counter() - frame_start) * 1000  # ms
            frame_times.append(frame_elapsed)
            
            if not success:
                continue
            
            # Mantener últimos 30 frames
            if len(frame_times) > 30:
                frame_times.pop(0)
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            # Mostrar stats cada 60 frames
            if metadata.frame_number % 60 == 0:
                elapsed = time.time() - start_time
                avg_frame_time = sum(frame_times) / len(frame_times)
                fps = 1000 / avg_frame_time if avg_frame_time > 0 else 0
                
                print(f"\nTiempo transcurrido: {elapsed:.1f}s")
                print(f"Frames procesados: {metadata.frame_number}")
                print(f"FPS promedio: {fps:.1f}")
                print(f"Tiempo/frame promedio: {avg_frame_time:.2f}ms")
                print(f"Tiempo inferencia: {result.inference_time_ms:.2f}ms")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.release()
        cv2.destroyAllWindows()


# ============================================================================
# EJEMPLO 9: Risk Analysis con BehaviorAnalyzer (FASE 2)
# ============================================================================

"""
Analizar comportamiento de cada persona y calcular risk_score.
Útil para debugging de reglas de comportamiento.
"""

def example_9_risk_analysis():
    import cv2
    from edge_service import DetectionPipeline, BehaviorAnalyzer
    
    pipeline = DetectionPipeline(camera_index=0, draw_detections=True)
    analyzer = BehaviorAnalyzer()
    
    pipeline.start()
    
    try:
        while pipeline.is_running():
            success, frame, metadata, result = pipeline.process_frame()
            
            if not success:
                continue
            
            # Analizar riesgo para cada detección
            for i, det in enumerate(result.detections):
                if det.landmarks:
                    analysis = analyzer.analyze(det.landmarks)
                    
                    risk_level = analyzer.get_risk_level_text(analysis.risk_score)
                    print(f"Persona {i}: Risk={analysis.risk_score:.2f} ({risk_level}) "
                          f"| Reglas: {', '.join(analysis.rules_triggered)}")
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.release()
        cv2.destroyAllWindows()


# ============================================================================
# EJEMPLO 10: Complete FASE 2 Pipeline
# ============================================================================

"""
Ejemplo completo mostrando FASE 2 integrada.
"""

def example_10_complete_fase2():
    import cv2
    from edge_service import DetectionPipeline
    
    pipeline = DetectionPipeline(
        camera_index=0,
        frame_width=1280,
        frame_height=720,
        target_fps=30,
        model_name="yolov8n.pt",
        draw_detections=True,
    )
    
    pipeline.start()
    frame_count = 0
    
    try:
        while pipeline.is_running():
            success, frame, metadata, result = pipeline.process_frame()
            
            if not success:
                continue
            
            frame_count += 1
            
            # Información cada 60 frames
            if frame_count % 60 == 0:
                print(f"\nFrame {metadata.frame_number}: {result.count()} personas")
                
                for i, det in enumerate(result.detections):
                    print(f"  Persona {i+1}: Risk={det.risk_score:.2f}, "
                          f"Landmarks={'✓' if det.landmarks else '✗'}")
                
                if hasattr(pipeline, '_ring_buffer') and pipeline._ring_buffer:
                    buf_stats = pipeline._ring_buffer.get_stats()
                    print(f"  Buffer: {buf_stats.current_size}/{buf_stats.max_size} "
                          f"({buf_stats.memory_usage_mb:.1f}MB)")
            
            pipeline.display_frame_with_info(frame, metadata, result)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        pipeline.print_stats()
        pipeline.release()
        cv2.destroyAllWindows()


# ============================================================================
# MAIN: Elegir qué ejemplo ejecutar
# ============================================================================

if __name__ == "__main__":
    import sys
    
    examples = {
        "1": ("Detección básica", example_1_basic_object_detection),
        "2": ("Detección avanzada", example_2_advanced_detection),
        "3": ("Pipeline (RECOMENDADO)", example_3_detection_pipeline),
        "4": ("Context Manager", example_4_context_manager),
        "5": ("Estadísticas", example_5_pipeline_statistics),
        "6": ("Guardar frames", example_6_save_detections),
        "7": ("Alta confianza", example_7_high_confidence_processing),
        "8": ("Performance", example_8_performance_monitoring),
        "9": ("Risk Analysis (FASE 2)", example_9_risk_analysis),
        "10": ("FASE 2 Completa", example_10_complete_fase2),
    }
    
    print("Ejemplos disponibles:")
    for key, (desc, _) in examples.items():
        print(f"  {key}: {desc}")
    
    choice = input("\nElige un ejemplo (1-10): ").strip()
    
    if choice in examples:
        print(f"\nEjecutando: {examples[choice][0]}\n")
        examples[choice][1]()
    else:
        print("Opción inválida")
        sys.exit(1)
