import os
from django.core.asgi       import get_asgi_application
from channels.routing       import ProtocolTypeRouter, URLRouter
from channels.auth          import AuthMiddlewareStack
from django.urls            import path
from Zecbay                 import consumers  # Import the WebSocket consumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Zecbay.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/bids/<str:auction_id>/', consumers.BidConsumer.as_asgi()),  # WebSocket for bids
            path('ws/messages/<str:auction_id>/', consumers.MessageConsumer.as_asgi()),  # WebSocket for messages
        ])
    ),
})
