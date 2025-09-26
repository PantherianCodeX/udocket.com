from __future__ import annotations

import os
import socket
from pathlib import Path
from typing import Any, Dict, Optional, cast

import environ  # type: ignore[import-not-found]


BASE_DIR = Path(__file__).resolve().parents[4]  # repo root (/app)
_environ_module: Any = environ
env = _environ_module.Env()

# Load .env from repo root, but only if present (avoid noisy log)
_env_path = BASE_DIR / ".env"
# Only auto-read .env when explicitly enabled. In Docker, compose already
# provides env vars via env_file, and in local pytest discovery we avoid
# binding to container-only values (e.g., Postgres host).
if os.environ.get("ENV_READ_DOTENV") == "1" and _env_path.exists():
    _environ_module.Env.read_env(str(_env_path))


SECRET_KEY = cast(str, env("DJANGO_SECRET_KEY", default="dev-insecure-secret-key"))
DEBUG = bool(env.bool("DJANGO_DEBUG", default=True))

ALLOWED_HOSTS = cast(list[str], env.list("DJANGO_ALLOWED_HOSTS", default=["*"]))

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


# Database: honor DATABASE_URL; default to local sqlite under storage root
default_storage = (BASE_DIR / "storage").resolve()
sr_env = cast(str, env("STORAGE_ROOT", default=str(default_storage)))
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
STORAGE_ROOT = str(storage_root)
default_sqlite_path = storage_root / "udocket_django.db"

# Robust DB config with local fallback when DATABASE_URL points to an
# unavailable path (e.g., host dev using container-oriented /app/storage).
DatabaseSettings = Dict[str, Any]

database_config: DatabaseSettings

if os.environ.get("PYTEST_CURRENT_TEST"):
    test_url = (
        os.environ.get("TEST_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{default_sqlite_path}"
    )
    if test_url.startswith("sqlite:///"):
        _sqlite_path = Path(test_url.replace("sqlite:///", "")).resolve()
        _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        database_config = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(_sqlite_path),
        }
    else:
        database_config = cast(DatabaseSettings, _environ_module.Env.db_url_config(test_url))
else:
    _db_url = env("DATABASE_URL", default=f"sqlite:///{default_sqlite_path}")
    allow_sqlite_fallback = bool(env.bool("ALLOW_SQLITE_DEV_FALLBACK", default=False))
    if isinstance(_db_url, str) and _db_url.startswith("sqlite:///"):
        _sqlite_path = Path(_db_url.replace("sqlite:///", "")).resolve()
        try:
            _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            database_config = {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(_sqlite_path),
            }
        except Exception:
            database_config = {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(default_sqlite_path),
            }
    else:
        _db_conf = cast(DatabaseSettings, env.db("DATABASE_URL", default=_db_url))
        should_fallback = False
        if allow_sqlite_fallback:
            host = cast(Optional[str], _db_conf.get("HOST"))
            port_value = _db_conf.get("PORT")
            port: Optional[int] = None
            if isinstance(port_value, int):
                port = port_value
            elif isinstance(port_value, str) and port_value.isdigit():
                port = int(port_value)
            if host:
                try:
                    socket.getaddrinfo(host, port)
                except (socket.gaierror, ValueError):
                    should_fallback = True
        if allow_sqlite_fallback and should_fallback:
            fallback_path = default_sqlite_path
            try:
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            database_config = {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": str(fallback_path),
            }
        else:
            database_config = _db_conf

DATABASES: Dict[str, DatabaseSettings] = {"default": database_config}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Organization scoping header (used by middleware to set DB session var for RLS)
ORG_HEADER_NAME = cast(str, env("ORG_HEADER_NAME", default="HTTP_X_ORGANIZATION_ID"))


LANGUAGE_CODE = cast(str, env("DJANGO_LANGUAGE_CODE", default="en-ca"))
TIME_ZONE = cast(str, env("DJANGO_TIME_ZONE", default="UTC"))
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
ChannelLayerConfig = Dict[str, Any]

_redis_url = cast(Optional[str], env("REDIS_URL", default=None))
channel_layer_config: ChannelLayerConfig
if _redis_url:
    channel_layer_config = {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [_redis_url]},
    }
else:
    channel_layer_config = {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }

CHANNEL_LAYERS: Dict[str, ChannelLayerConfig] = {"default": channel_layer_config}


