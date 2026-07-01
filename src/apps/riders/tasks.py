from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@shared_task
def task_broadcast_location(ride_id, lat, lng, status):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'ride_{ride_id}',
        {
            'type': 'ride_update',
            'data': {
                "type": "LOCATION_UPDATE",
                "lat": lat,
                "lng": lng,
                "status": status
            }
        }
    )

@shared_task
def task_expire_ride_offer(ride_id, driver_user_id, offered_at_iso):
    """
    If the driver currently holding the offer hasn't responded within
    RIDE_OFFER_TIMEOUT_SECONDS, treat it as a decline and advance to the next.
    The guards make this a no-op if the ride was accepted/cancelled/re-offered.
    """
    from django.utils.dateparse import parse_datetime
    from src.apps.riders.models import Ride, RideDecline
    from src.apps.riders.dispatch import offer_ride_to_next_driver

    try:
        ride = Ride.objects.get(id=ride_id)
    except Ride.DoesNotExist:
        return

    if ride.status != "SEARCHING":
        return
    if ride.offered_to_id != driver_user_id:
        return
    expected = parse_datetime(offered_at_iso)
    if ride.offered_at is None or (
        expected is not None and abs((ride.offered_at - expected).total_seconds()) > 1
    ):
        return

    RideDecline.objects.get_or_create(ride_id=ride_id, driver_id=driver_user_id)
    try:
        from src.apps.drivers.utils import notify_driver
        from src.apps.riders.dispatch import build_ride_payload
        notify_driver(driver_user_id, {
            "event": "RIDE_OFFER_EXPIRED",
            "ride": build_ride_payload(ride),
            "message": "This ride offer expired.",
        })
    except Exception:
        pass
    offer_ride_to_next_driver(ride)