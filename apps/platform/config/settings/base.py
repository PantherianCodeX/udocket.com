from __future__ import annotations

import os
from pathlib import Path
import environ


BASE_DIR = Path(__file__).resolve().parents[4]  # repo root (/app)
env = environ.Env()

# Load .env from repo root, but only if present (avoid noisy log)
_env_path = BASE_DIR / ".env"
# Only auto-read .env when explicitly enabled. In Docker, compose already
# provides env vars via env_file, and in local pytest discovery we avoid
# binding to container-only values (e.g., Postgres host).
if os.environ.get("ENV_READ_DOTENV") == "1" and _env_path.exists():
    environ.Env.read_env(str(_env_path))


SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-secret-key")
DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

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
                "apps.platform.ui.context.ui_context",
            ],
        },
    },
]

WSGI_APPLICATION = None  # ASGI-first
ASGI_APPLICATION = "apps.platform.config.asgi.application"


# Database: honor DATABASE_URL; default to local sqlite under storage root
default_storage = (BASE_DIR / "storage").resolve()
sr_env = env("STORAGE_ROOT", default=str(default_storage))
storage_root = Path(sr_env).resolve()
# Ensure storage root exists; if not creatable, fall back to repo storage/
_ok = True
try:
    storage_root.mkdir(parents=True, exist_ok=True)
except Exception:
    _ok = False
if not _ok or not storage_root.exists():
    storage_root = default_storage
    try:
        storage_root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
default_sqlite_path = storage_root / "udocket_django.db"

# Robust DB config with local fallback when DATABASE_URL points to an
# unavailable path (e.g., host dev using container-oriented /app/storage).
if os.environ.get("PYTEST_CURRENT_TEST"):
    test_url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{default_sqlite_path}"
    )
    if test_url.startswith("sqlite:///"):
        _sqlite_path = Path(test_url.replace("sqlite:///", "")).resolve()
        _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(_sqlite_path)}}
    else:
        DATABASES = {"default": environ.Env.db_url_config(test_url)}
else:
    _db_url = env("DATABASE_URL", default=f"sqlite:///{default_sqlite_path}")
    if isinstance(_db_url, str) and _db_url.startswith("sqlite:///"):
        _sqlite_path = Path(_db_url.replace("sqlite:///", "")).resolve()
        try:
            _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(_sqlite_path)}}
        except Exception:
            DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(default_sqlite_path)}}
    else:
        DATABASES = {"default": env.db("DATABASE_URL", default=_db_url)}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Organization scoping header (used by middleware to set DB session var for RLS)
ORG_HEADER_NAME = env("ORG_HEADER_NAME", default="HTTP_X_ORGANIZATION_ID")


LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", default="en-ca")
TIME_ZONE = env("DJANGO_TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = str(BASE_DIR / "static")

MEDIA_URL = "/media/"
MEDIA_ROOT = str(storage_root / "media")


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
_redis_url = env("REDIS_URL", default=None)
if _redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


# Security defaults (override in prod.py)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True


# Guardian object-perms
ANONYMOUS_USER_NAME = None

# Guardian backend for object permissions (warning silence)
# Enable OIDC backend only when OIDC is configured (discovery or explicit endpoints)
_oidc_enabled = bool(env("OIDC_DISCOVERY_URL", default=None) or env("OIDC_OP_TOKEN_ENDPOINT", default=None))

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
) + (("apps.platform.accounts.auth.KeycloakOIDCBackend",) if _oidc_enabled else tuple())


# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=env("REDIS_URL", default="redis://localhost:6379/1"))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=7200)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=7100)

# Logging to stdout
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
    "loggers": {
        "apps.platform": {"handlers": ["console"], "level": env("PLATFORM_LOG_LEVEL", default="DEBUG"), "propagate": False},
        "azure": {"handlers": ["console"], "level": env("AZURE_LOG_LEVEL", default="WARNING"), "propagate": False},
    },
}

