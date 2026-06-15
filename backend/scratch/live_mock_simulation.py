import json
import time
import random
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

print("Starting live mock data publisher for RetroVision...")
client = mqtt.Client(client_id="retrovision-live-simulator")
try:
    client.connect("localhost", 1883, keepalive=60)
    print("Connected to Mosquitto broker on localhost:1883")
except Exception as e:
    print(f"Error connecting to MQTT broker: {e}")
    print("Please make sure Docker Compose containers are running (docker compose up -d)")
    exit(1)

entrantes = 25
salientes = 12
en_cola = 1
espera_avg = 3.5
iteration = 0

try:
    while True:
        iteration += 1
        iso_now = datetime.now(timezone.utc).isoformat()
        
        # Simular variaciones de flujo comercial
        if random.random() < 0.45:
            entrantes += random.randint(1, 2)
        if random.random() < 0.35:
            salientes += random.randint(1, 2)
            
        # Asegurar que salientes no supere a entrantes
        if salientes > entrantes:
            salientes = entrantes - random.randint(1, 3)
            if salientes < 0:
                salientes = 0
                
        # Simular cola de espera (rango de 0 a 6 personas)
        cola_change = random.choice([-1, 0, 1])
        en_cola = max(0, min(6, en_cola + cola_change))
        
        if en_cola > 0:
            espera_avg = round(en_cola * 3.2 + random.uniform(-0.8, 0.8), 1)
        else:
            espera_avg = 0.0
            
        # Simular coordenadas de puntos calientes en la zona de paso / cola
        # Trapezoid bounds roughly: X between 450 and 1050, Y between 360 and 640
        num_points = random.randint(1, 5)
        points = []
        for _ in range(num_points):
            pt_x = random.randint(480, 1020)
            pt_y = random.randint(370, 630)
            points.append([pt_x, pt_y])
            
        telemetry_payload = {
            "timestamp": iso_now,
            "camera_id": "camera-01",
            "personas_entrantes": entrantes,
            "personas_salientes": salientes,
            "personas_en_cola": en_cola,
            "tiempo_espera_promedio": espera_avg,
            "heatmap_points": points
        }
        
        # Publicar telemetría
        client.publish("retrovision/telemetry", json.dumps(telemetry_payload), qos=1)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Telemetry: In={entrantes}, Out={salientes}, Queue={en_cola}, Wait={espera_avg}s. Points count: {num_points}")
        
        # Cada 6 iteraciones (18 segundos), simular una alerta de seguridad de alto riesgo
        if iteration % 6 == 0:
            alert_rules = random.choice([
                ["Agachado sospechoso", "Mano oculta en bolsillo"],
                ["Intrusión área restringida (Caja)"],
                ["Merodeo prolongado en zona de salida"]
            ])
            risk = round(random.uniform(0.72, 0.98), 2)
            alert_payload = {
                "timestamp": iso_now,
                "camera_id": "camera-01",
                "risk_score": risk,
                "rules_triggered": alert_rules,
                "video_path": f"/var/retrovision/clips/incident_auto_{iteration}.mp4"
            }
            client.publish("retrovision/edge/alerts", json.dumps(alert_payload), qos=1)
            print(f"*** ALERT PUBLISHED *** Risk: {risk * 100}% | Rules: {alert_rules}")
            
        time.sleep(3)
except KeyboardInterrupt:
    print("\nStopping publisher simulator...")
finally:
    client.disconnect()
    print("Disconnected.")
