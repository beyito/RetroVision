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
    class Meta:
        model = SecurityAlert
        fields = '__all__'

class TelemetriaAfluenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Telemetria_Afluencia
        fields = '__all__'

class HeatmapsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Heatmaps
        fields = '__all__'
