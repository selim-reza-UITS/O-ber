from django.contrib.gis.geos import Point
from rest_framework.views import APIView
from rest_framework import permissions,status
from rest_framework.response import Response
from django.contrib.gis.measure import D,Distance
from src.apps.riders.models import Ride
from src.apps.riders.serializers import RideSerializer
from src.apps.drivers.utils import broadcast_ride_update
from src.apps.riders.tasks import task_broadcast_location
from django.db import transaction

from src.apps.accounts.permissions import IsDriver, IsVerifiedDriver


class UpdateDriverLocationView(APIView):
    # Security: Ensure only authenticated DRIVERS can call this
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lat = request.data.get('lat')
        lng = request.data.get('lng')
        
        if lat is None or lng is None:
            return Response({"error": "Coordinates (lat, lng) required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Update Driver's DB Profile
            driver_profile = request.user.driver_profile
            driver_profile.last_location = Point(float(lng), float(lat), srid=4326)
            driver_profile.is_online = True
            driver_profile.save()

            # 2. WebSocket Push (Hybrid Logic)
            # Find if this driver is currently in an active trip
            active_ride = Ride.objects.filter(
                driver=request.user, 
                status__in=['ACCEPTED', 'ARRIVED', 'STARTED']
            ).first()
            
            if active_ride:
                # We broadcast the update so the Rider's map shows the car moving
                broadcast_ride_update(active_ride.id, {
                    "type": "LOCATION_UPDATE",
                    "lat": float(lat),
                    "lng": float(lng),
                    "status": active_ride.status,
                    "driver_id": request.user.user_id
                })
                task_broadcast_location.delay(
                    active_ride.id, 
                    float(lat), 
                    float(lng), 
                    active_ride.status
                )

            return Response({"message": "Location updated and broadcasted"})

        except AttributeError:
            return Response({"error": "User does not have a driver profile"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AvailableRidesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        driver_profile = request.user.driver_profile
        if not driver_profile.last_location:
            return Response({"error": "Update your location first"}, status=400)

        # Find rides within 5km of the driver's current position
        rides = Ride.objects.filter(
            status='SEARCHING',
            pickup_location__distance_lte=(driver_profile.last_location, D(km=5))
        ).annotate(
            distance=Distance('pickup_location', driver_profile.last_location)
        ).order_by('distance')

        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)
    

class AcceptRideView(APIView):
    permission_classes = [IsVerifiedDriver]

    def post(self, request, ride_id):
        with transaction.atomic():
            # Select_for_update locks the row so no other driver can edit it right now
            try:
                ride = Ride.objects.select_for_update().get(id=ride_id)
            except Ride.DoesNotExist:
                return Response({"error": "Ride not found"}, status=404)

            if ride.status != 'SEARCHING':
                return Response({"error": "Ride already taken or cancelled"}, status=400)

            # Assign driver and change status
            ride.driver = request.user
            ride.status = 'ACCEPTED'
            ride.save()

            return Response({
                "message": "Ride accepted successfully",
                "ride_id": ride.id
            })
        
