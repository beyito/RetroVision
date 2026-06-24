# Guía de Despliegue en Producción (AWS + Supabase + Docker)

Esta guía detalla el aprovisionamiento de infraestructura y el despliegue del sistema central de RetroVision en producción utilizando **Amazon EC2, Amazon S3, IAM Roles, Supabase PostgreSQL** y **Docker Compose**.

---

## 1. Configuración de Base de Datos (Supabase)

Para producción, utilizaremos el servicio administrado de **Supabase** conectado mediante su **Supabase Connection Pooler** (`*.pooler.supabase.com`). Esto es fundamental porque la conexión directa a la base de datos de Supabase es solo IPv6, mientras que las instancias EC2 tradicionales no suelen tener IPv6 configurado por defecto. El pooler sí soporta IPv4.

Dependiendo de tu necesidad, puedes elegir uno de los siguientes puertos:
- **Session Pooler (Puerto `5432`)** - *Recomendado*: Mantiene conexiones persistentes a nivel de sesión y es compatible con todas las características de Django (incluyendo cursores).
- **Transaction Pooler (Puerto `6543`)**: Diseñado para picos masivos de tráfico, reutiliza conexiones a nivel de transacción (requiere obligatoriamente desactivar cursores en Django).

Ambas opciones funcionan perfectamente con nuestra configuración en `settings.py` porque:
1. Hemos forzado `"DISABLE_SERVER_SIDE_CURSORS": True` (obligatorio para el puerto `6543` y seguro/soportado para el puerto `5432`).
2. Hemos configurado `"sslmode": "require"` para cifrar toda la transmisión.

### Pasos para configurar:
1. Regístrate o inicia sesión en [Supabase](https://supabase.com/).
2. Crea un nuevo proyecto.
3. Ve a **Project Settings > Database**.
4. Copia la cadena de conexión de **Connection Pooling** y selecciona **Session** (puerto `5432`) o **Transaction** (puerto `6543`).
   - Ejemplo (Session Pooler): `postgresql://postgres.[PROYECTO]:[PASSWORD]@aws-1-[REGION].pooler.supabase.com:5432/postgres?sslmode=require`
5. Esta cadena de conexión se establecerá en la variable de entorno `DATABASE_URL` del backend.

---

## 2. Aprovisionamiento de AWS S3 (Almacenamiento de Alertas)

Las imágenes y videoclips de alertas se almacenan en un bucket S3. El sistema los organiza de forma segura bajo la estructura de directorios:
`tenant_slug/store_slug/camera_id/alertas/filename.mp4`

### A. Crear Bucket S3
1. Abre la consola de **Amazon S3** en AWS.
2. Haz clic en **Create bucket**.
3. Asigna un nombre al bucket (ej: `retrovision-alerts-prod`) y selecciona tu región.
4. Desmarca la opción **Block all public access** para permitir que el frontend cargue los videoclips mediante las URLs firmadas de lectura (o configura políticas específicas).
5. Crea el bucket.

### B. Configuración de CORS en S3
Para que el reproductor de video HTML5 del frontend en el navegador pueda reproducir los clips directamente desde S3 sin problemas de origen cruzado, debes configurar la política CORS en el bucket:

1. Entra al bucket en la consola de S3, pestaña **Permissions > Cross-origin resource sharing (CORS)**.
2. Pega la siguiente configuración JSON:
```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "GET",
            "PUT",
            "HEAD"
        ],
        "AllowedOrigins": [
            "*"
        ],
        "ExposedHeaders": [
            "ETag"
        ],
        "MaxAgeSeconds": 3000
    }
]
```
3. Guarda los cambios.

---

## 3. Configuración de Seguridad en AWS (IAM Roles)

Para evitar almacenar contraseñas/claves estáticas de AWS en el servidor Django (lo cual es una mala práctica), utilizaremos un **IAM Instance Profile** asignado a la instancia EC2.

### A. Crear Política de S3
1. Ve a la consola de **IAM > Policies** y haz clic en **Create policy**.
2. Selecciona la pestaña **JSON** y añade los permisos de escritura y lectura:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::retrovision-alerts-prod",
                "arn:aws:s3:::retrovision-alerts-prod/*"
            ]
        }
    ]
}
```
*(Reemplaza `retrovision-alerts-prod` con el nombre real de tu bucket).*
3. Nombra la política como `RetroVisionS3Policy` y créala.

### B. Crear IAM Role para EC2
1. Ve a **IAM > Roles > Create role**.
2. Elige **AWS service** y selecciona **EC2** como el caso de uso.
3. Busca y adjunta la política `RetroVisionS3Policy`.
4. Nombra al rol como `RetroVisionEC2Role` y haz clic en **Create role**.

---

## 4. Creación y Configuración de AWS EC2

### A. Lanzar Instancia
1. Abre la consola de **EC2 > Launch instance**.
2. Selecciona **Ubuntu Server 22.04 LTS** (o similar) de 64 bits.
3. Tipo de instancia: Se recomienda al menos `t3.medium` (2 vCPUs, 4GB RAM) para producción estable.
4. Par de claves (Key pair): Elige uno existente o crea uno nuevo para conectarte vía SSH.

### B. Asignar IAM Role a la Instancia
Una vez lanzada la instancia:
1. Selecciónala en el panel de EC2.
2. Haz clic en **Actions > Security > Modify IAM role**.
3. Selecciona el rol `RetroVisionEC2Role` que creamos y guarda.

### C. Grupo de Seguridad (Security Group)
Configura el grupo de seguridad de tu EC2 con las siguientes reglas de entrada:

| Tipo | Puerto | Origen | Descripción |
|---|---|---|---|
| SSH | 22 | Tu IP pública | Acceso administrativo |
| HTTP | 80 | 0.0.0.0/0 | Acceso web para frontend y API |
| Custom TCP | 1883 | Nodos Edge IP o 0.0.0.0/0 | Entrada de mensajes MQTT de cámaras remotas |
| Custom TCP | 8000 | Nodos Edge IP o 0.0.0.0/0 | Opcional (si se quiere acceder al backend directo) |

---

## 5. Variables de Entorno del Backend (`.env`)

En el EC2, crea un archivo `.env` dentro de la carpeta `backend/` con las siguientes variables:

```bash
# Entorno Django
DJANGO_SECRET_KEY=un-secreto-muy-seguro-para-produccion
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=midominio.com,IP_PUBLICA_EC2

