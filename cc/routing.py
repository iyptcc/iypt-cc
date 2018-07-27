from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

import apps.fight.routing

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket':  #AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                apps.fight.routing.websocket_urlpatterns
            )
        ),
    #),
})
