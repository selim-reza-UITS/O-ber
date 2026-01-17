from django.urls import path
from src.apps.accounts.api.views_driver import DriverOnboardingView,DriverSelfieVerifyView
urlpatterns = [
    path('driver-onboarding/', DriverOnboardingView.as_view(), name='driver-onboarding'),
    path('driver-selfie-verify/', DriverSelfieVerifyView.as_view(), name='driver-selfie-verify'),
        
]