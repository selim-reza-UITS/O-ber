from django.contrib.gis.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Ride(models.Model):
    STATUS_CHOICES = [
        ('SEARCHING', 'Searching for Driver'),
        ('ACCEPTED', 'Driver Accepted'),
        ('ARRIVED', 'Driver Arrived'),
        ('STARTED', 'Trip Started'),
        ('COMPLETED', 'Trip Completed'),
        ('CANCELED', 'Trip Canceled'),
    ]

    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rides_as_rider')
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rides_as_driver')
    
    # Coordinates (PostGIS)
    pickup_location = models.PointField()
    dropoff_location = models.PointField()
    pickup_address = models.TextField()
    dropoff_address = models.TextField()
    requested_vehicle_type = models.CharField(
        max_length=20, 
        choices=[('ECONOMY', 'Economy'), ('XL', 'Van/XL'), ('PREMIUM', 'Premium')],
        default='ECONOMY'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SEARCHING')
    
    # Pricing
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Cancellation
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_rides')
    cancellation_reason = models.TextField(null=True, blank=True)
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)


class RideRequest(models.Model):
    STATUS = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('ARRIVED', 'Arrived'),
        ('PICKED_UP', 'Picked Up'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ride_requests')
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='trips')
    
    pickup_location = models.PointField(srid=4326)
    dropoff_location = models.PointField(srid=4326)
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

class RideMessage(models.Model):
    ride = models.ForeignKey('riders.Ride', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg from {self.sender.full_name} on Ride {self.ride.id}"

class RideReview(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name='review')
    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_written')
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    rating = models.PositiveIntegerField(default=5)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} stars for Ride {self.ride.id}"