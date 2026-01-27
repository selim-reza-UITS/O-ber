import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_ephemeral_key(customer_id, api_version='2023-10-16'):
    try:
        key = stripe.EphemeralKey.create(
            customer=customer_id,
            stripe_version=api_version
        )
        return key
    except Exception as e:
        print(f"Error creating ephemeral key: {e}")
        return None

def create_payment_intent(amount, currency, customer_id, payment_method_id=None):
    try:
        amount_cents = int(float(amount) * 100)
        
        intent_params = {
            'amount': amount_cents,
            'currency': currency,
            'customer': customer_id,
            'automatic_payment_methods': {'enabled': True},
        }

        if payment_method_id:
            intent_params['payment_method'] = payment_method_id
            intent_params['confirm'] = True
            intent_params['return_url'] = 'https://ober-aruba.com/payment-complete' # In a real Flutter app, this might be a deep link

        intent = stripe.PaymentIntent.create(**intent_params)
        return intent
    except Exception as e:
        print(f"Error creating payment intent: {e}")
        return None

import logging
logger = logging.getLogger(__name__)

def process_ride_payment(ride):
    """
    Handles payment processing via Stripe Checkout Session.
    Returns: session_id, session_url, status
    """
    try:
        amount_in_cents = int(ride.estimated_price * 100)
        customer_id = ride.rider.stripe_customer_id
        
        logger.info(f"Processing payment for Ride {ride.id}. Amount: {amount_in_cents}, Customer: {customer_id}")
        
        # Base URL for redirects (Deep links or Web pages)
        # In production, these should be your app's deep links (e.g. ober://payment-success)
        base_url = getattr(settings, 'FRONTEND_URL', 'http://10.10.13.22:9500')

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Ride with {ride.driver.full_name}",
                        'description': f"Trip from {ride.pickup_address} to {ride.dropoff_address}",
                    },
                    'unit_amount': amount_in_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{base_url}/api/v1/rider/payment/success/?ride_id={ride.id}",
            cancel_url=f"{base_url}/api/v1/rider/payment/cancel/?ride_id={ride.id}",
            customer=customer_id if customer_id else None,
            customer_email=ride.rider.email if not customer_id else None,
            client_reference_id=str(ride.id),
            metadata={
                'ride_id': str(ride.id),
                'rider_id': str(ride.rider.user_id)
            }
        )
        
        logger.info(f"Stripe Session Created: {session.id}, URL: {session.url}")
        
        # Status is PENDING until webhook confirms it
        return session.id, session.url, "PENDING"
        
    except Exception as e:
        logger.error(f"Stripe Checkout Error for Ride {ride.id}: {str(e)}", exc_info=True)
        return None, None, "FAILED"