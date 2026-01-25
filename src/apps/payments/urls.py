from django.urls import path
from . import views

urlpatterns = [
    path('config/', views.StripeConfigView.as_view(), name='stripe-config'),
    path('payment-sheet/', views.PaymentSheetView.as_view(), name='payment-sheet'),
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
]