# Azure Blob env passthrough (for batch upload convenience)
AZURE_BLOB_ACCOUNT = env("AZURE_BLOB_ACCOUNT", default=None)
AZURE_BLOB_KEY = env("AZURE_BLOB_KEY", default=None)
AZURE_BLOB_CONNECTION_STRING = env("AZURE_BLOB_CONNECTION_STRING", default=None)
AZURE_BLOB_CONTAINER = env("AZURE_BLOB_CONTAINER", default=None)
AZURE_BLOB_SAS_TTL_MIN = env.int("AZURE_BLOB_SAS_TTL_MIN", default=120)

# SimpleJWT (accept Keycloak JWTs via remote JWKS)
SIMPLE_JWT = {
    "JWK_URL": env("OIDC_JWKS_URL", default=None),
    "ALGORITHMS": ["RS256"],
    "AUDIENCE": env("OIDC_AUDIENCE", default=None),
    "ISSUER": env("OIDC_ISSUER", default=None),
}

# OIDC for browser SSO (Keycloak)
OIDC_RP_CLIENT_ID = env("OIDC_CLIENT_ID", default=None)
OIDC_RP_CLIENT_SECRET = env("OIDC_CLIENT_SECRET", default=None)
OIDC_OP_DISCOVERY_ENDPOINT = env("OIDC_DISCOVERY_URL", default=None)
OIDC_RP_SIGN_ALGO = env("OIDC_RP_SIGN_ALGO", default="RS256")
# Route login via OIDC only when enabled; otherwise use Django admin/login
LOGIN_URL = "/oidc/authenticate/" if _oidc_enabled else "/admin/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
# Development/open access toggle (bypasses auth policies when true)
PLATFORM_DEV_OPEN = env.bool("PLATFORM_DEV_OPEN", default=False)

# If discovery is not set, derive OP endpoints from OIDC_ISSUER when provided
OIDC_ISSUER = env("OIDC_ISSUER", default=None)
_op_auth = env("OIDC_OP_AUTHORIZATION_ENDPOINT", default=None)
_op_token = env("OIDC_OP_TOKEN_ENDPOINT", default=None)
_op_user = env("OIDC_OP_USER_ENDPOINT", default=None)
_op_jwks = env("OIDC_OP_JWKS_ENDPOINT", default=None)
if _op_auth:
    OIDC_OP_AUTHORIZATION_ENDPOINT = _op_auth
elif OIDC_ISSUER:
    OIDC_OP_AUTHORIZATION_ENDPOINT = OIDC_ISSUER.rstrip("/") + "/protocol/openid-connect/auth"
if _op_token:
    OIDC_OP_TOKEN_ENDPOINT = _op_token
elif OIDC_ISSUER:
    OIDC_OP_TOKEN_ENDPOINT = OIDC_ISSUER.rstrip("/") + "/protocol/openid-connect/token"
if _op_user:
    OIDC_OP_USER_ENDPOINT = _op_user
elif OIDC_ISSUER:
    OIDC_OP_USER_ENDPOINT = OIDC_ISSUER.rstrip("/") + "/protocol/openid-connect/userinfo"
if _op_jwks:
    OIDC_OP_JWKS_ENDPOINT = _op_jwks
else:
    jwks_fallback = env("OIDC_JWKS_URL", default=None)
    if jwks_fallback:
        OIDC_OP_JWKS_ENDPOINT = jwks_fallback

# Default OIDC scopes for browser SSO
OIDC_RP_SCOPES = env("OIDC_RP_SCOPES", default="openid email profile")

# Optional: sync case memberships from Keycloak group claims
OIDC_SYNC_MEMBERSHIPS = env.bool("OIDC_SYNC_MEMBERSHIPS", default=False)
OIDC_CASE_GROUP_PREFIX = env("OIDC_CASE_GROUP_PREFIX", default="case:")
OIDC_CASE_GROUP_SEPARATOR = env("OIDC_CASE_GROUP_SEPARATOR", default=":")
OIDC_CASE_DEFAULT_ROLE = env("OIDC_CASE_DEFAULT_ROLE", default="REVIEWER")
