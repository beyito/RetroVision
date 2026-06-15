from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SecurityAlert, Telemetria_Afluencia, Heatmaps
from .serializers import SecurityAlertSerializer, TelemetriaAfluenciaSerializer, HeatmapsSerializer

class SecurityAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows security alerts to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = SecurityAlert.objects.all().order_by('-timestamp')
    serializer_class = SecurityAlertSerializer

class TelemetriaAfluenciaViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows commercial telemetry to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Telemetria_Afluencia.objects.all().order_by('-timestamp')
    serializer_class = TelemetriaAfluenciaSerializer

class HeatmapsViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows visual heatmaps to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = Heatmaps.objects.all().order_by('-timestamp')
    serializer_class = HeatmapsSerializer
