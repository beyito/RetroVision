from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SecurityAlertViewSet

router = DefaultRouter()
router.register(r'alerts', SecurityAlertViewSet, basename='securityalert')

urlpatterns = [
    path('', include(router.urls)),
]
