#!/bin/bash
clear
echo "==================================================="
echo "  RetroVision Edge Service - Configuración Inicial"
echo "==================================================="
echo ""

# CONFIGURACIÓN CENTRAL DEL SAAS (Modifica esto antes de empaquetar el ZIP para producción)
SAAS_BACKEND_URL="http://localhost:8000"
SAAS_MQTT_HOST="localhost"

# 1. Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado. Instálalo antes de continuar."
    exit 1
fi

# 2. Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "[INFO] Creando entorno virtual (venv)..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "[ERROR] No se pudo crear el entorno virtual. Instala python3-venv si es necesario."
        exit 1
    fi
    echo "[INFO] Entorno virtual creado con éxito."
    echo ""
    echo "[INFO] Instalando dependencias (esto puede tardar unos minutos)..."
    ./venv/bin/pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[ERROR] No se pudieron instalar las dependencias."
        exit 1
    fi
    echo "[INFO] Dependencias instaladas con éxito."
    echo ""
fi

# 3. Configurar archivo .env
if [ ! -f ".env" ]; then
    echo "[INFO] Configurando credenciales del Nodo Edge..."
    echo ""
    read -p "-> Ingresa tu ID del Nodo (ej. burguer_node): " NODE_ID
    read -p "-> Ingresa tu Clave de API (API Key): " API_KEY
    
    # Crear el archivo .env
    cat <<EOT > .env
# RetroVision Edge - Configuración del Cliente
SYNC_CAMERA_CONFIG=true
BACKEND_API_BASE_URL=$SAAS_BACKEND_URL
EDGE_NODE_ID=$NODE_ID
EDGE_API_KEY=$API_KEY
MQTT_ENABLED=true
MQTT_BROKER_HOST=$SAAS_MQTT_HOST
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=retrovision-edge-$NODE_ID
LOG_LEVEL=INFO
LOG_FILE=logs/edge_service.log
DEBUG_MODE=false
MODEL_NAME=best.pt
EOT
    echo ""
    echo "[INFO] Archivo de configuración .env creado con éxito."
    echo ""
fi

# 4. Ejecutar el servicio Edge
echo "[INFO] Iniciando servicio RetroVision Edge..."
echo "==================================================="
./venv/bin/python main.py
