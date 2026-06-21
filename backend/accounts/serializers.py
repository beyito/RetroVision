from rest_framework import serializers

from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    tenant_max_cameras = serializers.IntegerField(source='tenant.max_cameras', read_only=True)
    tenant_is_active = serializers.BooleanField(source='tenant.is_active', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'role',
            'tenant',
            'tenant_name',
            'tenant_max_cameras',
            'tenant_is_active',
            'store',
            'store_name',
            'is_staff',
            'is_superuser',
        )


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    tenant_name = serializers.CharField(max_length=128)
    plan = serializers.ChoiceField(choices=['basico', 'estandar', 'premium'], default='basico')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está registrado.")
        return value

    def validate_tenant_name(self, value):
        from alerts_api.models import Tenant
        if Tenant.objects.filter(name=value).exists():
            raise serializers.ValidationError("Este nombre de empresa ya está registrado.")
        return value
