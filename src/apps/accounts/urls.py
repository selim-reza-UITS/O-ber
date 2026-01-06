from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .api.views import (
    SignUpView, 
    LoginView, 
    ForgotPasswordRequestView, 
    VerifyOTPView,
    PasswordResetConfirmView
)

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordRequestView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reset-password/', PasswordResetConfirmView.as_view(), name='reset-password'),
]