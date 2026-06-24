import os
import sys
import django
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Configurar el entorno de Django para poder importar modelos
SCRATCH_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRATCH_DIR)
sys.path.append(BACKEND_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "retrovision_core.settings")
django.setup()

from alerts_api.models import Telemetria_Afluencia, SecurityAlert, Camera

def generate_blended_dataset():
    print("=========================================================")
    print("RetroVision - Generador de Datasets Multicámara para ML")
    print("=========================================================")
    
    # 1. Obtener la cámara de referencia o crear una por defecto
    camera = Camera.objects.first()
    camera_id = camera.camera_id if camera else "camara_local"
    print(f"[*] Usando Camera ID de referencia para blending: '{camera_id}'")
    
    # Definir los perfiles de cámara para la simulación
    camera_profiles = [
        {"camera_id": "camara_entrada", "profile": "entrada"},
        {"camera_id": camera_id, "profile": "cajas"},  # La cámara real se mapea al perfil de cajas
        {"camera_id": "camara_carnes", "profile": "carnes"},
        {"camera_id": "camara_lacteos", "profile": "lacteos"}
    ]
    print("[*] Generando datos para las siguientes fuentes:")
    for c in camera_profiles:
        print(f"    - '{c['camera_id']}' (Perfil: {c['profile']})")
    
    # 2. Definir límites del dataset (1 año de datos horarios)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    print(f"[*] Rango de simulación: {start_date.date()} al {end_date.date()}")
    
    # Generar rango de fechas por hora
    date_range = pd.date_range(start=start_date, end=end_date, freq='h')
    total_hours = len(date_range)
    print(f"[*] Total de muestras horarias por cámara: {total_hours}")
    
    # 3. Consultar datos históricos reales para blending (solo para la cámara real)
    print("[*] Leyendo datos históricos reales para blending...")
    real_telemetry = Telemetria_Afluencia.objects.filter(
        camera_id=camera_id,
        timestamp__gte=start_date, 
        timestamp__lte=end_date
    ).order_by('timestamp')
    
    real_alerts = SecurityAlert.objects.filter(
        camera_id=camera_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date
    ).order_by('timestamp')
    
    print(f"    - Registros de telemetría real (cámara real): {real_telemetry.count()}")
    print(f"    - Alertas de seguridad real (cámara real): {real_alerts.count()}")
    
    # Agrupar datos reales por hora
    real_telemetry_dict = {}
    for t in real_telemetry:
        hour_dt = t.timestamp.replace(minute=0, second=0, microsecond=0)
        if hour_dt not in real_telemetry_dict:
            real_telemetry_dict[hour_dt] = []
        real_telemetry_dict[hour_dt].append(t)
        
    real_alerts_dict = {}
    for a in real_alerts:
        hour_dt = a.timestamp.replace(minute=0, second=0, microsecond=0)
        if hour_dt not in real_alerts_dict:
            real_alerts_dict[hour_dt] = 0
        real_alerts_dict[hour_dt] += 1
        
    # Feriados fijos (Mes, Día)
    holidays = [
        (1, 1),   # Año Nuevo
        (1, 22),  # Estado Plurinacional
        (5, 1),   # Día del Trabajo
        (6, 21),  # Año Nuevo Andino Amazónico
        (8, 6),   # Día de la Independencia
        (11, 2),  # Todos Santos
        (12, 25)  # Navidad
    ]
    
    dataset_records = []
    
    print("[*] Iniciando simulación matemática y mezcla de datos (blending)...")
    np.random.seed(42)  # Para reproducibilidad
    
    for dt in date_range:
        h = dt.hour
        d = dt.weekday()  # Monday=0, Sunday=6
        m = dt.month
        
        # Variables de Calendario
        is_weekend = 1 if d >= 5 else 0
        is_holiday = 1 if (m, dt.day) in holidays else 0
        is_promotion = 1 if (is_weekend and dt.day <= 7) else 0
        
        dt_naive = dt.replace(tzinfo=None)
        
        for cam_info in camera_profiles:
            cid = cam_info["camera_id"]
            prof = cam_info["profile"]
            
            # Blending: Solo aplica para la cámara real (perfil cajas) si existen registros reales
            real_t_list = []
            real_alerts_count = 0
            
            if cid == camera_id:
                for hour_key, val_list in real_telemetry_dict.items():
                    if hour_key.replace(tzinfo=None) == dt_naive:
                        real_t_list = val_list
                        break
                for hour_key, count in real_alerts_dict.items():
                    if hour_key.replace(tzinfo=None) == dt_naive:
                        real_alerts_count = count
                        break
            
            if real_t_list:
                # Usar datos reales del negocio
                visitor_inflow = sum(r.personas_entrantes for r in real_t_list)
                personas_en_cola = int(np.mean([r.personas_en_cola for r in real_t_list]))
                avg_wait_time = np.mean([r.tiempo_espera_promedio for r in real_t_list])
                
                sectores = real_t_list[0].sectores or {}
                sector_carnes = sectores.get('carnes', 0)
                sector_lacteos = sectores.get('lacteos', 0)
                is_real_data = 1
            else:
                # Simular datos sintéticos según el perfil de la cámara
                is_real_data = 0
                
                # Base de afluencia
                base_inflow = 3.0
                
                # Patrón diario (almuerzo y tarde)
                daily_pattern = 15.0 * np.exp(-((h - 13.0) / 1.8)**2) + 22.0 * np.exp(-((h - 19.0) / 2.2)**2)
                
                if h < 8 or h > 21:
                    daily_pattern = 0.1
                    base_inflow = 0.2
                    
                # Multiplicadores
                weekend_multiplier = 1.5 if d >= 4 else 1.0
                promotion_multiplier = 1.35 if is_promotion else 1.0
                holiday_multiplier = 1.3 if is_holiday else 1.0
                
                # Ajuste de afluencia por perfil de cámara
                if prof == "entrada":
                    # Entrada recibe el flujo principal (más alto)
                    profile_multiplier = 1.8
                elif prof == "cajas":
                    profile_multiplier = 1.0
                else:  # carnes, lacteos
                    # Los sectores comerciales reciben menos tráfico directo
                    profile_multiplier = 0.7
                    
                inflow_calc = (base_inflow + daily_pattern) * weekend_multiplier * promotion_multiplier * holiday_multiplier * profile_multiplier
                noise = np.random.normal(0, 2.0)
                visitor_inflow = max(0, int(round(inflow_calc + noise)))
                
                # Cerrado en feriados mayores
                if (m == 12 and dt.day == 25) or (m == 1 and dt.day == 1):
                    visitor_inflow = 0
                
                # Simular Colas y Tiempos de espera según perfil
                if prof == "cajas" and visitor_inflow > 0:
                    queue_factor = visitor_inflow * 0.14
                    if visitor_inflow > 18:
                        queue_factor += (visitor_inflow - 18) * 0.25
                    personas_en_cola = max(0, int(round(queue_factor + np.random.normal(0, 0.4))))
                    wait_calc = personas_en_cola * 12.0 + (personas_en_cola ** 1.8) * 4.5
                    avg_wait_time = max(0.0, round(wait_calc + np.random.normal(0, 4.0), 1))
                else:
                    # En la entrada o sectores no hay colas registradas
                    personas_en_cola = 0
                    avg_wait_time = 0.0
                    
                # Ocupación por sector según perfil
                sector_carnes = 0
                sector_lacteos = 0
                
                if visitor_inflow > 0:
                    if prof == "carnes":
                        # Alta ocupación en carnes en las mañanas
                        carnes_factor = 0.28 if h < 14 else 0.14
                        sector_carnes = max(0, int(round(visitor_inflow * carnes_factor + np.random.normal(0, 0.5))))
                    elif prof == "lacteos":
                        # Alta ocupación en lácteos por las tardes
                        lacteos_factor = 0.12 if h < 14 else 0.26
                        sector_lacteos = max(0, int(round(visitor_inflow * lacteos_factor + np.random.normal(0, 0.5))))
            
            # Simular alertas de seguridad (las reales si existen, sino simuladas)
            if real_alerts_count > 0:
                security_alerts_count = real_alerts_count
            else:
                alert_prob = 0.004
                if h < 6 or h > 22:
                    alert_prob = 0.05
                elif visitor_inflow > 25:
                    alert_prob = 0.015
                
                # Entrada y cajas tienen mayor propensión a incidentes que los sectores internos
                if prof in ("entrada", "cajas"):
                    alert_prob *= 1.5
                else:
                    alert_prob *= 0.5
                    
                security_alerts_count = 1 if np.random.rand() < alert_prob else 0
                
            queue_saturation_ratio = min(1.0, round(avg_wait_time / 120.0, 3))
            
            dataset_records.append({
                "timestamp": dt.isoformat(),
                "store_id": 1,
                "camera_id": cid,
                "profile": prof,
                "hour": h,
                "day_of_week": d,
                "month": m,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "is_promotion": is_promotion,
                "visitor_inflow": visitor_inflow,
                "personas_en_cola": personas_en_cola,
                "avg_wait_time_seconds": avg_wait_time,
                "queue_saturation_ratio": queue_saturation_ratio,
                "sector_carnes_occupancy": sector_carnes,
                "sector_lacteos_occupancy": sector_lacteos,
                "security_alerts_count": security_alerts_count,
                "is_real_data": is_real_data
            })
            
    # Convertir a DataFrame y guardar
    df = pd.DataFrame(dataset_records)
    output_path = os.path.join(SCRATCH_DIR, "retrovision_ml_dataset.csv")
    df.to_csv(output_path, index=False)
    
    print("=========================================================")
    print(f"[+] ¡Éxito! Dataset multicámara generado correctamente.")
    print(f"[+] Ubicación: {output_path}")
    print(f"[+] Registros totales: {len(df)} (4 cámaras * {total_hours} horas)")
    print(f"[+] Registros mezclados de base de datos real: {df['is_real_data'].sum()}")
    print(f"[+] Total de alertas registradas en el dataset: {df['security_alerts_count'].sum()}")
    print("=========================================================")
    return output_path

if __name__ == "__main__":
    generate_blended_dataset()
