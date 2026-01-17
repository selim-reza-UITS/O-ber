from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_ride_update(ride_id, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'ride_{ride_id}',
        {
            'type': 'ride_update',
            'data': data
        }
    )