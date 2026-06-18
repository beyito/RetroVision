from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ADMIN_SOFTWARE = 'ADMIN_SOFTWARE'
    ADMIN_EMPRESA = 'ADMIN_EMPRESA'
    SEGURIDAD = 'SEGURIDAD'
    
    ROLE_CHOICES = [
        (ADMIN_SOFTWARE, 'Administrador de Software'),
        (ADMIN_EMPRESA, 'Administrador de Empresa'),
        (SEGURIDAD, 'Personal de Seguridad'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=SEGURIDAD
    )
    tenant = models.ForeignKey(
        'alerts_api.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    store = models.ForeignKey(
        'alerts_api.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
