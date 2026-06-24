@echo off
title RetroVision Edge - Setup and Run
echo ===================================================
echo   RetroVision Edge Service - Configuración Inicial
echo ===================================================
echo.

:: CONFIGURACIÓN CENTRAL DEL SAAS (Modifica esto antes de empaquetar el ZIP para producción)
set SAAS_BACKEND_URL=https://retrovis.duckdns.org
set SAAS_MQTT_HOST=retrovis.duckdns.org

:: 1. Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no está instalado o no se encuentra en el PATH del sistema.
    echo Por favor, instala Python 3.10 o superior antes de continuar.
    pause
    exit /b 1
)

:: 2. Crear entorno virtual si no existe
if exist venv goto VENV_OK
echo [INFO] Creando entorno virtual (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
)
echo [INFO] Entorno virtual creado con éxito.
echo.
echo [INFO] Instalando dependencias necesarias (esto puede tardar unos minutos)...
venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
)
echo [INFO] Dependencias instaladas con éxito.
echo.
:VENV_OK

:: 3. Configurar archivo .env si no existe
if exist .env goto RUN_APP
echo [INFO] Configurando credenciales del Nodo Edge...
echo.
set /p NODE_ID="-> Ingresa tu ID del Nodo (ej. burguer_node): "
set /p API_KEY="-> Ingresa tu Clave de API (API Key): "

:: Crear el archivo .env sin bloques de paréntesis para evitar errores de variables
echo # RetroVision Edge - Configuración del Cliente > .env
echo SYNC_CAMERA_CONFIG=true >> .env
echo BACKEND_API_BASE_URL=%SAAS_BACKEND_URL% >> .env
echo EDGE_NODE_ID=%NODE_ID% >> .env
echo EDGE_API_KEY=%API_KEY% >> .env
echo MQTT_ENABLED=true >> .env
echo MQTT_BROKER_HOST=%SAAS_MQTT_HOST% >> .env
echo MQTT_BROKER_PORT=1883 >> .env
echo MQTT_CLIENT_ID=retrovision-edge-%NODE_ID% >> .env
echo LOG_LEVEL=INFO >> .env
echo LOG_FILE=logs/edge_service.log >> .env
echo DEBUG_MODE=false >> .env
echo MODEL_NAME=best.pt >> .env
echo BUFFER_DURATION=8 >> .env
echo WEAPON_CONFIDENCE_THRESHOLD=0.65 >> .env

echo.
echo [INFO] Archivo de configuración .env creado con éxito.
echo.

:RUN_APP
:: 4. Ejecutar el servicio Edge
echo [INFO] Iniciando servicio RetroVision Edge...
echo ===================================================
venv\Scripts\python main.py
pause
