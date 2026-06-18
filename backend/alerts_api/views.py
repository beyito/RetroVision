from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
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
        if isinstance(user, EdgeNode):
            serializer.save(store=user.store, edge_node=user)
            return
        if is_admin_empresa(user) and getattr(user, "tenant_id", None):
            allowed_store = Store.objects.filter(
                id=self.request.data.get("store"),
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

class SecurityAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows security alerts to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = SecurityAlert.objects.none()
    serializer_class = SecurityAlertSerializer

    def get_queryset(self):
        queryset = SecurityAlert.objects.all().order_by('-timestamp')
        return _apply_context_filters(self.request, queryset)

class TelemetriaAfluenciaViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows commercial telemetry to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Telemetria_Afluencia.objects.none()
    serializer_class = TelemetriaAfluenciaSerializer

    def get_queryset(self):
        queryset = Telemetria_Afluencia.objects.all().order_by('-timestamp')
        return _apply_context_filters(self.request, queryset)

class HeatmapsViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows visual heatmaps to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Heatmaps.objects.none()
    serializer_class = HeatmapsSerializer

    def get_queryset(self):
        queryset = Heatmaps.objects.all().order_by('-timestamp')
        return _apply_context_filters(self.request, queryset)
