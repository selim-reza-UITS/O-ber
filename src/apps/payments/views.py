from rest_framework.views import APIView
from src.apps.riders.models import Ride
from rest_framework.response import Response
from src.apps.payments.services import process_ride_payment
from src.apps.payments.models import Transaction
from drivers.utils import broadcast_ride_update
class UpdateRideStatusView(APIView):

    def post(self, request, ride_id):
        new_status = request.data.get('status') # 'ARRIVED', 'STARTED', 'COMPLETED'
        ride = Ride.objects.get(id=ride_id, driver=request.user)
        ride.status = new_status
        
        if new_status == 'COMPLETED':
            # 1. Process Stripe
            intent_id, pay_status = process_ride_payment(ride)
            # 2. Save Transaction
            Transaction.objects.create(ride=ride, amount=ride.estimated_price, status=pay_status)
            # 3. WS Signal: Tell rider to show Review Screen
            broadcast_ride_update(ride.id, {
                "type": "TRIP_COMPLETED",
                "final_fare": str(ride.estimated_price),
                "payment_status": pay_status
            })
        else:
            # Notify for Arrived/Started
            broadcast_ride_update(ride.id, {
                "type": "STATUS_UPDATE",
                "status": new_status
            })

        ride.save()
        return Response({"message": "Status updated"})