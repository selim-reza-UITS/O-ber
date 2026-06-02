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