from rest_framework import serializers
from .models import Tenant, Store, EdgeNode, Camera, SecurityAlert, Telemetria_Afluencia, Heatmaps


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'


class StoreSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)

    class Meta:
        model = Store
        fields = '__all__'


class EdgeNodeSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    tenant_name = serializers.CharField(source='store.tenant.name', read_only=True)

    class Meta:
        model = EdgeNode
        fields = '__all__'


class CameraSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    tenant_name = serializers.CharField(source='store.tenant.name', read_only=True)
    edge_node_name = serializers.CharField(source='edge_node.display_name', read_only=True)

    class Meta:
        model = Camera
        fields = '__all__'

class SecurityAlertSerializer(serializers.ModelSerializer):
    tenant_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    camera_display_name = serializers.SerializerMethodField()

    @staticmethod
    def _get_camera(camera_id):
        return Camera.objects.filter(camera_id=camera_id).select_related('store__tenant').first()

    def get_tenant_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        if camera and camera.store and camera.store.tenant:
            return camera.store.tenant.name
        return ""

    def get_store_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        if camera and camera.store:
            return camera.store.name
        return ""

    def get_camera_display_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        return camera.display_name if camera else ""

    class Meta:
        model = SecurityAlert
        fields = '__all__'

class TelemetriaAfluenciaSerializer(serializers.ModelSerializer):
    tenant_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    camera_display_name = serializers.SerializerMethodField()

    @staticmethod
    def _get_camera(camera_id):
        return Camera.objects.filter(camera_id=camera_id).select_related('store__tenant').first()

    def get_tenant_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        if camera and camera.store and camera.store.tenant:
            return camera.store.tenant.name
        return ""

    def get_store_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        if camera and camera.store:
            return camera.store.name
        return ""

    def get_camera_display_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        return camera.display_name if camera else ""

    class Meta:
        model = Telemetria_Afluencia
        fields = '__all__'

class HeatmapsSerializer(serializers.ModelSerializer):
    tenant_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    camera_display_name = serializers.SerializerMethodField()

    @staticmethod
    def _get_camera(camera_id):
        return Camera.objects.filter(camera_id=camera_id).select_related('store__tenant').first()

    def get_tenant_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        if camera and camera.store and camera.store.tenant:
            return camera.store.tenant.name
        return ""

    def get_store_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        if camera and camera.store:
            return camera.store.name
        return ""

    def get_camera_display_name(self, obj):
        camera = self._get_camera(obj.camera_id)
        return camera.display_name if camera else ""

    class Meta:
        model = Heatmaps
        fields = '__all__'
