from django.urls import path

from .views import CurrentUserProfileView


urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="current-user-profile"),
]
