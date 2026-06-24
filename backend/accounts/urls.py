from django.urls import path

from .views import CurrentUserProfileView, CreateCheckoutSessionView, UserRegistrationView, CheckoutCompleteView


urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="current-user-profile"),
    path("create-checkout-session/", CreateCheckoutSessionView.as_view(), name="create-checkout-session"),
    path("register/", UserRegistrationView.as_view(), name="user-registration"),
    path("checkout-complete/", CheckoutCompleteView.as_view(), name="checkout-complete"),
]
