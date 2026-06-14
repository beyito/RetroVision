from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SecurityAlert
from .serializers import SecurityAlertSerializer

class SecurityAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows security alerts to be viewed."""
    permission_classes = [IsAuthenticated]
    queryset = SecurityAlert.objects.all().order_by('-timestamp')
    serializer_class = SecurityAlertSerializer
