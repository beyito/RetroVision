from django.db.models import Q
from urllib import request as urlrequest, error as urlerror
import uuid
import json
import time
import base64
from django.core.cache import cache
from django.conf import settings
from paho.mqtt import publish as mqtt_publish
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from django.http import HttpResponse, JsonResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Camera, SecurityAlert, Telemetria_Afluencia, Heatmaps
from .serializers import (
    CameraSerializer,
    SecurityAlertSerializer,
    TelemetriaAfluenciaSerializer,
    HeatmapsSerializer,
    TenantSerializer,
    StoreSerializer,
    EdgeNodeSerializer,
)
from .authentication import EdgeNodeAuthentication
from .models import Tenant, Store, EdgeNode


def is_admin_software(user) -> bool:
    return getattr(user, "role", "") == "ADMIN_SOFTWARE" or getattr(user, "is_superuser", False)


def is_admin_empresa(user) -> bool:
    return getattr(user, "role", "") == "ADMIN_EMPRESA"


def is_seguridad(user) -> bool:
    return getattr(user, "role", "") == "SEGURIDAD"


def scope_by_user(queryset, user, tenant_field: str, store_field: str):
    """Scopes a queryset according to the authenticated dashboard user."""
    if isinstance(user, EdgeNode):
        return queryset
    if is_admin_software(user):
        return queryset
    if is_admin_empresa(user) and getattr(user, "tenant_id", None):
        return queryset.filter(**{tenant_field: user.tenant_id})
    if is_seguridad(user) and getattr(user, "store_id", None):
        return queryset.filter(**{store_field: user.store_id})
    return queryset.none()


def _optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _camera_ids_for_scope(user, tenant_id=None, store_id=None, camera_id=None):
    queryset = Camera.objects.select_related("store", "store__tenant").all()

    if not is_admin_software(user):
        queryset = scope_by_user(queryset, user, "store__tenant_id", "store_id")

    if tenant_id is not None:
        queryset = queryset.filter(store__tenant_id=tenant_id)
    if store_id is not None:
        queryset = queryset.filter(store_id=store_id)
    if camera_id:
        queryset = queryset.filter(camera_id=camera_id)

    return list(queryset.values_list("camera_id", flat=True))


def _apply_context_filters(request, queryset, *, camera_field="camera_id"):
    user = request.user
    tenant_id = _optional_int(request.query_params.get("tenant"))
    store_id = _optional_int(request.query_params.get("store"))
    camera_id = request.query_params.get("camera_id") or None

    if isinstance(user, EdgeNode):
        if camera_id:
            return queryset.filter(**{camera_field: camera_id})
        return queryset

    allowed_camera_ids = _camera_ids_for_scope(
        user,
        tenant_id=tenant_id,
        store_id=store_id,
        camera_id=camera_id,
    )
    if not allowed_camera_ids:
        return queryset.none()
    return queryset.filter(**{f"{camera_field}__in": allowed_camera_ids})


class TenantViewSet(viewsets.ModelViewSet):
    """API endpoint that allows tenants to be viewed by dashboard users."""
    permission_classes = [IsAuthenticated]
    queryset = Tenant.objects.none()
    serializer_class = TenantSerializer

    def get_queryset(self):
        queryset = Tenant.objects.all().order_by('name')
        user = self.request.user
        if is_admin_software(user):
            return queryset
        if getattr(user, "tenant_id", None):
            return queryset.filter(id=user.tenant_id)
        return queryset.none()


