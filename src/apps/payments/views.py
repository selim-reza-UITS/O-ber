from rest_framework.views import APIView
from src.apps.riders.models import Ride
from rest_framework.response import Response
from src.apps.payments.services import process_ride_payment
from src.apps.payments.models import Transaction

class UpdateRideStatusView(APIView):
    def post(self, request, ride_id):
        new_status = request.data.get('status')
        ride = Ride.objects.get(id=ride_id, driver=request.user)
        
        ride.status = new_status
        
        if new_status == 'COMPLETED':
            # 1. Trigger Payment Logic
            intent_id, pay_status = process_ride_payment(ride)
            
            # 2. Record the Transaction
            Transaction.objects.create(
                ride=ride,
                stripe_payment_intent_id=intent_id or "",
                amount=ride.estimated_price,
                status=pay_status
            )
            
            # 3. Notify Rider via WebSocket (Live Receipt)
            # broadcast_ride_update(ride.id, {"type": "PAYMENT_COMPLETED", "amount": str(ride.estimated_price)})

        ride.save()
        return Response({"message": f"Status updated to {new_status}"})