# Security defaults (override in prod.py)
SECURE_SSL_REDIRECT = bool(env.bool("SECURE_SSL_REDIRECT", default=False))
SESSION_COOKIE_SECURE = bool(env.bool("SESSION_COOKIE_SECURE", default=False))
CSRF_COOKIE_SECURE = bool(env.bool("CSRF_COOKIE_SECURE", default=False))
CSRF_TRUSTED_ORIGINS = cast(list[str], env.list("CSRF_TRUSTED_ORIGINS", default=[]))
SECURE_HSTS_SECONDS = int(env.int("SECURE_HSTS_SECONDS", default=0))
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True


# Guardian object-perms
ANONYMOUS_USER_NAME = None

# Guardian backend for object permissions (warning silence)
# Enable OIDC backend only when OIDC is configured (discovery or explicit endpoints)
_oidc_enabled = bool(env("OIDC_DISCOVERY_URL", default=None) or env("OIDC_OP_TOKEN_ENDPOINT", default=None))

_base_auth_backends: tuple[str, ...] = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)
_oidc_auth_backends: tuple[str, ...] = (
    "apps.platform.accounts.auth.KeycloakOIDCBackend",
) if _oidc_enabled else tuple()

AUTHENTICATION_BACKENDS: tuple[str, ...] = _base_auth_backends + _oidc_auth_backends


# Celery
CELERY_BROKER_URL = cast(
    str,
    env(
        "CELERY_BROKER_URL",
        default=env("REDIS_URL", default="redis://localhost:6379/1"),
    ),
)
CELERY_RESULT_BACKEND = cast(str, env("CELERY_RESULT_BACKEND", default="django-db"))
CELERY_TASK_ALWAYS_EAGER = bool(env.bool("CELERY_TASK_ALWAYS_EAGER", default=False))
CELERY_TASK_TIME_LIMIT = int(env.int("CELERY_TASK_TIME_LIMIT", default=7200))
CELERY_TASK_SOFT_TIME_LIMIT = int(env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=7100))

# Persist Celery beat schedule under storage/runtime/celery/
celery_runtime_dir = storage_root / "runtime" / "celery"
try:
    celery_runtime_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
CELERY_BEAT_SCHEDULE_FILENAME = str(celery_runtime_dir / "celerybeat-schedule")

# Logging configuration: rely on propagation so modules inherit handler wiring
LoggerLevelDefaults = Dict[str, tuple[str, str]]

_LOGGER_LEVEL_DEFAULTS: LoggerLevelDefaults = {
    "apps.platform": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "apps.platform.accounts": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "apps.platform.accounts.auth": ("AUTH_LOG_LEVEL", "INFO"),
    "apps.platform.operations": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "apps.platform.operations.llm": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "apps.platform.jobs": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "apps.platform.ui": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "udocket": ("PLATFORM_LOG_LEVEL", "DEBUG"),
    "udocket.azure.client": ("AZURE_LOG_LEVEL", "INFO"),
    "azure": ("AZURE_LOG_LEVEL", "WARNING"),
    "langchain": ("LANGCHAIN_LOG_LEVEL", "INFO"),
    "langchain_core": ("LANGCHAIN_LOG_LEVEL", "INFO"),
    "langgraph": ("LANGCHAIN_LOG_LEVEL", "INFO"),
    "django.contrib.auth": ("DJANGO_AUTH_LOG_LEVEL", "INFO"),
    "mozilla_django_oidc": ("DJANGO_AUTH_LOG_LEVEL", "INFO"),
    "oauthlib": ("DJANGO_AUTH_LOG_LEVEL", "WARNING"),
    "django.request": ("DJANGO_REQUEST_LOG_LEVEL", "WARNING"),
}

LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {
        "handlers": ["console"],
        "level": cast(str, env("DJANGO_LOG_LEVEL", default="INFO")),
    },
    "loggers": {
        name: {"level": cast(str, env(env_key, default=default)), "propagate": True}
        for name, (env_key, default) in _LOGGER_LEVEL_DEFAULTS.items()
    },
}

# Azure Blob env passthrough (for batch upload convenience)
AZURE_BLOB_ACCOUNT = cast(Optional[str], env("AZURE_BLOB_ACCOUNT", default=None))
AZURE_BLOB_KEY = cast(Optional[str], env("AZURE_BLOB_KEY", default=None))
AZURE_BLOB_CONNECTION_STRING = cast(
    Optional[str], env("AZURE_BLOB_CONNECTION_STRING", default=None)
)
AZURE_BLOB_CONTAINER = cast(Optional[str], env("AZURE_BLOB_CONTAINER", default=None))
AZURE_BLOB_SAS_TTL_MIN = int(env.int("AZURE_BLOB_SAS_TTL_MIN", default=120))

