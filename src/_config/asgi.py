import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from src.apps.riders.consumers import TripTrackingConsumer,RideChatConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src._config.settings.local')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/ride/<str:ride_id>/", TripTrackingConsumer.as_asgi()),
            path("ws/ride/chat/<str:ride_id>/", RideChatConsumer.as_asgi()),
        ])
    ),
})