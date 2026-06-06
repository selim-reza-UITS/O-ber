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
        from django.utils import timezone

        new_status = request.data.get('status')
        allowed = ('ARRIVED', 'STARTED', 'COMPLETED')

        if new_status not in allowed:
            return Response(
                {"error": f"Invalid status. Allowed: {', '.join(allowed)}"},
                status=400
            )

        try:
            ride = Ride.objects.get(id=ride_id, driver=request.user)
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found or you are not the driver"}, status=404)

        ride.status = new_status

        if new_status == 'ARRIVED':
            # Driver has physically reached the rider's pickup point
            ride.arrival_time = timezone.now()
            broadcast_ride_update(ride.id, {
                "type": "DRIVER_ARRIVED",
                "status": "ARRIVED",
            })

        elif new_status == 'STARTED':
            ride.start_time = timezone.now()
            broadcast_ride_update(ride.id, {
                "type": "TRIP_STARTED",
                "status": "STARTED",
            })

        elif new_status == 'COMPLETED':
            ride.drop_off_time = timezone.now()
            broadcast_ride_update(ride.id, {
                "type": "TRIP_COMPLETED",
                "final_fare": str(ride.estimated_price),
            })

        ride.save()
        return Response({"message": "Status updated", "status": new_status})


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


class RidePaymentView(APIView):
    """
    POST /payment/ride/<ride_id>/pay/
    Body: { "payment_method": "CASH" | "DIGITAL" }

    CASH   — records the transaction as SUCCESS immediately, no Stripe call.
    DIGITAL — creates a Stripe Checkout session and returns the payment_url.
    
    If payment already exists:
    - CASH + SUCCESS: error (already paid)
    - DIGITAL + PENDING: regenerate payment URL (session may have expired)
    - DIGITAL + SUCCESS: error (already paid)
    - DIGITAL + FAILED: allow retry, create new session
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        try:
            ride = Ride.objects.get(id=ride_id, rider=request.user)
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found"}, status=404)

        if ride.status != 'COMPLETED':
            return Response({"error": "Ride is not completed yet"}, status=400)

        payment_method = request.data.get('payment_method', '').upper()
        if payment_method not in ('CASH', 'DIGITAL'):
            return Response({"error": "payment_method must be CASH or DIGITAL"}, status=400)

        # Check if payment already exists
        existing_transaction = None
        if hasattr(ride, 'transaction'):
            existing_transaction = ride.transaction

        if existing_transaction:
            # If already SUCCESS, cannot pay again (regardless of method)
            if existing_transaction.status == 'SUCCESS':
                # Infer payment method: empty stripe_payment_intent_id = CASH, has value = DIGITAL
                inferred_method = 'DIGITAL' if existing_transaction.stripe_payment_intent_id else 'CASH'
                return Response({
                    "error": "Payment already completed for this ride",
                    "payment_method": inferred_method,
                    "status": "SUCCESS"
                }, status=400)
            
            # If switching TO CASH (from PENDING/FAILED DIGITAL), delete old transaction and create CASH
            if payment_method == 'CASH' and existing_transaction.status in ['PENDING', 'FAILED']:
                existing_transaction.delete()
                Transaction.objects.create(
                    ride=ride,
                    amount=ride.estimated_price,
                    status='SUCCESS',
                    stripe_payment_intent_id='',
                )
                return Response({
                    "message": "Payment method switched to CASH",
                    "payment_method": "CASH",
                    "status": "SUCCESS"
                })
            
            # If DIGITAL and PENDING, regenerate payment URL (session may have expired)
            if existing_transaction.status == 'PENDING' and payment_method == 'DIGITAL':
                session_id, session_url, pay_status = process_ride_payment(ride)
                existing_transaction.stripe_payment_intent_id = session_id if session_id else ''
                existing_transaction.save()
                return Response({
                    "message": "Payment URL regenerated",
                    "payment_method": "DIGITAL",
                    "payment_url": session_url,
                    "payment_status": pay_status,
                })
            
            # If DIGITAL and FAILED, allow retry
            if existing_transaction.status == 'FAILED' and payment_method == 'DIGITAL':
                session_id, session_url, pay_status = process_ride_payment(ride)
                existing_transaction.stripe_payment_intent_id = session_id if session_id else ''
                existing_transaction.status = pay_status
                existing_transaction.save()
                return Response({
                    "message": "Payment retry link generated",
                    "payment_method": "DIGITAL",
                    "payment_url": session_url,
                    "payment_status": pay_status,
                })

        # No existing transaction, create new one
        if payment_method == 'CASH':
            Transaction.objects.create(
                ride=ride,
                amount=ride.estimated_price,
                status='SUCCESS',
                stripe_payment_intent_id='',
            )
            broadcast_ride_update(ride.id, {
                "type": "PAYMENT_SUCCESS",
                "amount": str(ride.estimated_price),
                "payment_method": "CASH",
            })
            return Response({"message": "Cash payment recorded", "payment_method": "CASH"})

        # DIGITAL — Stripe checkout
        session_id, session_url, pay_status = process_ride_payment(ride)
        Transaction.objects.create(
            ride=ride,
            amount=ride.estimated_price,
            status=pay_status,
            stripe_payment_intent_id=session_id if session_id else '',
        )
        return Response({
            "payment_method": "DIGITAL",
            "payment_url": session_url,
            "payment_status": pay_status,
        })