# Base de datos Supabase (Session Pooler - Puerto 5432 o Transaction Pooler - Puerto 6543)
# IMPORTANTE: Si tu contraseña contiene caracteres especiales (como #, @, :, /), debes codificarlos en formato URL.
# Ejemplo: si tu contraseña es "#CObuchan898", debes escribir "%23CObuchan898".
DATABASE_URL=postgresql://postgres.xxx:pass@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require

# Configuración de S3 de AWS
AWS_STORAGE_BUCKET_NAME=retrovision-alerts-prod
AWS_S3_REGION_NAME=us-east-1

# Nota: AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY NO son necesarios si asignaste 
# el IAM Role a la instancia EC2. Boto3 los resolverá automáticamente.
```

---

## 6. Pasos para el Despliegue en la Instancia EC2

Una vez conectado por SSH a tu máquina de Ubuntu:

### A. Instalar Docker y Docker Compose
Ejecuta la instalación limpia de Docker:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable docker
sudo systemctl start docker
# Opcional: añade tu usuario al grupo docker para evitar usar sudo
sudo usermod -aG docker $USER
newgrp docker
```

### B. Clonar y Desplegar
Clona el repositorio e inicia los contenedores de producción:
```bash
# 1. Clonar el repositorio
git clone <URL_DE_TU_REPOSITORIO> retrovision
cd retrovision

# 2. Configurar variables de entorno
nano backend/.env
# (Pega las variables especificadas en la sección 5 y guarda)

# 3. Levantar la infraestructura
docker compose -f docker-compose.prod.yml up -d --build
```

### C. Ejecutar Migraciones de Base de Datos
Aplica las migraciones iniciales y de SaaS en Supabase desde el contenedor de Django:
```bash
docker exec -it retrovision-web-prod python manage.py migrate
docker exec -it retrovision-web-prod python manage.py collectstatic --noinput
```

### D. Crear Superusuario Inicial
Crea el administrador principal de la plataforma SaaS:
```bash
docker exec -it retrovision-web-prod python manage.py createsuperuser
```

---

## 7. Flujo de Actualización en un Clic (CD Simplificado)
Cuando hagas cambios en tu código y los subas a Git, para actualizar tu servidor producción EC2 solo necesitas correr:
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
docker exec -it retrovision-web-prod python manage.py migrate
```
Esto reconstruirá el frontend con Nginx, levantará el servidor Daphne (Django ASGI), reconectará a Supabase y mantendrá tu sistema en vivo con cero lag y total consistencia de datos.

> [!TIP]
> **Entrenamiento Automático de Modelos Predictivos (ML)**:
> Al levantar el contenedor `retrovision-web-prod` mediante Docker Compose, el comando de inicio ejecuta automáticamente `python scratch/train_forecasting_models.py || true` antes de iniciar Daphne. Esto genera los archivos `.joblib` en caliente en el directorio `/app/scratch/` usando los datos de PostgreSQL.
>
> Si deseas forzar un re-entrenamiento manual de los modelos predictivos en caliente sin reiniciar el contenedor, puedes ejecutar:
> ```bash
> docker exec -it retrovision-web-prod python scratch/train_forecasting_models.py
> ```

---

## 8. Configuración de HTTPS / SSL (Let's Encrypt)

Los navegadores modernos (como Chrome) bloquean o advierten sobre descargas de archivos `.zip` o ejecutables que se realicen a través de conexiones inseguras HTTP (`http://15.229.143.177/...`). 

