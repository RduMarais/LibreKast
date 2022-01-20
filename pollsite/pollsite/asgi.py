"""
ASGI config for pollsite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

django_asgi_application = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import poll.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pollsite.settings')


# if __name__ == '__main__':
#     import django
#     django.setup()

application = ProtocolTypeRouter({
	"http" : django_asgi_application,
	"websocket": AuthMiddlewareStack(
        URLRouter(
            poll.routing.websocket_urlpatterns
        )
    ),
	})
