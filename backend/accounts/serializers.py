from rest_framework import serializers

from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
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
            'store',
            'store_name',
            'is_staff',
            'is_superuser',
        )
