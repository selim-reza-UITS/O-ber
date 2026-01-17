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