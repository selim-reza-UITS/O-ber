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

def process_ride_payment(ride, payment_method_id=None):
    """
    Handles payment processing via Stripe.
    """
    try:
        amount_in_cents = int(ride.estimated_price * 100)
        customer_id = ride.rider.stripe_customer_id

        if not customer_id:
             # Fallback: Create customer if missing (should exist via signal)
             return None, "FAILED_NO_CUSTOMER"

        # Create the charge
        # If we have a saved payment method, try to charge it immediately
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency="usd", # Or 'awg'
            description=f"Ride {ride.id} in Aruba",
            customer=customer_id,
            payment_method=payment_method_id if payment_method_id else None,
            confirm=True if payment_method_id else False, # Only confirm if we passed a method
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            off_session=True if payment_method_id else False,
        )
        
        status = "SUCCESS" if intent.status == 'succeeded' else "PENDING"
        return intent.id, status
        
    except stripe.error.CardError as e:
        print(f"Stripe Card Error: {e}")
        return None, "FAILED_CARD_ERROR"
    except Exception as e:
        print(f"Stripe Error: {str(e)}")
        return None, "FAILED"