from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import stripe
from .models import User

stripe.api_key = settings.STRIPE_SECRET_KEY

@receiver(post_save, sender=User)
def create_stripe_customer(sender, instance, created, **kwargs):
    if created and not instance.stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=instance.email,
                name=instance.full_name,
                phone=instance.phone_number,
                metadata={
                    "user_id": instance.user_id,
                    "platform": "O-ber Aruba"
                }
            )
            instance.stripe_customer_id = customer.id
            instance.save()
        except Exception as e:
            # In production, log this error
            print(f"Error creating Stripe customer: {e}")