Para resolver esta advertencia y proteger todo el tráfico, debes habilitar **HTTPS** usando un dominio propio y un certificado gratuito de **Let's Encrypt (Certbot)**.

### Paso A: Apuntar tu dominio al EC2
1. Compra o configura un dominio (ej: `retrovision.tudominio.com`).
2. En tu proveedor de DNS, añade un registro tipo **A** que apunte al **IP Público** de tu instancia EC2.

### Paso B: Modificar puertos en Docker Compose
Para que el Nginx del servidor host maneje el SSL (Terminación SSL), cambiaremos el puerto del contenedor frontend para que no choque con el puerto 80 del host.

1. Abre tu `docker-compose.prod.yml`.
2. Modifica la sección de `frontend` para cambiar los puertos mapeados a `8080:80`:
```yaml
  frontend:
    ...
    ports:
      - "8080:80"
```
3. Reinicia la aplicación: `docker compose -f docker-compose.prod.yml up -d`

### Paso C: Instalar Nginx y Certbot en el servidor host
1. Instala Nginx en tu sistema operativo Ubuntu host:
```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

2. Crea un archivo de configuración para tu sitio:
```bash
sudo nano /etc/nginx/sites-available/retrovision
```

3. Pega la siguiente configuración (reemplaza `retrovision.tudominio.com` por tu dominio real):
```nginx
server {
    listen 80;
    server_name retrovision.tudominio.com;

    # Proxy para HTTP y WebSockets hacia Docker en el puerto 8080
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Soporte para WebSockets
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

4. Habilita el sitio y reinicia Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/retrovision /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Paso D: Generar el Certificado SSL
Ejecuta Certbot para obtener el certificado SSL e instalarlo automáticamente en Nginx:
```bash
sudo certbot --nginx -d retrovision.tudominio.com
```
*Sigue las instrucciones en pantalla, introduce tu correo y acepta los términos. Certbot configurará automáticamente la redirección obligatoria de HTTP a HTTPS.*

¡Listo! A partir de ese momento, tu aplicación cargará bajo `https://retrovision.tudominio.com` y podrás descargar el agente ZIP sin ninguna advertencia del navegador.

---

## 9. Configuración y Empaquetado del Agente Edge (Tiendas)

El agente que corre en las tiendas (`retrovision_edge`) requiere conectarse a tu backend y al broker MQTT instalados en el EC2 de producción.

Para evitar que tus clientes tengan que configurar manualmente las direcciones IP del servidor, debes empaquetar el agente con la configuración correcta de producción antes de subirlo a Git/EC2.

### Paso A: Modificar los scripts de inicio en el código fuente
Abre los siguientes archivos en tu entorno de desarrollo local:
1. **[`retrovision_edge/iniciar_retrovision.sh`](file:///c:/SW1_PROYECTO/retrovision_edge/iniciar_retrovision.sh)** (Líneas 9 y 10)
2. **[`retrovision_edge/iniciar_retrovision.bat`](file:///c:/SW1_PROYECTO/retrovision_edge/iniciar_retrovision.bat)** (Líneas 9 y 10)

Reemplaza los valores por defecto (`localhost`) por la IP pública de tu EC2 o tu dominio de producción:

```bash
# Ejemplo usando IP Pública (si no tienes dominio aún)
SAAS_BACKEND_URL="http://15.229.143.177:8000"  # O http://15.229.143.177 si usas el proxy de Nginx
SAAS_MQTT_HOST="15.229.143.177"

# Ejemplo usando tu dominio HTTPS (Una vez completado el Paso 8)
SAAS_BACKEND_URL="https://retrovision.tudominio.com"
SAAS_MQTT_HOST="retrovision.tudominio.com"
```

### Paso B: Regenerar el archivo ZIP
Una vez modificados los scripts con las credenciales de producción, corre el script de empaquetado en tu terminal:
```bash
python zip_edge_agent.py
```
Esto creará el archivo comprimido actualizado en `retrovision_web/public/retrovision_edge.zip`.

### Paso C: Subir los cambios a producción
Realiza el commit y empuja los cambios para que se actualicen en el EC2:
```bash
git add retrovision_edge/iniciar_retrovision.sh retrovision_edge/iniciar_retrovision.bat retrovision_web/public/retrovision_edge.zip
git commit -m "configurar edge agent para produccion"
git push
```
Al hacer `git pull` y reconstruir el frontend en tu EC2, cualquier cliente que descargue el agente desde tu panel web tendrá la configuración lista para conectarse automáticamente a producción.

> [!NOTE]
> **Modificación manual alternativa**: Si un cliente ya descargó el agente y tiene problemas para conectar, simplemente debe abrir el archivo `.env` que se genera en la carpeta del agente de su computadora y cambiar manualmente las variables `BACKEND_API_BASE_URL` y `MQTT_BROKER_HOST` por la dirección IP o dominio de tu servidor EC2.
