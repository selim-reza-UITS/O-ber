from shortuuid.django_fields import ShortUUIDField
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from .managers import CustomUserManager

class User(AbstractUser):
    user_id = ShortUUIDField(
        length=6,
        max_length=6,
        alphabet="0123456789",
        primary_key=True,
    )
    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=255)
    
    is_rider = models.BooleanField(default=True)
    is_driver = models.BooleanField(default=False)
    
    # Stripe
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number']

    objects = CustomUserManager()

    def __str__(self):
        return f"{self.full_name} ({self.email})"

class RiderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='rider_profile')
    user_photo = models.ImageField(upload_to='rider/photos/')

class DriverProfile(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    user_photo = models.ImageField(upload_to='drivers/photos/')
    # Personal Info
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Verification Documents
    nid_front = models.ImageField(upload_to='drivers/documents/nid/')
    nid_back = models.ImageField(upload_to='drivers/documents/nid/')
    license_front = models.ImageField(upload_to='drivers/documents/license/')
    license_back = models.ImageField(upload_to='drivers/documents/license/')
    
    # Vehicle Details
    vehicle_type = models.CharField(max_length=50)
    vehicle_brand = models.CharField(max_length=50)
    vehicle_model = models.CharField(max_length=50)
    vehicle_plate = models.CharField(max_length=20, unique=True, null=True)
    registration_photo = models.ImageField(upload_to='drivers/documents/vehicle/')
    
    # Status
    ai_verified = models.BooleanField(default=False)
    admin_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_online = models.BooleanField(default=False)
    # PostGIS field for real-time location
    last_location = models.PointField(null=True, blank=True, srid=4326)

class VehicleImage(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='vehicle_photos')
    image = models.ImageField(upload_to='drivers/vehicles/multiple/')
    
    
    
    
    
#

class PendingDriverUpdate(models.Model):
    driver = models.OneToOneField(DriverProfile, on_delete=models.CASCADE, related_name='pending_update')
    full_name = models.CharField(max_length=255, null=True, blank=True)
    user_photo = models.ImageField(upload_to='drivers/pending/photos/', null=True, blank=True)
    gender = models.CharField(max_length=1, choices=DriverProfile.GENDER_CHOICES, null=True, blank=True)
    nid_front = models.ImageField(upload_to='drivers/pending/nid/', null=True, blank=True)
    nid_back = models.ImageField(upload_to='drivers/pending/nid/', null=True, blank=True)
    license_front = models.ImageField(upload_to='drivers/pending/license/', null=True, blank=True)
    license_back = models.ImageField(upload_to='drivers/pending/license/', null=True, blank=True)
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)
    vehicle_brand = models.CharField(max_length=50, null=True, blank=True)
    vehicle_model = models.CharField(max_length=50, null=True, blank=True)
    registration_photo = models.ImageField(upload_to='drivers/pending/vehicle/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pending Update for {self.driver.user.full_name}"