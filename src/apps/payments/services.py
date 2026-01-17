import stripe

def process_ride_payment(ride):
    """
    In a real app, you'd use the Rider's saved 'Customer ID' and 'Payment Method'.
    For a 5-day MVP/Demo, we will create a 'Payment Intent'.
    """
    try:
        # Stripe expects amounts in CENTS (so $15.00 becomes 1500)
        amount_in_cents = int(ride.estimated_price * 100)

        # Create the charge
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency="usd", # Or 'awg' if supported in your Stripe region
            description=f"Ride {ride.id} in Aruba",
            # In a real app, add: customer=ride.rider.stripe_customer_id
            payment_method="pm_card_visa", # Dummy card for testing
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        return intent.id, "SUCCESS"
    except Exception as e:
        print(f"Stripe Error: {str(e)}")
        return None, "FAILED"