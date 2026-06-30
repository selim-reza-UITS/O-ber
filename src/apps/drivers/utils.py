from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_ride_update(ride_id, data):
    channel_layer = get_channel_layer()
    group_name = f'ride_{ride_id}'
    print(f"[DEBUG] broadcast_ride_update → group={group_name} data={data}", flush=True)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'ride_update',
            'data': data
        }
    )
    print(f"[DEBUG] broadcast_ride_update → group_send DONE", flush=True)

def notify_driver(driver_user_id, data):
    """Push an event to a SINGLE driver's personal discovery socket.

    The driver app stays connected to DriverDiscoveryConsumer (group
    `driver_<user_id>`), NOT the per-ride TripTracking group `ride_<id>`.
    So ride-level events that the driver must see — like a rider cancelling an
    already-accepted ride — have to be sent here as well as via
    broadcast_ride_update().
    """
    if not driver_user_id:
        return
    channel_layer = get_channel_layer()
    group_name = f'driver_{driver_user_id}'
    print(f"[DEBUG] notify_driver → group={group_name} data={data}", flush=True)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'ride_cancelled',
            'data': data,
        }
    )
    print(f"[DEBUG] notify_driver → group_send DONE", flush=True)