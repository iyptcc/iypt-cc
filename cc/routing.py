from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

import apps.fight.routing
import apps.result.routing
import apps.virtual.routing

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    'http': django_asgi_app,

    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                apps.fight.routing.websocket_urlpatterns + \
                apps.virtual.routing.websocket_urlpatterns + \
                apps.result.routing.websocket_urlpatterns
            )
        ),
    ),
})