# SimpleJWT (accept Keycloak JWTs via remote JWKS)
SIMPLE_JWT: Dict[str, Optional[str] | list[str]] = {
    "JWK_URL": cast(Optional[str], env("OIDC_JWKS_URL", default=None)),
    "ALGORITHMS": ["RS256"],
    "AUDIENCE": cast(Optional[str], env("OIDC_AUDIENCE", default=None)),
    "ISSUER": cast(Optional[str], env("OIDC_ISSUER", default=None)),
}

# OIDC for browser SSO (Keycloak)
OIDC_RP_CLIENT_ID = cast(Optional[str], env("OIDC_CLIENT_ID", default=None))
OIDC_RP_CLIENT_SECRET = cast(Optional[str], env("OIDC_CLIENT_SECRET", default=None))
OIDC_OP_DISCOVERY_ENDPOINT = cast(Optional[str], env("OIDC_DISCOVERY_URL", default=None))
OIDC_RP_SIGN_ALGO = cast(str, env("OIDC_RP_SIGN_ALGO", default="RS256"))
# Route login via OIDC only when enabled; otherwise use Django admin/login
LOGIN_URL = "/oidc/authenticate/" if _oidc_enabled else "/admin/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
# Development/open access toggle (bypasses auth policies when true)
PLATFORM_DEV_OPEN = bool(env.bool("PLATFORM_DEV_OPEN", default=False))

# If discovery is not set, derive OP endpoints from OIDC_ISSUER when provided
OIDC_ISSUER = cast(Optional[str], env("OIDC_ISSUER", default=None))
_op_auth = cast(Optional[str], env("OIDC_OP_AUTHORIZATION_ENDPOINT", default=None))
_op_token = cast(Optional[str], env("OIDC_OP_TOKEN_ENDPOINT", default=None))
_op_user = cast(Optional[str], env("OIDC_OP_USER_ENDPOINT", default=None))
_op_jwks = cast(Optional[str], env("OIDC_OP_JWKS_ENDPOINT", default=None))

_auth_endpoint: Optional[str] = _op_auth
if not _auth_endpoint and OIDC_ISSUER:
    _auth_endpoint = OIDC_ISSUER.rstrip("/") + "/protocol/openid-connect/auth"
if _auth_endpoint:
    OIDC_OP_AUTHORIZATION_ENDPOINT = _auth_endpoint

_token_endpoint: Optional[str] = _op_token
if not _token_endpoint and OIDC_ISSUER:
    _token_endpoint = OIDC_ISSUER.rstrip("/") + "/protocol/openid-connect/token"
if _token_endpoint:
    OIDC_OP_TOKEN_ENDPOINT = _token_endpoint

_user_endpoint: Optional[str] = _op_user
if not _user_endpoint and OIDC_ISSUER:
    _user_endpoint = OIDC_ISSUER.rstrip("/") + "/protocol/openid-connect/userinfo"
if _user_endpoint:
    OIDC_OP_USER_ENDPOINT = _user_endpoint

_jwks_endpoint: Optional[str] = _op_jwks
if not _jwks_endpoint:
    jwks_fallback = cast(Optional[str], env("OIDC_JWKS_URL", default=None))
    _jwks_endpoint = jwks_fallback
if _jwks_endpoint:
    OIDC_OP_JWKS_ENDPOINT = _jwks_endpoint

# Default OIDC scopes for browser SSO
OIDC_RP_SCOPES = cast(str, env("OIDC_RP_SCOPES", default="openid email profile"))

# Optional: sync case memberships from Keycloak group claims
OIDC_SYNC_MEMBERSHIPS = bool(env.bool("OIDC_SYNC_MEMBERSHIPS", default=False))
OIDC_CASE_GROUP_PREFIX = cast(str, env("OIDC_CASE_GROUP_PREFIX", default="case:"))
OIDC_CASE_GROUP_SEPARATOR = cast(str, env("OIDC_CASE_GROUP_SEPARATOR", default=":"))
OIDC_CASE_DEFAULT_ROLE = cast(str, env("OIDC_CASE_DEFAULT_ROLE", default="REVIEWER"))