class StoreViewSet(viewsets.ModelViewSet):
    """API endpoint that allows stores to be viewed by dashboard users."""
    permission_classes = [IsAuthenticated]
    queryset = Store.objects.none()
    serializer_class = StoreSerializer

    def get_queryset(self):
        queryset = Store.objects.select_related('tenant').all().order_by('tenant__name', 'name')
        queryset = scope_by_user(queryset, self.request.user, "tenant_id", "id")
        tenant_id = _optional_int(self.request.query_params.get("tenant"))
        if tenant_id is not None:
            queryset = queryset.filter(tenant_id=tenant_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            serializer.save(tenant_id=user.tenant_id)
            return
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            serializer.save(tenant_id=user.tenant_id)
            return
        serializer.save()


class EdgeNodeViewSet(viewsets.ModelViewSet):
    """API endpoint that allows edge nodes to be viewed by dashboard users."""
    permission_classes = [IsAuthenticated]
    queryset = EdgeNode.objects.none()
    serializer_class = EdgeNodeSerializer

    def get_queryset(self):
        queryset = EdgeNode.objects.select_related('store', 'store__tenant').all().order_by('node_id')
        return scope_by_user(queryset, self.request.user, "store__tenant_id", "store_id")

    def perform_create(self, serializer):
        user = self.request.user
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            allowed_store = Store.objects.filter(
                id=self.request.data.get("store"),
                tenant_id=user.tenant_id,
            ).first()
            serializer.save(store=allowed_store)
            return
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            allowed_store = Store.objects.filter(
                id=self.request.data.get("store", serializer.instance.store_id),
                tenant_id=user.tenant_id,
            ).first()
            serializer.save(store=allowed_store)
            return
        serializer.save()


class CameraViewSet(viewsets.ModelViewSet):
    """API endpoint for camera profiles and queue ROI configuration."""
    permission_classes = [IsAuthenticated]
    authentication_classes = (EdgeNodeAuthentication, JWTAuthentication, SessionAuthentication)
    queryset = Camera.objects.none()
    serializer_class = CameraSerializer
    lookup_field = 'camera_id'

    def get_permissions(self):
        if isinstance(self.request.user, EdgeNode):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = Camera.objects.select_related('store', 'store__tenant', 'edge_node').all().order_by('camera_id')
        user = self.request.user
        if isinstance(user, EdgeNode):
            queryset = queryset.filter(
                Q(store=user.store) & (Q(edge_node=user) | Q(edge_node__isnull=True))
            )
            # Solo permitir cámaras activas de tiendas y tenants que estén activos y al día con el pago
            queryset = queryset.filter(is_active=True, store__is_active=True, store__tenant__is_active=True)
        else:
            queryset = scope_by_user(queryset, user, "store__tenant_id", "store_id")

        tenant_id = _optional_int(self.request.query_params.get("tenant"))
        store_id = _optional_int(self.request.query_params.get("store"))
        camera_id = self.request.query_params.get("camera_id")
        if tenant_id is not None:
            queryset = queryset.filter(store__tenant_id=tenant_id)
        if store_id is not None:
            queryset = queryset.filter(store_id=store_id)
        if camera_id:
            queryset = queryset.filter(camera_id=camera_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        from rest_framework.exceptions import ValidationError
        
        # Validar el límite de cámaras por Tenant para control de facturación
        store_id = self.request.data.get("store")
        if isinstance(user, EdgeNode):
            store = user.store
        elif store_id:
            store = Store.objects.select_related("tenant").filter(id=store_id).first()
        else:
            store = None
            
        if store and store.tenant:
            tenant = store.tenant
            existing_count = Camera.objects.filter(store__tenant=tenant).count()
            if existing_count >= tenant.max_cameras:
                raise ValidationError({"detail": f"Límite de cámaras ({tenant.max_cameras}) alcanzado para tu plan de suscripción."})

        if isinstance(user, EdgeNode):
            serializer.save(store=user.store, edge_node=user)
            return
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            allowed_store = Store.objects.filter(
                id=store_id,
                tenant_id=user.tenant_id,
            ).first()
            serializer.save(
                store=allowed_store,
                edge_node=serializer.validated_data.get("edge_node"),
            )
            return
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if isinstance(user, EdgeNode):
            serializer.save(store=user.store, edge_node=user)
            return
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            allowed_store = Store.objects.filter(
                id=self.request.data.get("store", serializer.instance.store_id),
                tenant_id=user.tenant_id,
            ).first()
            serializer.save(
                store=allowed_store,
                edge_node=serializer.validated_data.get("edge_node", serializer.instance.edge_node),
            )
            return
        serializer.save()

    @action(detail=True, methods=["get"], url_path="snapshot")
    def snapshot(self, request, camera_id=None):
        camera = self.get_object()
        edge_node = camera.edge_node
        if edge_node is None:
            return JsonResponse(
                {"detail": "La cámara no está vinculada a ningún nodo Edge."},
                status=400,
            )

        correlation_id = str(uuid.uuid4())
        request_topic = f"retrovision/edge/{edge_node.node_id}/snapshot/request"
        payload = {
            "camera_id": camera.camera_id,
            "correlation_id": correlation_id,
        }

        # Intentar publicar por MQTT
        mqtt_sent = False
        try:
            mqtt_publish.single(
                request_topic,
                payload=json.dumps(payload),
                qos=1,
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
            )
            mqtt_sent = True
        except Exception as exc:
            # Fallback legacy si MQTT_BROKER no está disponible
            if not edge_node.control_api_base_url:
                return JsonResponse(
                    {"detail": f"Error al enviar solicitud de snapshot por MQTT: {exc}"},
                    status=502,
                )

        if mqtt_sent:
            # Polling del cache de Django (Redis) con un máximo de 4.0 segundos
            cache_key = f"snapshot_response:{correlation_id}"
            timeout = 4.0
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                response_data = cache.get(cache_key)
                if response_data is not None:
                    cache.delete(cache_key)
                    
                    if "error" in response_data:
                        return JsonResponse({"detail": response_data["error"]}, status=502)
                    
                    img_b64 = response_data.get("image_base64")
                    if not img_b64:
                        return JsonResponse({"detail": "La respuesta del Edge no contenía la imagen."}, status=502)
                    
                    try:
                        img_bytes = base64.b64decode(img_b64)
                        return HttpResponse(img_bytes, content_type="image/jpeg")
                    except Exception as decode_exc:
                        return JsonResponse({"detail": f"Error decodificando imagen: {decode_exc}"}, status=502)
                        
                time.sleep(0.1)

        # Fallback HTTP legacy si falló MQTT/timeout y tenemos control_api_base_url
        if edge_node.control_api_base_url:
            snapshot_url = f"{edge_node.control_api_base_url.rstrip('/')}/snapshot?camera_id={camera.camera_id}"
            upstream_request = urlrequest.Request(
                snapshot_url,
                headers={
                    "X-Edge-Node-Id": edge_node.node_id,
                    "X-Edge-Api-Key": edge_node.api_key,
                },
                method="GET",
            )
            try:
                with urlrequest.urlopen(upstream_request, timeout=4) as upstream_response:
                    payload = upstream_response.read()
                    content_type = upstream_response.headers.get("Content-Type", "image/jpeg")
                    return HttpResponse(payload, content_type=content_type)
            except urlerror.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore") or "Error del edge al generar snapshot (fallback)."
                return JsonResponse({"detail": detail}, status=exc.code)
            except Exception as http_exc:
                return JsonResponse({"detail": f"Timeout en MQTT y error en fallback HTTP: {http_exc}"}, status=504)
        
        return JsonResponse({"detail": "Timeout esperando respuesta de snapshot del Edge Node (4s)."}, status=504)


from rest_framework.pagination import PageNumberPagination

class AlertsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

class SecurityAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows security alerts to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = SecurityAlert.objects.none()
    serializer_class = SecurityAlertSerializer
    pagination_class = AlertsPagination

    def get_queryset(self):
        queryset = SecurityAlert.objects.all().order_by('-timestamp')
        return _apply_context_filters(self.request, queryset)

    @action(detail=False, methods=["post"], url_path="presigned-url", authentication_classes=(EdgeNodeAuthentication,), permission_classes=[IsAuthenticated])
    def presigned_url(self, request):
        import os
        import boto3
        from django.utils.text import slugify
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone
        from .models import EdgeNode, Camera, SecurityAlert
        
        edge_node = request.user
        if not isinstance(edge_node, EdgeNode):
            return JsonResponse({"detail": "Solo los nodos Edge autorizados pueden solicitar URLs pre-firmadas."}, status=403)
            
        camera_id = request.data.get("camera_id")
        filename = request.data.get("filename")
        risk_score = request.data.get("risk_score")
        rules_triggered = request.data.get("rules_triggered", [])
        zona = request.data.get("zona", "")
        raw_timestamp = request.data.get("timestamp")
        
        if not camera_id or not filename:
            return JsonResponse({"detail": "camera_id y filename son requeridos."}, status=400)
            
        try:
            camera = Camera.objects.select_related("store", "store__tenant").get(
                camera_id=camera_id,
                store=edge_node.store
            )
        except Camera.DoesNotExist:
            return JsonResponse({"detail": "La cámara no pertenece a este nodo Edge o no existe."}, status=404)
            
        tenant_name = camera.store.tenant.name
        store_name = camera.store.name
        
        tenant_folder = slugify(tenant_name)
        store_folder = slugify(store_name)
        camera_folder = slugify(camera_id)
        s3_key = f"{tenant_folder}/{store_folder}/{camera_folder}/alertas/{filename}"
        
        bucket_name = getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
        aws_access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        aws_secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        aws_region = getattr(settings, "AWS_S3_REGION_NAME", "us-east-1")
        
        presigned_url_str = ""
        s3_url = ""
        
        timestamp = None
        if raw_timestamp:
            parsed = parse_datetime(str(raw_timestamp))
            if parsed:
                if timezone.is_naive(parsed):
                    timestamp = timezone.make_aware(parsed, timezone.get_current_timezone())
                else:
                    timestamp = parsed
        if not timestamp:
            timestamp = timezone.now()
            
        if bucket_name:
            try:
                if aws_access_key and aws_secret_key:
                    s3_client = boto3.client(
                        "s3",
                        aws_access_key_id=aws_access_key,
                        aws_secret_key=aws_secret_key,
                        region_name=aws_region,
                        config=boto3.session.Config(signature_version="s3v4")
                    )
                else:
                    s3_client = boto3.client(
                        "s3",
                        region_name=aws_region,
                        config=boto3.session.Config(signature_version="s3v4")
                    )
                
                presigned_url_str = s3_client.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": bucket_name,
                        "Key": s3_key,
                        "ContentType": "video/mp4",
                    },
                    ExpiresIn=3600,
                )
                s3_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{s3_key}"
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to generate pre-signed URL: {e}")
                return JsonResponse({"detail": f"Error de S3: {e}"}, status=502)
        else:
            s3_url = request.build_absolute_uri(settings.MEDIA_URL + f"alerts/{s3_key}") if hasattr(settings, "MEDIA_URL") else f"/media/alerts/{s3_key}"
            presigned_url_str = request.build_absolute_uri(f"/api/alerts/upload-fallback/?key={s3_key}")
            
        alert = SecurityAlert.objects.create(
            timestamp=timestamp,
            camera_id=camera_id,
            risk_score=float(risk_score) if risk_score is not None else 0.75,
            rules_triggered=rules_triggered if isinstance(rules_triggered, list) else [str(rules_triggered)],
            video_path=s3_url,
            zona=zona
        )
        
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "security_alerts",
                {
                    "type": "alert_message",
                    "alert": {
                        "id": alert.id,
                        "timestamp": alert.timestamp.isoformat(),
                        "camera_id": alert.camera_id,
                        "risk_score": alert.risk_score,
                        "rules_triggered": alert.rules_triggered,
                        "video_path": alert.video_path,
                        "zona": alert.zona,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                    }
                }
            )
            
        return JsonResponse({
            "status": "success",
            "alert_id": alert.id,
            "presigned_url": presigned_url_str,
            "s3_url": s3_url
        })

    @action(detail=False, methods=["put"], url_path="upload-fallback", authentication_classes=(), permission_classes=())
    def upload_fallback(self, request):
        s3_key = request.query_params.get("key")
        if not s3_key:
            return HttpResponse("Missing key query parameter", status=400)
            
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        file_data = request.body
        local_path = default_storage.save(f"alerts/{s3_key}", ContentFile(file_data))
        return HttpResponse("Local upload success", status=200)

class TelemetriaAfluenciaViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows commercial telemetry to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Telemetria_Afluencia.objects.none()
    serializer_class = TelemetriaAfluenciaSerializer

    def get_queryset(self):
        queryset = Telemetria_Afluencia.objects.all().order_by('-timestamp')
        return _apply_context_filters(self.request, queryset)[:100]

    def list(self, request, *args, **kwargs):
        user = request.user
        tenant = request.query_params.get("tenant") or ""
        store = request.query_params.get("store") or ""
        camera_id = request.query_params.get("camera_id") or ""
        
        user_key = f"user:{user.id if hasattr(user, 'id') else user.username}"
        cache_key = f"telemetry_list:{user_key}:{tenant}:{store}:{camera_id}"
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
            
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=2)  # Cache for 2 seconds
        return response

    @action(detail=False, methods=['get'])
    def historical(self, request):
        from django.utils import timezone
        from django.db.models.functions import Extract
        from datetime import timedelta
        from collections import defaultdict
        
        user = request.user
        time_range = request.query_params.get("range", "7days")
        tenant = request.query_params.get("tenant") or ""
        store = request.query_params.get("store") or ""
        camera_id = request.query_params.get("camera_id") or ""
        
        user_key = f"user:{user.id if hasattr(user, 'id') else user.username}"
        cache_key = f"historical_telemetry:{user_key}:{time_range}:{tenant}:{store}:{camera_id}"
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
            
        # 1. Determine parameters
        days = 30 if time_range == "30days" else 7
        
        # Calculate date bounds
        start_date = timezone.now() - timedelta(days=days)
        
        # 2. Get scoped queryset
        base_queryset = Telemetria_Afluencia.objects.filter(timestamp__gte=start_date).order_by('timestamp')
        queryset = _apply_context_filters(request, base_queryset)
        
        # 3. Apply Sampling (Downsampling) based on range to prevent payload overloading
        # Sample every 15 minutes for 30days, sample every 5 minutes for 7days
        sampling_minutes = [0, 15, 30, 45] if time_range == "30days" else [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
        
        records = queryset.annotate(
            minute=Extract('timestamp', 'minute'),
            second=Extract('timestamp', 'second')
        ).filter(
            minute__in=sampling_minutes,
            second__lte=10 # Only capture the start of the sample minute to get a single record per interval
        )
        
        # If no records in the sample, fallback to all records within the range (up to 2000 records) to avoid blank dashboard
        record_list = list(records)
        if len(record_list) == 0:
            record_list = list(queryset[:2000])
            
        total_records = len(record_list)
        if total_records == 0:
            resp_data = {
                "total_records_analyzed": 0,
                "total_visitors_estimated": 0,
                "time_range": time_range,
                "peak_hour": "N/A",
                "busiest_sector": "Ninguno",
                "queue_metrics": {
                    "avg_people_in_queue": 0.0,
                    "avg_wait_time_seconds": 0.0,
                    "max_wait_time_seconds": 0.0,
                    "saturation_percentage": 0.0
                },
                "sectors_metrics": {},
                "hourly_inflow": [],
                "daily_inflow": []
            }
            cache.set(cache_key, resp_data, timeout=300)
            return Response(resp_data)
            
        # 4. Aggregate metrics
        total_queue_people = 0
        total_wait_time = 0.0
        max_wait_time = 0.0
        saturated_records_count = 0
        
        sector_totals = defaultdict(int)
        sector_maxes = defaultdict(int)
        sector_record_counts = defaultdict(int)
        
        # For hourly inflow (entries by hour of the day)
        hourly_inflow_by_hour = defaultdict(int)
        
        # For daily inflow
        daily_inflow_by_day = defaultdict(int)
        
        # To calculate hourly flow and daily flow properly:
        # Sum of positive entry differences
        prev_entrantes_by_cam = {}
        for r in record_list:
            cam_id = r.camera_id
            
            # Queue metrics
            total_queue_people += r.personas_en_cola
            total_wait_time += r.tiempo_espera_promedio
            if r.tiempo_espera_promedio > max_wait_time:
                max_wait_time = r.tiempo_espera_promedio
            if r.alerta_cola_activa or r.personas_en_cola >= 3:
                saturated_records_count += 1
                
            # Sectores metrics
            sectores = r.sectores or {}
            if isinstance(sectores, dict):
                for name, count in sectores.items():
                    normalized_name = str(name).strip().capitalize() if name else "Desconocido"
                    val = int(count or 0)
                    sector_totals[normalized_name] += val
                    sector_record_counts[normalized_name] += 1
                    if val > sector_maxes[normalized_name]:
                        sector_maxes[normalized_name] = val
                        
            # Flow differences
            val_entrantes = r.personas_entrantes
            hour = r.timestamp.hour
            day_name = r.timestamp.strftime("%A") # e.g. "Monday"
            
            if cam_id in prev_entrantes_by_cam:
                diff = val_entrantes - prev_entrantes_by_cam[cam_id]
                if diff > 0:
                    hourly_inflow_by_hour[hour] += diff
                    daily_inflow_by_day[day_name] += diff
            prev_entrantes_by_cam[cam_id] = val_entrantes
            
        # Compute final aggregates
        avg_people_in_queue = total_queue_people / total_records
        avg_wait_time = total_wait_time / total_records
        saturation_percentage = (saturated_records_count / total_records) * 100.0
        
        sectors_metrics = {}
        for name in sector_totals.keys():
            sectors_metrics[name] = {
                "avg_occupancy": round(sector_totals[name] / sector_record_counts[name], 1),
                "max_occupancy": sector_maxes[name]
            }
            
        # Format hourly inflow distribution
        hourly_inflow = []
        for h in range(24):
            hourly_inflow.append({
                "hour": f"{h:02d}:00",
                "inflow": hourly_inflow_by_hour.get(h, 0)
            })
            
        # Format daily inflow distribution
        day_mapping = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miércoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        day_order = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        daily_inflow = []
        for eng_name, esp_name in day_mapping.items():
            daily_inflow.append({
                "day": esp_name,
                "inflow": daily_inflow_by_day.get(eng_name, 0)
            })
        # Order daily inflow to match calendar week
        daily_inflow.sort(key=lambda x: day_order.index(x["day"]) if x["day"] in day_order else 9)
        
        # Calculate total visitors estimated
        total_visitors_estimated = sum(d["inflow"] for d in daily_inflow)
        
        # Find peak hour
        peak_hour_val = -1
        peak_hour_str = "N/A"
        for h_data in hourly_inflow:
            if h_data["inflow"] > peak_hour_val:
                peak_hour_val = h_data["inflow"]
                peak_hour_str = h_data["hour"]
                
        # Find busiest sector
        busiest_sector = "Ninguno"
        highest_avg = 0.0
        for s_name, s_data in sectors_metrics.items():
            if s_data["avg_occupancy"] > highest_avg:
                highest_avg = s_data["avg_occupancy"]
                busiest_sector = s_name
        
        resp_data = {
            "total_records_analyzed": total_records,
            "total_visitors_estimated": total_visitors_estimated,
            "time_range": time_range,
            "peak_hour": peak_hour_str,
            "busiest_sector": busiest_sector,
            "queue_metrics": {
                "avg_people_in_queue": round(avg_people_in_queue, 1),
                "avg_wait_time_seconds": round(avg_wait_time, 1),
                "max_wait_time_seconds": round(max_wait_time, 1),
                "saturation_percentage": round(saturation_percentage, 1)
            },
            "sectors_metrics": sectors_metrics,
            "hourly_inflow": hourly_inflow,
            "daily_inflow": daily_inflow
        }
        cache.set(cache_key, resp_data, timeout=300)  # Cache for 5 minutes
        return Response(resp_data)


class HeatmapsViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows visual heatmaps to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Heatmaps.objects.none()
    serializer_class = HeatmapsSerializer

    def get_queryset(self):
        queryset = Heatmaps.objects.all().order_by('-timestamp')
        return _apply_context_filters(self.request, queryset)[:50]

    def list(self, request, *args, **kwargs):
        user = request.user
        tenant = request.query_params.get("tenant") or ""
        store = request.query_params.get("store") or ""
        camera_id = request.query_params.get("camera_id") or ""
        
        user_key = f"user:{user.id if hasattr(user, 'id') else user.username}"
        cache_key = f"heatmaps_list:{user_key}:{tenant}:{store}:{camera_id}"
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
            
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=2)  # Cache for 2 seconds
        return response
