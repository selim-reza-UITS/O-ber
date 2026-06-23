from decimal import Decimal
from math import ceil
from django.db.models import Case, When, IntegerField
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
import logging

logger = logging.getLogger("ober.rides")
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
        # ---- DEBUG: log the incoming request ----
        logger.debug(
            "[CreateRide] incoming request from user=%s payload=%s",
            getattr(request.user, "user_id", None),
            dict(request.data),
        )

        serializer = RideSerializer(data=request.data)
        if not serializer.is_valid():
            # ---- DEBUG: log why validation failed ----
            logger.warning("[CreateRide] serializer invalid: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            v_type = request.data.get("requested_vehicle_type", "ECONOMY")
            p_lat = serializer.validated_data["pickup_lat"]
            p_lng = serializer.validated_data["pickup_lng"]
            d_lat = serializer.validated_data["dropoff_lat"]
            d_lng = serializer.validated_data["dropoff_lng"]

            pickup_p = Point(p_lng, p_lat, srid=4326)
            dropoff_p = Point(d_lng, d_lat, srid=4326)
            estimated_price = calculate_dynamic_fare(pickup_p, dropoff_p, v_type)

            # ---- DEBUG: log the computed inputs ----
            logger.debug(
                "[CreateRide] v_type=%s pickup=(%s,%s) dropoff=(%s,%s) estimated_price=%s",
                v_type, p_lat, p_lng, d_lat, d_lng, estimated_price,
            )

            ride = serializer.save(
                rider=request.user,
                requested_vehicle_type=v_type,
                estimated_price=estimated_price,
                status="SEARCHING",
            )
            logger.info("[CreateRide] ride %s created (status=SEARCHING)", ride.id)

            # Import here to avoid any circular-import surprises at module load.
            from .dispatch import (
                build_ride_payload,
                dispatch_ride_to_nearby_drivers,
                get_nearby_drivers_for_ride,
            )

            # ---- DEBUG: enumerate the candidate drivers before dispatching ----
            radius_km = getattr(settings, "RIDE_DISCOVERY_RADIUS_KM", 5)
            candidates = list(get_nearby_drivers_for_ride(ride))
            logger.debug(
                "[CreateRide] ride %s: %s candidate driver(s) within %skm "
                "(vehicle_type=%s, pickup=%s,%s)",
                ride.id, len(candidates), radius_km, v_type,
                ride.pickup_location.y, ride.pickup_location.x,
            )
            for d in candidates:
                dist_km = getattr(getattr(d, "distance", None), "km", None)
                logger.debug(
                    "[CreateRide]   candidate driver_%s vehicle=%s distance=%s",
                    d.user_id, d.vehicle_type,
                    f"{dist_km:.2f}km" if dist_km is not None else "n/a",
                )

            # Push the ride to every eligible nearby driver. The same dispatcher
            # is reused by DriverDeclineRideView so a decline re-offers the ride.
            drivers_notified = dispatch_ride_to_nearby_drivers(ride, request=request)
            logger.info(
                "[CreateRide] ride %s dispatched to %s driver(s)",
                ride.id, drivers_notified,
            )
            if drivers_notified == 0:
                logger.warning(
                    "[CreateRide] ride %s: NO drivers notified — check that drivers "
                    "are online, admin_verified, have a recent location, match "
                    "vehicle_type='%s', and are within %skm.",
                    ride.id, v_type, radius_km,
                )

            response_data = build_ride_payload(ride, request=request)
            response_data["nearby_drivers_count"] = drivers_notified

            # ---- DEBUG: log the outgoing payload keys ----
            logger.debug(
                "[CreateRide] ride %s response keys=%s",
                ride.id, list(response_data.keys()),
            )

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception:
            # ---- DEBUG: never swallow a 500 silently ----
            logger.exception("[CreateRide] unexpected error while creating ride")
            return Response(
                {"error": "Could not create ride. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RideHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    RUNNING_STATUSES = ['ACCEPTED', 'ARRIVED', 'STARTED']

    def get(self, request):
        if request.user.is_driver:
            qs = Ride.objects.filter(driver=request.user)
        else:
            qs = Ride.objects.filter(rider=request.user)

        # Running rides first (0), then everything else (1); newest first within each group
        rides = qs.annotate(
            _running_first=Case(
                When(status__in=self.RUNNING_STATUSES, then=0),
                default=1,
                output_field=IntegerField(),
            )
        ).order_by('_running_first', '-created_at')

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

class ActiveRideView(APIView):
    """
    Returns the rider's current ongoing ride (if any).

    Called when the rider re-opens the app. If they had a ride that is still
    SEARCHING for a driver — or already ACCEPTED / ARRIVED / STARTED — we
    return it so the app can restore the correct screen instead of starting
    a brand-new search.
    """
    permission_classes = [IsRider]

    # Statuses that mean "something is happening right now"
    ACTIVE_STATUSES = ['SEARCHING', 'ACCEPTED', 'ARRIVED', 'STARTED']

    def get(self, request):
        ride = (
            Ride.objects
            .filter(rider=request.user, status__in=self.ACTIVE_STATUSES)
            .order_by('-created_at')
            .first()
        )

        if not ride:
            return Response(
                {"has_active_ride": False, "ride": None},
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "has_active_ride": True,
                "is_searching": ride.status == 'SEARCHING',
                "ride": RideSerializer(ride).data,
            },
            status=status.HTTP_200_OK,
        )