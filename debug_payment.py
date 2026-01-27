import os
import django
import sys

# Add project root to path
sys.path.append('/home/reza/Code/Ober_temp')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src._config.settings.base')
django.setup()

from src.apps.riders.models import Ride
from src.apps.payments.services import process_ride_payment
from django.conf import settings

print(f"Stripe Key Configured: {'Yes' if getattr(settings, 'STRIPE_SECRET_KEY', None) else 'No'}")
print(f"Stripe Webhook Secret: {'Yes' if getattr(settings, 'STRIPE_WEBHOOK_SECRET', None) else 'No'}")

# Try to get the latest completed ride or any ride to test
ride = Ride.objects.last()

if not ride:
    print("No rides found to test.")
else:
    print(f"Testing with Ride ID: {ride.id}")
    print(f"Rider: {ride.rider.email}, Stripe ID: {ride.rider.stripe_customer_id}")
    
    if not ride.rider.stripe_customer_id:
        print("ERROR: Rider has no stripe_customer_id")
    else:
        print("Attempting process_ride_payment...")
        try:
            session_id, session_url, status = process_ride_payment(ride)
            print(f"Result - Session ID: {session_id}")
            print(f"Result - URL: {session_url}")
            print(f"Result - Status: {status}")
        except Exception as e:
            print(f"Exception caught during test: {e}")
