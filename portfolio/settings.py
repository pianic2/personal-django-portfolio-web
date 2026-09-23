"""Environment-aware Django settings for the portfolio backend."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_environment() -> None:
    """Load uncommitted local settings without adding a dotenv runtime dependency."""
    environment_file = BASE_DIR / ".env"
    if not environment_file.exists():
        return
    for line in environment_file.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


load_local_environment()


def env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    if value.lower() in {"1", "true", "yes", "on"}:
        return True
    if value.lower() in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be a boolean value.")


DEBUG = env_bool("DJANGO_DEBUG", default=True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "development-only-key-do-not-use-in-production"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY is required when DJANGO_DEBUG is false.")
if not DEBUG and (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5):
    raise RuntimeError("DJANGO_SECRET_KEY must be a strong production secret.")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]", "testserver"]
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS is required when DJANGO_DEBUG is false.")


def database_config() -> dict[str, object]:
    database_url = os.environ.get("DJANGO_DATABASE_URL")
    if not database_url:
        raise RuntimeError("DJANGO_DATABASE_URL must configure a PostgreSQL database.")
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DJANGO_DATABASE_URL must use postgres or postgresql.")
    db_name = unquote(parsed.path.lstrip("/"))
    if not parsed.hostname or not db_name:
        raise RuntimeError("DJANGO_DATABASE_URL must include a PostgreSQL host and database name.")
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise RuntimeError("DJANGO_DATABASE_URL must contain a valid PostgreSQL port.") from exc
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_name,
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname,
        "PORT": port,
    }


DATABASES = {"default": database_config()}

INSTALLED_APPS = [
    "portfolio",
    "rest_framework",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail.api.v3",
    "wagtail",
    "modelcluster",
    "taggit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "portfolio.urls"
WSGI_APPLICATION = "portfolio.wsgi.application"
ASGI_APPLICATION = "portfolio.asgi.application"

LANGUAGE_CODE = "it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True
WAGTAIL_I18N_ENABLED = True
LANGUAGES = [("it", "Italiano"), ("en", "English")]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,https://pianic2.github.io",
    ).split(",")
    if origin.strip()
]

PORTFOLIO_ADMIN_NAME = "Personal Django Portfolio"
WAGTAIL_SITE_NAME = PORTFOLIO_ADMIN_NAME
ADMIN_SITE_HEADER = PORTFOLIO_ADMIN_NAME
ADMIN_SITE_TITLE = PORTFOLIO_ADMIN_NAME
ADMIN_INDEX_TITLE = "Technical administration"
WAGTAILADMIN_BASE_URL = os.environ.get("DJANGO_BASE_URL", "http://localhost:8000")
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("DJANGO_EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("DJANGO_EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("DJANGO_EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("DJANGO_EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "webmaster@localhost")
CONTACT_RECIPIENT_EMAIL = os.environ.get("DJANGO_CONTACT_RECIPIENT_EMAIL", "")
CONTACT_FROM_EMAIL = os.environ.get("DJANGO_CONTACT_FROM_EMAIL") or DEFAULT_FROM_EMAIL
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "contact": "3/minute",
        "contact_duplicate": "1/minute",
    },
}

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
