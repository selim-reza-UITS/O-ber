from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point
from decimal import Decimal
from django.shortcuts import get_object_or_404

from .models import Ride, RideReview
from .serializers import RideSerializer
from src.apps.accounts.models import DriverProfile
from src.apps.accounts.permissions import IsRider
from .utils import calculate_dynamic_fare
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from src.apps.drivers.utils import broadcast_ride_update


class FareEstimateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pickup_lat = request.data.get('pickup_lat')
        pickup_lng = request.data.get('pickup_lng')
        dropoff_lat = request.data.get('dropoff_lat')
        dropoff_lng = request.data.get('dropoff_lng')
        pickup_address = request.data.get('pickup_address', '')
        dropoff_address = request.data.get('dropoff_address', '')

        if not all([pickup_lat, pickup_lng, dropoff_lat, dropoff_lng]):
            return Response({"error": "All coordinates are required"}, status=400)

        pickup_point = Point(float(pickup_lng), float(pickup_lat), srid=4326)
        dropoff_point = Point(float(dropoff_lng), float(dropoff_lat), srid=4326)
        distance_km = round(pickup_point.distance(dropoff_point) * 111.32, 2)

        vehicle_types = ['ECONOMY', 'XL', 'PREMIUM']
        estimates = []

        for v_type in vehicle_types:
            price = calculate_dynamic_fare(pickup_point, dropoff_point, v_type)
            available_drivers = DriverProfile.objects.filter(
                is_active=True,
                is_online=True,
                vehicle_type=v_type,
                last_location__distance_lte=(pickup_point, D(km=10))
            ).count()

            estimates.append({
                "vehicle_type": v_type,
                "estimated_price": str(price),
                "currency": "AWG",
                "available_drivers": available_drivers,
                "eta_minutes": 5 if available_drivers > 0 else None
            })

        return Response({
            "pickup_address": pickup_address,
            "dropoff_address": dropoff_address,
            "distance_km": distance_km,
            "estimates": estimates
        })


class CreateRideView(APIView):
    permission_classes = [IsRider]

    def post(self, request):
        serializer = RideSerializer(data=request.data)
        if serializer.is_valid():
            v_type = request.data.get('requested_vehicle_type', 'ECONOMY')
            p_lat = serializer.validated_data['pickup_lat']
            p_lng = serializer.validated_data['pickup_lng']
            d_lat = serializer.validated_data['dropoff_lat']
            d_lng = serializer.validated_data['dropoff_lng']
            
            pickup_p = Point(p_lng, p_lat, srid=4326)
            dropoff_p = Point(d_lng, d_lat, srid=4326)
            estimated_price = calculate_dynamic_fare(pickup_p, dropoff_p, v_type)

            ride = serializer.save(
                rider=request.user,
                requested_vehicle_type=v_type,
                estimated_price=estimated_price,
                status='SEARCHING'
            )
            
            nearby_drivers = DriverProfile.objects.filter(
                is_active=True,
                is_online=True,
                last_location__distance_lte=(ride.pickup_location, D(km=5))
            ).annotate(
                distance=Distance('last_location', ride.pickup_location)
            ).order_by('distance')

            channel_layer = get_channel_layer()
            ride_data = RideSerializer(ride).data
            
            async_to_sync(channel_layer.group_send)(
                "drivers_discovery",
                {
                    "type": "new_ride_available",
                    "data": {
                        "event": "NEW_RIDE_AVAILABLE",
                        "ride": ride_data,
                    }
                }
            )

            response_data = ride_data
            response_data['nearby_drivers_count'] = nearby_drivers.count()
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RideHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_driver:
            rides = Ride.objects.filter(driver=request.user).order_by('-created_at')
        else:
            rides = Ride.objects.filter(rider=request.user).order_by('-created_at')
        
        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)


class RideDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)
        if ride.rider != request.user and ride.driver != request.user:
            return Response({"error": "Not authorized"}, status=403)
        return Response(RideSerializer(ride).data)


class CancelRideView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id)
        
        if ride.rider != request.user and ride.driver != request.user:
            return Response({"error": "Not authorized"}, status=403)
             
        if ride.status in ['COMPLETED', 'CANCELED']:
            return Response({"error": "Cannot cancel completed or already canceled ride"}, status=400)

        ride.status = 'CANCELED'
        ride.cancelled_by = request.user
        ride.cancellation_reason = request.data.get('reason', 'Client cancelled')
        
        if ride.status in ['ARRIVED', 'STARTED']:
            ride.cancellation_fee = Decimal('5.00')
        
        ride.save()
        
        broadcast_ride_update(ride.id, {
            "type": "RIDE_CANCELLED",
            "cancelled_by": request.user.full_name,
            "reason": ride.cancellation_reason
        })
        
        return Response({"message": "Ride cancelled", "fee": ride.cancellation_fee})


class RideReviewView(APIView):
    permission_classes = [IsRider]

    def post(self, request, ride_id):
        ride = get_object_or_404(Ride, id=ride_id, rider=request.user)
        
        if ride.status != 'COMPLETED':
            return Response({"error": "Ride not completed"}, status=400)
             
        if hasattr(ride, 'review'):
            return Response({"error": "Already reviewed"}, status=400)
             
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        
        RideReview.objects.create(
            ride=ride,
            rider=request.user,
            driver=ride.driver,
            rating=rating,
            comment=comment
        )
        
        return Response({"message": "Review submitted"})