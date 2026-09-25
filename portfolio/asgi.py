import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portfolio.settings")

django_application = get_asgi_application()

# Importing urls completes router registration before generating the in-process
# Wagtail schema used by the MCP adapter.
from . import urls as _urls  # noqa: E402,F401
from .mcp_asgi import compose_asgi  # noqa: E402

application = compose_asgi(django_application)
