"""URL configuration for RetroVision Core."""

from django.contrib import admin
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/accounts/", include("accounts.urls")),
    path("api/", include("alerts_api.urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
