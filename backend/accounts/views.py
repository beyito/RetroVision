from django.db import transaction
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alerts_api.models import Tenant
from .models import User
from .serializers import UserProfileSerializer, UserRegistrationSerializer


class CurrentUserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class UserRegistrationView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Mapeo de límites de cámaras por plan
        plan_limits = {
            'basico': 2,
            'estandar': 5,
            'premium': 10
        }
        max_cameras = plan_limits.get(data['plan'], 5)
        
        try:
            with transaction.atomic():
                # Crear Tenant transaccionalmente
                tenant = Tenant.objects.create(
                    name=data['tenant_name'],
                    slug=slugify(data['tenant_name']),
                    max_cameras=max_cameras,
                    is_active=True
                )
                
                # Crear User vinculado al Tenant con rol ADMIN_EMPRESA
                user = User.objects.create_user(
                    username=data['username'],
                    email=data.get('email', ''),
                    password=data['password'],
                    role=User.ADMIN_EMPRESA,
                    tenant=tenant
                )
        except Exception as exc:
            return Response(
                {"detail": f"Error al procesar el registro: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        return Response({
            "message": "Registro completado con éxito.",
            "user": {
                "id": user.id,
                "username": user.username,
                "tenant_name": tenant.name,
                "role": user.role
            }
        }, status=status.HTTP_201_CREATED)
