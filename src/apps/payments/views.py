import stripe
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from src.apps.riders.models import Ride
from src.apps.payments.services import process_ride_payment, create_stripe_ephemeral_key, create_payment_intent
from src.apps.payments.models import Transaction
from src.apps.drivers.utils import broadcast_ride_update


class StripeConfigView(APIView):
    def get(self, request):
        return Response({
            'publishableKey': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', 'pk_test_placeholder')
        })


class PaymentSheetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        customer_id = request.user.stripe_customer_id
        if not customer_id:
            return Response({"error": "No Stripe customer found for user"}, status=400)

        ephemeral_key = create_stripe_ephemeral_key(customer_id)
        if not ephemeral_key:
            return Response({"error": "Could not create ephemeral key"}, status=500)
        
        amount = request.data.get('amount')
        
        if amount:
            intent = create_payment_intent(amount, 'usd', customer_id)
            client_secret = intent.client_secret
        else:
            setup_intent = stripe.SetupIntent.create(customer=customer_id)
            client_secret = setup_intent.client_secret

        return Response({
            'paymentIntent': client_secret,
            'ephemeralKey': ephemeral_key.secret,
            'customer': customer_id,
            'publishableKey': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', 'pk_test_placeholder')
        })


class UpdateRideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        new_status = request.data.get('status')
        
        try:
            ride = Ride.objects.get(id=ride_id, driver=request.user)
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found or you are not the driver"}, status=404)

        ride.status = new_status
        
        if new_status == 'COMPLETED':
            session_id, session_url, pay_status = process_ride_payment(ride)
            
            Transaction.objects.create(
                ride=ride, 
                amount=ride.estimated_price, 
                status=pay_status,
                stripe_payment_intent_id=session_id if session_id else '' # Using session_id as the ref for now
            )
            
            broadcast_ride_update(ride.id, {
                "type": "TRIP_COMPLETED",
                "final_fare": str(ride.estimated_price),
                "payment_status": pay_status,
                "payment_url": session_url
            })
        else:
            broadcast_ride_update(ride.id, {
                "type": "STATUS_UPDATE",
                "status": new_status
            })

        ride.save()
        return Response({"message": "Status updated"})


class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=400)

        if event['type'] == 'checkout.session.completed':
            self.handle_checkout_success(event['data']['object'])
        elif event['type'] == 'payment_intent.succeeded':
            self.handle_payment_success(event['data']['object'])
        elif event['type'] == 'payment_intent.payment_failed':
            self.handle_payment_failure(event['data']['object'])

        return Response(status=200)

    def handle_checkout_success(self, session):
        # We stored session_id in stripe_payment_intent_id field
        transaction = Transaction.objects.filter(stripe_payment_intent_id=session['id']).first()
        if transaction:
            transaction.status = 'SUCCESS'
            transaction.save()
            
            if transaction.ride:
                broadcast_ride_update(transaction.ride.id, {
                    "type": "PAYMENT_SUCCESS",
                    "amount": str(transaction.amount)
                })

    def handle_payment_success(self, intent):
        transaction = Transaction.objects.filter(stripe_payment_intent_id=intent['id']).first()
        if transaction:
            transaction.status = 'SUCCESS'
            transaction.save()
            
            if transaction.ride:
                broadcast_ride_update(transaction.ride.id, {
                    "type": "PAYMENT_SUCCESS",
                    "amount": str(transaction.amount)
                })

    def handle_payment_failure(self, intent):
        transaction = Transaction.objects.filter(stripe_payment_intent_id=intent['id']).first()
        if transaction:
            transaction.status = 'FAILED'
            transaction.save()
            
            if transaction.ride:
                broadcast_ride_update(transaction.ride.id, {
                    "type": "PAYMENT_FAILED",
                    "error": intent.get('last_payment_error', {}).get('message', 'Unknown error')
                })