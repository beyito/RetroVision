# Guía de Despliegue en Producción (AWS + Supabase + Docker)

Esta guía detalla el aprovisionamiento de infraestructura y el despliegue del sistema central de RetroVision en producción utilizando **Amazon EC2, Amazon S3, IAM Roles, Supabase PostgreSQL** y **Docker Compose**.

---

## 1. Configuración de Base de Datos (Supabase)

Para producción, utilizaremos el servicio administrado de **Supabase** conectado mediante su **Session Pooler** (puerto `6543`) en modo transacción.

1. Regístrate o inicia sesión en [Supabase](https://supabase.com/).
2. Crea un nuevo proyecto.
3. Ve a **Project Settings > Database**.
4. Copia la cadena de conexión de **Connection Pooling (Session)**. Debe tener un puerto `6543`.
   - Ejemplo: `postgresql://postgres.[PROYECTO]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require`
   
5. Esta cadena de conexión se establecerá en la variable de entorno `DATABASE_URL` del backend.
   - *Nota*: Django ha sido configurado en `settings.py` para deshabilitar automáticamente los cursores del lado del servidor (`DISABLE_SERVER_SIDE_CURSORS: True`) y forzar SSL (`sslmode: require`) para garantizar compatibilidad con el pooler transaccional.

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

# Base de datos Supabase (Session Pooler)
DATABASE_URL=postgresql://postgres.xxx:pass@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require

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
