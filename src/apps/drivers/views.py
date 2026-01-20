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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from src.apps.accounts.models import DriverProfile
from .serializers import DriverDashboardSerializer
from .models import DriverShift
from django.utils import timezone

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
        





class DriverProfileDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver profile not found"}, status=404)

        serializer = DriverDashboardSerializer(profile)
        
        response_data = {
            "full_name": request.user.full_name,
            "email": request.user.email,
            "phone": request.user.phone_number,
            "stats": serializer.data
        }
        
        return Response(response_data)
    


class DriverToggleOnlineView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # 1. Ensure the user has a driver profile
        try:
            profile = user.driver_profile
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Safety Check: Only verified drivers can go online
        if not profile.admin_verified:
            return Response({
                "error": "Your account is pending admin approval. You cannot go online yet."
            }, status=status.HTTP_403_FORBIDDEN)

        # 3. Toggle Logic
        profile.is_online = not profile.is_online
        
        if profile.is_online:
            # Logic: Start a new shift
            # We use update_or_create/last check to prevent double shifts if the app crashed
            DriverShift.objects.create(driver=profile, start_time=timezone.now())
            message = "You are now Online and searching for rides."
        else:
            # Logic: End the current open shift
            current_shift = DriverShift.objects.filter(driver=profile, end_time__isnull=True).last()
            if current_shift:
                current_shift.end_time = timezone.now()
                current_shift.save()
            message = "You are now Offline."

        profile.save()

        return Response({
            "is_online": profile.is_online,
            "message": message
        }, status=status.HTTP_200_OK)