from django.urls import path

from .views import CurrentUserProfileView, UserRegistrationView


urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="current-user-profile"),
    path("register/", UserRegistrationView.as_view(), name="user-registration"),
]
