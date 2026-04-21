import os
import sys
import django
import random
from django.core.files.base import ContentFile
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.gis.geos import Point

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src._config.settings.local')
django.setup()

# Import all models
from src.apps.accounts.models import User, RiderProfile, DriverProfile, VehicleImage
from src.apps.riders.models import Ride, RideReview, RideMessage, RideRequest
from src.apps.payments.models import Transaction, Withdrawal
from src.apps.drivers.models import DriverShift
from src.apps.dashboard.models import (
    HelpSupport, Notification, PriceConfig, Commision, 
    TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs
)
from django.contrib.auth.hashers import make_password

# Smallest possible transparent GIF (1x1 pixel)
DUMMY_IMAGE = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'

def create_mock_users():
    print("🚀 Starting comprehensive mock data generation...")

    # 1. Platform Settings (Ensure app functionality)
    print("🛠 Initializing Platform Settings...")
    for v_type in ['ECONOMY', 'XL', 'PREMIUM']:
        PriceConfig.objects.get_or_create(
            vehicle_type=v_type,
            defaults={
                'base_fare': 5.00,
                'price_per_km': 2.50,
                'price_per_minute': 0.50,
                'aruba_tax_percentage': 7.00
            }
        )
    Commision.objects.get_or_create(commision=15.00)
    
    # Initialize Static Content if empty
    if not TermsAndConditionsModel.objects.exists():
        TermsAndConditionsModel.objects.create(content="<h2>Terms and Conditions</h2><p>Mock terms content...</p>")
    if not PrivacyAndPolicyModel.objects.exists():
        PrivacyAndPolicyModel.objects.create(content="<h2>Privacy Policy</h2><p>Mock privacy content...</p>")
    if not AboutUs.objects.exists():
        AboutUs.objects.create(content="<h2>About Us</h2><p>Mock about us content...</p>")

    # 2. Create Users
    print("👤 Creating Users...")
    rider_email = "srreza1999@gmail.com"
    rider_pass = "Jvai@2025"
    rider_user, _ = User.objects.get_or_create(
        email=rider_email,
        defaults={
            'full_name': 'Somrat Rider',
            'phone_number': '+8801700000000',
            'is_rider': True,
            'is_driver': False,
            'password': make_password(rider_pass)
        }
    )
    RiderProfile.objects.get_or_create(
        user=rider_user,
        defaults={'user_photo': ContentFile(DUMMY_IMAGE, name='rider_photo.gif')}
    )

    driver_email = "somrat@gmail.com"
    driver_pass = "Somrat1234"
    driver_user, _ = User.objects.get_or_create(
        email=driver_email,
        defaults={
            'full_name': 'Somrat Driver',
            'phone_number': '+8801800000000',
            'is_rider': False,
            'is_driver': True,
            'password': make_password(driver_pass),
            'wallet_balance': 1500.00
        }
    )
    
    driver_profile, p_created = DriverProfile.objects.get_or_create(
        user=driver_user,
        defaults={
            'date_of_birth': date(1990, 1, 1),
            'gender': 'M',
            'nid_number': '1234567890',
            'driver_license_number': 'DL-123456',
            'vehicle_type': 'ECONOMY',
            'vehicle_brand': 'Toyota',
            'vehicle_model': 'Corolla',
            'vehicle_plate': 'DHK-METRO-123',
            'admin_verified': True,
            'is_active': True,
            'is_online': False,
            'ai_verified': True,
            'last_location': Point(-70.035, 12.525, srid=4326)
        }
    )
    
    if p_created:
        driver_profile.user_photo.save('driver_photo.gif', ContentFile(DUMMY_IMAGE))
        driver_profile.nid_front.save('nid_f.gif', ContentFile(DUMMY_IMAGE))
        driver_profile.nid_back.save('nid_b.gif', ContentFile(DUMMY_IMAGE))
        driver_profile.license_front.save('lic_f.gif', ContentFile(DUMMY_IMAGE))
        driver_profile.license_back.save('lic_b.gif', ContentFile(DUMMY_IMAGE))
        driver_profile.registration_photo.save('reg.gif', ContentFile(DUMMY_IMAGE))
        
        # Add multiple vehicle images
        for i in range(3):
            VehicleImage.objects.create(driver=driver_profile, image=ContentFile(DUMMY_IMAGE, name=f'car_{i}.gif'))

    # 3. Rides & History
    print("🚗 Creating Ride History, Chat & Requests...")
    locations = [
        {"p": (-70.035, 12.525), "pa": "Oranjestad", "d": (-70.015, 12.515), "da": "Airport"},
        {"p": (-70.045, 12.535), "pa": "Eagle Beach", "d": (-70.035, 12.525), "da": "Downtown"},
    ]
    
    now = timezone.now()
    for i, loc in enumerate(locations):
        ride_time = now - timedelta(days=i+1)
        ride = Ride.objects.create(
            rider=rider_user, driver=driver_user,
            pickup_location=Point(loc["p"][0], loc["p"][1], srid=4326),
            dropoff_location=Point(loc["d"][0], loc["d"][1], srid=4326),
            pickup_address=loc["pa"], dropoff_address=loc["da"],
            status='COMPLETED', estimated_price=30.00, final_price=30.00,
            payment_method='CARD'
        )
        Ride.objects.filter(id=ride.id).update(created_at=ride_time)
        Transaction.objects.create(ride=ride, amount=30.00, status='SUCCESS')
        RideReview.objects.create(ride=ride, rider=rider_user, driver=driver_user, rating=5, comment="Excellent!")
        
        # Create Chat History
        RideMessage.objects.create(ride=ride, sender=rider_user, content="I am at the entrance.")
        RideMessage.objects.create(ride=ride, sender=driver_user, content="Okay, I will be there in 2 minutes.")
        
        # Create Ride Request entries
        RideRequest.objects.create(
            rider=rider_user, driver=driver_user,
            pickup_location=Point(loc["p"][0], loc["p"][1], srid=4326),
            dropoff_location=Point(loc["d"][0], loc["d"][1], srid=4326),
            pickup_address=loc["pa"], dropoff_address=loc["da"],
            status='COMPLETED', estimated_fare=30.00
        )

    # 4. Financials
    print("💰 Creating Withdrawals & Shifts...")
    Withdrawal.objects.get_or_create(
        user=driver_user, amount=500.00,
        defaults={'destination_account': 'Bank Account XXXX-1234', 'status': 'SUCCESS'}
    )
    for i in range(3):
        start = now - timedelta(days=i, hours=5)
        DriverShift.objects.create(driver=driver_profile, start_time=start, end_time=start + timedelta(hours=4))

    # 5. Support & Notifications
    print("🔔 Creating Support Tickets & Notifications...")
    HelpSupport.objects.get_or_create(user=rider_user, message="How do I change my payment method?", defaults={'is_resolved': True})
    HelpSupport.objects.get_or_create(user=driver_user, message="My car needs an update in the profile.", defaults={'is_resolved': False})
    
    Notification.objects.create(user=rider_user, title="Welcome!", message="Welcome to O-ber! Enjoy your first ride.", is_read=True)
    Notification.objects.create(user=rider_user, title="Promo Code", message="Use RIDE20 for 20% off your next trip.", is_read=False)
    Notification.objects.create(user=driver_user, title="New Bonus", message="Complete 10 rides today to earn $50 extra.", is_read=False)

    print("✅ Full mock data generation finished successfully! (All 15+ models covered)")

if __name__ == "__main__":
    create_mock_users()
