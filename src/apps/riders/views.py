from decimal import Decimal
from math import ceil

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from src.apps.accounts.models import DriverProfile
from src.apps.accounts.permissions import IsRider
from src.apps.drivers.utils import broadcast_ride_update

from .models import Ride, RideReview
from .serializers import RideSerializer
from .utils import calculate_dynamic_fare

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

        RADIUS_KM = 5

        # Find which vehicle types actually have an online driver within 5km.
        nearby_drivers = DriverProfile.objects.filter(
            is_active=True,
            is_online=True,
            last_location__isnull=False,
            last_location__distance_lte=(pickup_point, D(km=RADIUS_KM)),
        )

        # Count available drivers per normalized vehicle type.
        type_counts = {}
        for driver in nearby_drivers:
            if not driver.vehicle_type:
                continue
            key = driver.vehicle_type.strip().upper()
            type_counts[key] = type_counts.get(key, 0) + 1

        estimates = []
        for v_type, available_drivers in type_counts.items():
            price = calculate_dynamic_fare(pickup_point, dropoff_point, v_type)
            eta_minutes = max(1, ceil((distance_km / 40) * 60))
            estimates.append({
                "vehicle_type": v_type,
                "estimated_price": str(price),
                "currency": "AWG",
                "available_drivers": available_drivers,
                "eta_minutes": eta_minutes,
            })

        # Optional: sort so cheaper/expected tiers come first
        tier_order = {"ECONOMY": 0, "XL": 1, "PREMIUM": 2}
        estimates.sort(key=lambda e: tier_order.get(e["vehicle_type"], 99))

        return Response({
            "pickup_address": pickup_address,
            "dropoff_address": dropoff_address,
            "distance_km": distance_km,
            "estimates": estimates,
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

            radius_km = getattr(settings, "RIDE_DISCOVERY_RADIUS_KM", 5)
            nearby_drivers = DriverProfile.objects.filter(
                is_online=True,            # actually toggled online
                admin_verified=True,       # the real "approved driver" gate (is_active is admin-only and often unset)
                last_location__isnull=False,
                last_location__distance_lte=(ride.pickup_location, D(km=radius_km)),
                # Optional vehicle-type match — case-insensitive so "Economy" matches "ECONOMY".
                # Remove this line if your driver vehicle_type values don't map cleanly to requested types.
                vehicle_type__iexact=v_type,
            ).annotate(
                distance=Distance('last_location', ride.pickup_location)
            ).order_by('distance')

            # --- TEMP DEBUG ---
            print(
                f"[DEBUG] Ride {ride.id} requested='{v_type}' "
                f"pickup={ride.pickup_location.y},{ride.pickup_location.x} "
                f"→ {nearby_drivers.count()} driver(s) within {radius_km}km",
                flush=True,
            )
            # ------------------

            channel_layer = get_channel_layer()
            ride_data = RideSerializer(ride).data

            # ---- enrich ride_data (this is the block you must NOT drop) ----
            total_distance = round(ride.pickup_location.distance(ride.dropoff_location) * 111.32, 2)
            eta_minutes = max(1, ceil((total_distance / 40) * 60))
            ride_data["distance"] = total_distance
            ride_data["estimated_time"] = eta_minutes
            ride_data["total_distance"] = total_distance
            ride_data["total_price"] = str(ride.estimated_price)
            ride_data["eta"] = eta_minutes

            rider_photo = None
            if hasattr(request.user, 'rider_profile') and request.user.rider_profile.user_photo:
                rider_photo = request.build_absolute_uri(request.user.rider_profile.user_photo.url)

            rider_details = {
                "user_id": request.user.user_id,
                "full_name": request.user.full_name,
                "email": request.user.email,
                "phone_number": request.user.phone_number,
                "user_photo": rider_photo,
            }
            ride_data["rider_details"] = rider_details
            # ----------------------------------------------------------------

            for driver in nearby_drivers:
                print(
                    f"[DEBUG]   → pushing ride {ride.id} to driver_{driver.user_id} "
                    f"(vehicle='{driver.vehicle_type}', {driver.distance.km:.2f} km away)",
                    flush=True,
                )
                async_to_sync(channel_layer.group_send)(
                    f"driver_{driver.user_id}",
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
        
        # Validate rating
        if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
            return Response({"error": "Rating must be an integer between 1 and 5"}, status=400)
        
        review = RideReview.objects.create(
            ride=ride,
            rider=request.user,
            driver=ride.driver,
            rating=rating,
            comment=comment
        )
        
        # Notify driver via websocket
        broadcast_ride_update(ride.id, {
            "type": "DRIVER_REVIEWED",
            "rating": rating,
            "comment": comment,
            "reviewer": request.user.full_name,
        })
        
        return Response({
            "message": "Review submitted successfully",
            "review": {
                "id": review.id,
                "ride_id": ride.id,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at,
                "reviewer": request.user.full_name,
            }
        }, status=201)