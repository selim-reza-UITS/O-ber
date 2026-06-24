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
from django.conf import settings
from src.apps.accounts.permissions import IsDriver, IsVerifiedDriver
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from src.apps.accounts.models import DriverProfile
from .serializers import DriverDashboardSerializer
from .models import DriverShift
from django.utils import timezone
from django.db.models import Case, When, IntegerField

from src.apps.riders.models import Ride, RideDecline


class UpdateDriverLocationView(APIView):
    # Security: Ensure only authenticated DRIVERS can call this
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lat = request.data.get('latitude') or request.data.get('lat')
        lng = request.data.get('longitude') or request.data.get('lng')

        if lat is None or lng is None:
            return Response({"error": "Coordinates (latitude, longitude) required"}, status=status.HTTP_400_BAD_REQUEST)

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
            ).order_by('-id').first()
            
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
            import traceback
            traceback.print_exc()
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
        ).exclude(
            declines__driver=request.user
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
            # Only the driver currently holding the offer may accept.
            if ride.offered_to_id and ride.offered_to_id != request.user.user_id:
                return Response({"error": "This ride has moved to another driver."}, status=409)
            # --- Geofence guard: driver must be within the allowed radius of the pickup ---
            driver_profile = request.user.driver_profile
            if not driver_profile.last_location:
                return Response({"error": "Update your location first"}, status=400)

            radius_km = getattr(settings, "RIDE_DISCOVERY_RADIUS_KM", 5)
            distance_to_pickup_km = driver_profile.last_location.distance(ride.pickup_location) * 111.32
            if distance_to_pickup_km > radius_km:
                return Response(
                    {"error": "You are too far from the pickup location to accept this ride."},
                    status=403
                )
            # -----------------------------------------------------------------------------

            # Assign driver and change status
            ride.driver = request.user
            ride.status = 'ACCEPTED'
            ride.offered_to = None
            ride.offered_at = None
            ride.save()
            from django.db.models import Avg
            from math import ceil
            driver_profile = request.user.driver_profile
            avg_rating = request.user.reviews_received.aggregate(Avg('rating'))['rating__avg']
            rating = round(float(avg_rating), 1) if avg_rating else 0.0
            total_trips = request.user.rides_as_driver.filter(status='COMPLETED').count()
            vehicle_name = f"{driver_profile.vehicle_brand} {driver_profile.vehicle_model}"
            first_photo = driver_profile.vehicle_photos.first()
            vehicle_photo = (
                request.build_absolute_uri(first_photo.image.url)
                if first_photo and first_photo.image else None
            )

            # ETA and distance from driver's current location to rider's pickup
            if driver_profile.last_location and ride.pickup_location:
                distance_to_rider = round(
                    driver_profile.last_location.distance(ride.pickup_location) * 111.32, 2
                )
                eta_to_rider = max(1, ceil((distance_to_rider / 40) * 60))
            else:
                distance_to_rider = None
                eta_to_rider = None

            broadcast_ride_update(ride.id, {
                "type": "DRIVER_ACCEPTED",
                "status": "ACCEPTED",
                "driver_name": request.user.full_name,
                "driver_phone": request.user.phone_number,
                'driver_image': request.build_absolute_uri(driver_profile.user_photo.url) if driver_profile.user_photo else None,
                "vehicle": vehicle_name,
                "rating": rating,
                "total_trips": total_trips,
                "vehicle_name": vehicle_name,
                "vehicle_number": driver_profile.vehicle_plate,
                "vehicle_photo": vehicle_photo,

                "ride_details":{
                    "pickup_location": {
                        "lat": ride.pickup_location.y,
                        "lng": ride.pickup_location.x
                    },
                    "dropoff_location": {
                        "lat": ride.dropoff_location.y,
                        "lng": ride.dropoff_location.x
                    },
                    "estimated_price": str(ride.estimated_price),
                    "rider_name": ride.rider.full_name,
                    "rider_phone": ride.rider.phone_number,
                    'rider_image': request.build_absolute_uri(ride.rider.rider_profile.user_photo.url) if hasattr(ride.rider, 'rider_profile') and ride.rider.rider_profile.user_photo else None,
                    "eta_to_rider": eta_to_rider,
                    "distance_to_rider": distance_to_rider,
                }
            })
            return Response({
                "message": "Ride accepted successfully",
                "ride_id": ride.id
            })
        
class DriverDeclineRideView(APIView):
    """
    Lets a driver decline a ride request that popped up in their app.
    The ride stays SEARCHING and keeps being offered to OTHER drivers, but it
    will no longer appear in THIS driver's available-rides list.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        try:
            ride = Ride.objects.get(id=ride_id)
        except Ride.DoesNotExist:
            return Response({"error": "Ride not found"}, status=404)

        # Only an open, still-searching request can be declined.
        if ride.status != 'SEARCHING':
            return Response(
                {"error": "This ride is no longer available to decline."},
                status=400,
            )

        # Idempotent: unique_together(ride, driver) prevents duplicate rows.
        RideDecline.objects.get_or_create(ride=ride, driver=request.user)

        # Re-offer the ride to the next nearby driver(s). Drivers who already
        # declined (including this one) are excluded inside the dispatcher, so
        # the ride effectively "moves" to another driver.
        from src.apps.riders.dispatch import offer_ride_to_next_driver
        next_driver = offer_ride_to_next_driver(ride, request=request)

        return Response(
            {
                "message": (
                    "Ride declined and offered to the next driver."
                    if next_driver else
                    "Ride declined. No more nearby drivers available."
                ),
                "ride_id": ride.id,
                "offered_to_driver": next_driver.user_id if next_driver else None,
            },
            status=200,
        )
    
class DriverCancelRideView(APIView):
    """
    Lets the assigned driver cancel a trip they accepted, as long as the
    passenger has NOT been picked up yet (status == 'ACCEPTED').
    The ride is requeued: driver is unassigned and status returns to
    'SEARCHING' so another nearby driver can accept it.
    """
    permission_classes = [IsAuthenticated]

    CANCELLABLE_STATUSES = ['ACCEPTED']

    def post(self, request, ride_id):
        with transaction.atomic():
            try:
                ride = Ride.objects.select_for_update().get(id=ride_id)
            except Ride.DoesNotExist:
                return Response({"error": "Ride not found"}, status=404)

            # Only the currently assigned driver may cancel this ride.
            # Compare instances (User PK is `user_id`, so there is no `.id`).
            if ride.driver != request.user:
                return Response({"error": "You are not the driver for this ride"}, status=403)

            # Only before pickup. 'STARTED' means the passenger is already picked up.
            if ride.status not in self.CANCELLABLE_STATUSES:
                return Response(
                    {"error": "You can only cancel a ride you've accepted and not yet started."},
                    status=400,
                )

            reason = request.data.get('reason', 'Driver cancelled before pickup')

            # Requeue: drop this driver and reopen the ride for others
            ride.driver = None
            ride.status = 'SEARCHING'
            ride.save(update_fields=['driver', 'status'])

        # Tell the rider their driver cancelled and we're finding a new one
        broadcast_ride_update(ride.id, {
            "type": "DRIVER_CANCELLED",
            "status": "SEARCHING",
            "message": "Your driver cancelled. We're finding you a new driver.",
            "reason": reason,
        })

        return Response(
            {
                "message": "Ride cancelled and requeued for other drivers.",
                "ride_id": ride.id,
                "status": ride.status,
            },
            status=200,
        )


class DriverProfileDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver profile not found"}, status=404)

        serializer = DriverDashboardSerializer(profile, context={"request": request})
        
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


class DriverEarningsView(APIView):
    """
    Returns comprehensive earnings report for the driver:
    - Total earnings (all time)
    - Total trips
    - Online time
    - Date-wise earnings breakdown
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncDate
        from src.apps.payments.models import Transaction
        from datetime import timedelta
        
        try:
            profile = request.user.driver_profile
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver profile not found"}, status=404)

        # 1. Total Earnings (All Time)
        completed_rides = Ride.objects.filter(driver=request.user, status='COMPLETED')
        total_earnings = Transaction.objects.filter(
            ride__in=completed_rides,
            status='SUCCESS'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # 2. Total Trips
        total_trips = completed_rides.count()

        # 3. Online Time (Total from all shifts)
        total_online_seconds = sum(
            [shift.duration.total_seconds() for shift in profile.shifts.filter(end_time__isnull=False)],
            0
        )
        total_online_hours = round(total_online_seconds / 3600, 1)

        # 4. Average Rating
        from django.db.models import Avg
        from src.apps.riders.models import RideReview
        avg_rating = RideReview.objects.filter(driver=request.user).aggregate(Avg('rating'))['rating__avg']
        avg_rating = round(avg_rating, 1) if avg_rating else 0.0

        # 5. Date-wise Earnings (Last 30 days)
        last_30_days = timezone.now() - timedelta(days=30)
        daily_earnings = Transaction.objects.filter(
            ride__driver=request.user,
            ride__status='COMPLETED',
            status='SUCCESS',
            created_at__gte=last_30_days
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            earnings=Sum('amount'),
            trips=Count('id')
        ).order_by('-date')

        # 6. This Week's Earnings
        last_7_days = timezone.now() - timedelta(days=7)
        this_week_earnings = Transaction.objects.filter(
            ride__driver=request.user,
            ride__status='COMPLETED',
            status='SUCCESS',
            created_at__gte=last_7_days
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        return Response({
            "summary": {
                "total_earnings": str(total_earnings),
                "this_week_earnings": str(this_week_earnings),
                "total_trips": total_trips,
                "total_online_hours": total_online_hours,
                "average_rating": avg_rating,
                "currency": "AWG"
            },
            "daily_breakdown": list(daily_earnings)
        })


class DriverTripHistoryView(APIView):
    """
    Returns driver's trips: running rides first, then past trips (with ratings)
    """
    permission_classes = [IsAuthenticated]

    RUNNING_STATUSES = ['ACCEPTED', 'ARRIVED', 'STARTED']

    def get(self, request):
        rides = Ride.objects.filter(
            driver=request.user
        ).select_related('rider').annotate(
            _running_first=Case(
                When(status__in=self.RUNNING_STATUSES, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by('_running_first', '-created_at')

        history = []
        for ride in rides:
            ride_data = RideSerializer(ride).data
            # Add rating if exists
            if hasattr(ride, 'review'):
                ride_data['rating'] = ride.review.rating
                ride_data['review_comment'] = ride.review.comment
            else:
                ride_data['rating'] = None
                ride_data['review_comment'] = None
            history.append(ride_data)

        return Response(history)