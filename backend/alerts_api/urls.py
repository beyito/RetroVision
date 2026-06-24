from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantViewSet,
    StoreViewSet,
    EdgeNodeViewSet,
    CameraViewSet,
    SecurityAlertViewSet,
    TelemetriaAfluenciaViewSet,
    HeatmapsViewSet,
    DynamicReportView,
    PredictiveAnalysisView,
)

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'edge-nodes', EdgeNodeViewSet, basename='edgenode')
router.register(r'cameras', CameraViewSet, basename='camera')
router.register(r'alerts', SecurityAlertViewSet, basename='securityalert')
router.register(r'telemetry', TelemetriaAfluenciaViewSet, basename='telemetry')
router.register(r'heatmaps', HeatmapsViewSet, basename='heatmap')

urlpatterns = [
    path('telemetry/predictive/', PredictiveAnalysisView.as_view(), name='telemetry-predictive'),
    path('', include(router.urls)),
    path('reports/dynamic/', DynamicReportView.as_view(), name='dynamic-report'),
]



