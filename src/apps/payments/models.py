# src/apps/payments/models.py
from django.db import models
from src.apps.riders.models import Ride

class Transaction(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')]
    
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='transaction')
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_payment_method_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Ride {self.ride.id} - {self.status}"