from rest_framework import serializers
from .models import SecurityAlert, Telemetria_Afluencia, Heatmaps

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
