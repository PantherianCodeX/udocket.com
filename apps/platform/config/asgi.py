import os
from django.core.asgi import get_asgi_application
from django.conf import settings

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE", "apps.platform.config.settings.dev")
)

django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from apps.platform.config.routing import websocket_urlpatterns
    # Serve static files in development (DEBUG) so /static/admin/* works under Daphne
    if getattr(settings, "DEBUG", False):
        try:
            from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
            http_app = ASGIStaticFilesHandler(django_asgi_app)
        except Exception:
            http_app = django_asgi_app
    else:
        http_app = django_asgi_app

    application = ProtocolTypeRouter({
        "http": http_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    })
except Exception:
    application = django_asgi_app
