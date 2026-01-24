# src/_config/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# 1. Set settings and initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src._config.settings.local')
django.setup()

# 2. Get the HTTP application
django_asgi_app = get_asgi_application()

# 3. Import Routing after django.setup()
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from src.apps.riders.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})