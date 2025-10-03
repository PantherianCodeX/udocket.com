from __future__ import annotations

import os
from pathlib import Path

import environ

from config.settings import settings

BASE_DIR = Path(__file__).resolve().parents[4]  # repo root (/app)
env = environ.Env()

storage_root_path = settings.ensure_storage_root()
if not storage_root_path.exists():
    fallback_root = (BASE_DIR / "storage").resolve()
    try:
        fallback_root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    else:
        storage_root_path = fallback_root
storage_config = settings.storage
STORAGE_ROOT = str(storage_config.root)

SECRET_KEY = settings.django.secret_key_value()
DEBUG = settings.django.debug

ALLOWED_HOSTS = list(settings.django.allowed_hosts)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "guardian",
    "rules",
    "simple_history",
    "mozilla_django_oidc",
    "apps.platform.jobs",
    "django_celery_results",
    "django_celery_beat",
    # Channels (ASGI)
    "channels",
    # Local apps
    "apps.platform.accounts",
    "apps.platform.cases",
    "apps.platform.artifacts",
    "apps.platform.operations",
    "apps.platform.authorization",
    "apps.platform.ui",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.platform.middleware.org_session_middleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "apps.platform.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "apps" / "platform" / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.platform.ui.context_processors.ui_context",
                "apps.platform.ui.context_processors.app_version",
            ],
        },
    },
]

WSGI_APPLICATION = None  # ASGI-first
ASGI_APPLICATION = "apps.platform.config.asgi.application"


running_tests = bool(os.environ.get("PYTEST_CURRENT_TEST"))
DATABASES = settings.database.as_django_config(env_parser=env, running_tests=running_tests)


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Organization scoping header (used by middleware to set DB session var for RLS)
ORG_HEADER_NAME = settings.django.org_header_name


LANGUAGE_CODE = settings.django.language_code
TIME_ZONE = settings.django.time_zone
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = str(storage_config.media_root())


# DRF
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.platform.accounts.auth.KeycloakJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SPECTACULAR_SETTINGS = {"TITLE": "uDocket API", "VERSION": "1.0.0"}


# Channels layer: use Redis if REDIS_URL set, else in-memory
redis_config = settings.redis
if redis_config.url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [redis_config.url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


# Security defaults (override in prod.py)
SECURE_SSL_REDIRECT = settings.django.secure_ssl_redirect
SESSION_COOKIE_SECURE = settings.django.session_cookie_secure
CSRF_COOKIE_SECURE = settings.django.csrf_cookie_secure
CSRF_TRUSTED_ORIGINS = list(settings.django.csrf_trusted_origins)
SECURE_HSTS_SECONDS = settings.django.secure_hsts_seconds
SECURE_CONTENT_TYPE_NOSNIFF = settings.django.secure_content_type_nosniff
SECURE_BROWSER_XSS_FILTER = settings.django.secure_browser_xss_filter


# Guardian object-perms
ANONYMOUS_USER_NAME = None

# Guardian backend for object permissions (warning silence)
oidc_config = settings.oidc
_oidc_enabled = oidc_config.is_enabled()

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
) + (("apps.platform.accounts.auth.KeycloakOIDCBackend",) if _oidc_enabled else tuple())


# Celery
celery_config = settings.celery
CELERY_BROKER_URL = celery_config.effective_broker_url()
CELERY_RESULT_BACKEND = celery_config.result_backend
CELERY_TASK_ALWAYS_EAGER = celery_config.task_always_eager
CELERY_TASK_TIME_LIMIT = celery_config.task_time_limit
CELERY_TASK_SOFT_TIME_LIMIT = celery_config.task_soft_time_limit

# Persist Celery beat schedule under storage/runtime/celery/
celery_runtime_dir = storage_config.runtime_dir("celery")
try:
    celery_runtime_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
CELERY_BEAT_SCHEDULE_FILENAME = str(celery_runtime_dir / "celerybeat-schedule")

# Logging configuration: rely on propagation so modules inherit handler wiring
logging_config = settings.logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": logging_config.root_level},
    "loggers": {
        name: {"level": level, "propagate": True}
        for name, level in logging_config.logger_levels.items()
    },
}

# Azure Blob env passthrough (for batch upload convenience)
azure_blob = settings.azure.blob
AZURE_BLOB_ACCOUNT = azure_blob.account
AZURE_BLOB_KEY = azure_blob.key_value()
AZURE_BLOB_CONNECTION_STRING = azure_blob.connection_string
AZURE_BLOB_CONTAINER = azure_blob.container
AZURE_BLOB_SAS_TTL_MIN = azure_blob.sas_ttl_min

# SimpleJWT (accept Keycloak JWTs via remote JWKS)
SIMPLE_JWT = oidc_config.simple_jwt()

# OIDC for browser SSO (Keycloak)
OIDC_RP_CLIENT_ID = oidc_config.client_id
OIDC_RP_CLIENT_SECRET = oidc_config.client_secret_value()
OIDC_OP_DISCOVERY_ENDPOINT = oidc_config.discovery_url
OIDC_RP_SIGN_ALGO = oidc_config.rp_sign_algo
# Route login via OIDC only when enabled; otherwise use Django admin/login
LOGIN_URL = "/oidc/authenticate/" if _oidc_enabled else "/admin/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
# Development/open access toggle (bypasses auth policies when true)
PLATFORM_DEV_OPEN = settings.django.platform_dev_open

# UI job table sizing (limits enforce websocket/poll efficiency)
jobs_ui_config = settings.jobs_ui
PLATFORM_UI_JOB_LIMIT_CHOICES = jobs_ui_config.limit_choices
PLATFORM_UI_JOB_MAX_LIMIT = jobs_ui_config.max_limit
PLATFORM_UI_JOB_DEFAULT_LIMIT = jobs_ui_config.default_limit

# If discovery is not set, derive OP endpoints from issuer when provided
OIDC_ISSUER = oidc_config.issuer
OIDC_OP_AUTHORIZATION_ENDPOINT = oidc_config.authorization_endpoint()
OIDC_OP_TOKEN_ENDPOINT = oidc_config.token_endpoint()
OIDC_OP_USER_ENDPOINT = oidc_config.userinfo_endpoint()
OIDC_OP_JWKS_ENDPOINT = oidc_config.jwks_endpoint()

# Default OIDC scopes for browser SSO
OIDC_RP_SCOPES = oidc_config.rp_scopes

# Optional: sync case memberships from Keycloak group claims
OIDC_SYNC_MEMBERSHIPS = oidc_config.sync_memberships
OIDC_CASE_GROUP_PREFIX = oidc_config.case_group_prefix
OIDC_CASE_GROUP_SEPARATOR = oidc_config.case_group_separator
OIDC_CASE_DEFAULT_ROLE = oidc_config.case_default_role
