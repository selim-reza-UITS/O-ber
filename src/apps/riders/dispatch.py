from math import ceil

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from datetime import timedelta
from django.utils import timezone
from src.apps.accounts.models import DriverProfile
from .serializers import RideSerializer
from src.apps.drivers.utils import broadcast_ride_update
from django.db import transaction

import logging

# Module logger so re-dispatch activity is visible in your logs.
logger = logging.getLogger("ober.rides")

def build_ride_payload(ride, request=None):
    """
    Build the exact same NEW_RIDE_AVAILABLE payload the rider app expects.
    Kept in one place so the ride looks identical whether it is dispatched on
    creation OR re-dispatched after a driver declines.
    """
    ride_data = RideSerializer(ride).data

    total_distance = round(ride.pickup_location.distance(ride.dropoff_location) * 111.32, 2)
    eta_minutes = max(1, ceil((total_distance / 40) * 60))
    ride_data["distance"] = total_distance
    ride_data["estimated_time"] = eta_minutes
    ride_data["total_distance"] = total_distance
    ride_data["total_price"] = str(ride.estimated_price)
    ride_data["eta"] = eta_minutes

    rider = ride.rider
    rider_photo = None
    if hasattr(rider, "rider_profile") and rider.rider_profile.user_photo:
        url = rider.rider_profile.user_photo.url
        rider_photo = request.build_absolute_uri(url) if request is not None else url

    ride_data["rider_details"] = {
        "user_id": rider.user_id,
        "full_name": rider.full_name,
        "email": rider.email,
        "phone_number": rider.phone_number,
        "user_photo": rider_photo,
    }
    return ride_data
# Ride statuses that mean the driver is actively handling a trip and must not
# be offered another ride.
ACTIVE_RIDE_STATUSES = ["ACCEPTED", "ARRIVED", "STARTED"]


def get_busy_driver_ids(exclude_ride_id=None):
    """User ids of drivers who are NOT free to take a new ride right now.

    A driver is considered busy if either:
      * they are the assigned driver on a ride that is currently ACCEPTED /
        ARRIVED / STARTED (an active trip), OR
      * they are currently holding an outstanding offer (`offered_to`) on some
        OTHER still-SEARCHING ride.

    Used both by the dispatcher (so a ride is never offered to a busy driver)
    and by the fare/availability screen (so busy drivers aren't shown as
    available). Pass exclude_ride_id to ignore the ride currently being
    dispatched, so it doesn't count its own outstanding offer as "busy".
    """
    from .models import Ride

    busy = set(
        Ride.objects.filter(
            status__in=ACTIVE_RIDE_STATUSES, driver__isnull=False
        ).values_list("driver_id", flat=True)
    )

    outstanding_offers = Ride.objects.filter(
        status="SEARCHING", offered_to__isnull=False
    )
    if exclude_ride_id is not None:
        outstanding_offers = outstanding_offers.exclude(id=exclude_ride_id)
    busy.update(outstanding_offers.values_list("offered_to_id", flat=True))

    return busy

def get_nearby_drivers_for_ride(ride):
    """
    Nearby, online, verified drivers of the right vehicle type, EXCLUDING any
    driver who already declined THIS ride. Ordered nearest-first.
    """
    radius_km = getattr(settings, "RIDE_DISCOVERY_RADIUS_KM", 5)
    qs = (
        DriverProfile.objects.filter(
            is_online=True,
            admin_verified=True,
            last_location__isnull=False,
            last_location__distance_lte=(ride.pickup_location, D(km=radius_km)),
            vehicle_type__iexact=ride.requested_vehicle_type,
        )
        .exclude(user__declined_rides__ride=ride)
    )

    # Defense-in-depth against "phantom" drivers: if a driver loses their socket
    # without a clean disconnect, is_online can stay True. Optionally drop
    # drivers whose profile hasn't been touched (location-update bumps
    # updated_at) within the freshness window, so they can't silently absorb a
    # dispatch. Tune RIDE_DRIVER_MAX_LOCATION_AGE_SECONDS to your app's
    # location-ping interval; leave it unset/None to disable.
    max_age = getattr(settings, "RIDE_DRIVER_MAX_LOCATION_AGE_SECONDS", None)
    if max_age:
        cutoff = timezone.now() - timedelta(seconds=max_age)
        qs = qs.filter(updated_at__gte=cutoff)

    # Exclude drivers who cannot take a new ride right now: already on an active
    # trip, OR currently holding an outstanding offer for a DIFFERENT ride. This
    # is what stops two simultaneous ride requests from being offered to (and
    # double-booking) the same driver.
    busy_ids = get_busy_driver_ids(exclude_ride_id=ride.id)
    if busy_ids:
        qs = qs.exclude(user_id__in=busy_ids)

    return (
        qs.annotate(distance=Distance("last_location", ride.pickup_location))
        .order_by("distance")
    )

