from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SecurityAlertViewSet, TelemetriaAfluenciaViewSet, HeatmapsViewSet

router = DefaultRouter()
router.register(r'alerts', SecurityAlertViewSet, basename='securityalert')
router.register(r'telemetry', TelemetriaAfluenciaViewSet, basename='telemetry')
router.register(r'heatmaps', HeatmapsViewSet, basename='heatmap')

urlpatterns = [
    path('', include(router.urls)),
]
