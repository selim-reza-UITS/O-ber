# src/apps/payments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from src.apps.riders.models import Ride

User = get_user_model()

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


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REVERSED', 'Reversed')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    destination_account = models.CharField(max_length=100)
    transfer_group = models.CharField(max_length=100, blank=True)
    stripe_transfer_id = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Withdrawal of {self.amount} {self.currency} by {self.user.full_name} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']