def offer_ride_to_next_driver(ride, request=None):
    """
    SEQUENTIAL dispatch. Offer the ride to the SINGLE nearest eligible driver
    who has not declined it yet. If that driver declines (or doesn't respond in
    time) this is called again to advance to the next-nearest driver.

    Returns the DriverProfile the ride was offered to, or None if nobody is
    left (in which case the rider is told NO_DRIVERS_AVAILABLE).
    """
    if ride.status != "SEARCHING":
        return None

    driver = None
    candidates = list(get_nearby_drivers_for_ride(ride))
    for candidate in candidates:
        with transaction.atomic():
            locked = (
                DriverProfile.objects.select_for_update()
                .filter(pk=candidate.pk)
                .first()
            )
            if locked is None:
                continue
            # Re-verify UNDER the lock that nobody claimed this driver between
            # our nearby query and acquiring the row lock.
            if locked.user_id in get_busy_driver_ids(exclude_ride_id=ride.id):
                continue
            # Claim: record the offer so accept-exclusivity + timeouts work, and
            # so a concurrent dispatch now sees this driver as busy.
            ride.offered_to = locked.user
            ride.offered_at = timezone.now()
            ride.save(update_fields=["offered_to", "offered_at"])
            driver = locked
        if driver is not None:
            break

    if driver is None:
        ride.offered_to = None
        ride.offered_at = None
        ride.save(update_fields=["offered_to", "offered_at"])
        broadcast_ride_update(ride.id, {
            "type": "NO_DRIVERS_AVAILABLE",
            "ride_id": ride.id,
            "message": "No nearby drivers are available right now.",
        })
        return None

    # Record the current offer so we can enforce accept-exclusivity + timeouts.
    ride.offered_to = driver.user
    ride.offered_at = timezone.now()
    ride.save(update_fields=["offered_to", "offered_at"])

    channel_layer = get_channel_layer()
    ride_data = build_ride_payload(ride, request=request)
    async_to_sync(channel_layer.group_send)(
        f"driver_{driver.user_id}",
        {
            "type": "new_ride_available",
            "data": {"event": "NEW_RIDE_AVAILABLE", "ride": ride_data},
        },
    )

    # Auto-advance if this driver doesn't respond in time (needs Celery+Redis).
    timeout = getattr(settings, "RIDE_OFFER_TIMEOUT_SECONDS", 20)
    if timeout:
        try:
            from .tasks import task_expire_ride_offer
            task_expire_ride_offer.apply_async(
                args=[ride.id, driver.user_id, ride.offered_at.isoformat()],
                countdown=timeout,
            )
        except Exception:
            pass

    return driver

def redispatch_stalled_rides(request=None, exclude_ride_id=None):
    """Retry dispatch for rides that are still SEARCHING but have NO live offer.

    Call this whenever a driver frees up — e.g. they decline an offer, or a trip
    of theirs completes / is cancelled. A ride that previously ran out of
    candidates and got NO_DRIVERS_AVAILABLE (its `offered_to` was reset to None)
    will now be retried against the newly-free driver.

    Oldest requests are retried first, so the rider who has been waiting longest
    gets the freed driver. `offer_ride_to_next_driver` still atomically claims a
    driver, so this is safe to call from concurrent requests.
    """
    from .models import Ride

    stalled = Ride.objects.filter(
        status="SEARCHING", offered_to__isnull=True
    ).order_by("created_at")
    if exclude_ride_id is not None:
        stalled = stalled.exclude(id=exclude_ride_id)

    stalled_ids = list(stalled.values_list("id", flat=True))
    if not stalled_ids:
        # Nothing is waiting — stay silent so this is cheap to call from frequent
        # hooks like driver location pings.
        return
    logger.info(
        "[Redispatch] a driver became available; retrying stalled ride(s): %s",
        stalled_ids,
    )

    for stalled_ride in stalled:
        offered = offer_ride_to_next_driver(stalled_ride, request=request)
        if offered is not None:
            logger.info(
                "[Redispatch] ride %s re-offered to driver_%s",
                stalled_ride.id, offered.user_id,
            )
        else:
            logger.info(
                "[Redispatch] ride %s still has no available driver",
                stalled_ride.id,
            )

            
def dispatch_ride_to_nearby_drivers(ride, request=None):
    """
    Push NEW_RIDE_AVAILABLE to every eligible nearby driver who has NOT declined
    this ride yet.

    Safe to call on creation AND on every decline: because declined drivers are
    filtered out, a decline naturally re-offers the ride to the next driver(s).
    Returns the number of drivers the ride was pushed to.
    """
    if ride.status != "SEARCHING":
        return 0

    drivers = get_nearby_drivers_for_ride(ride)
    channel_layer = get_channel_layer()
    ride_data = build_ride_payload(ride, request=request)

    count = 0
    for driver in drivers:
        async_to_sync(channel_layer.group_send)(
            f"driver_{driver.user_id}",
            {
                "type": "new_ride_available",
                "data": {
                    "event": "NEW_RIDE_AVAILABLE",
                    "ride": ride_data,
                },
            },
        )
        count += 1
    return count