import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numeria_project.settings')

from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import mentorat.routing

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            mentorat.routing.websocket_urlpatterns
        )
    ),
})
