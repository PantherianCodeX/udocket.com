from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource, PydanticBaseSettingsSource


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    return data.strip()


def _split_env_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _json_or_split_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                result.append(text)
        return result
    text = str(value).strip()
    if not text:
        return []
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return _split_env_list(text)
    if isinstance(loaded, str):
        return _split_env_list(loaded)
    if isinstance(loaded, Iterable) and not isinstance(loaded, (str, bytes, bytearray)):
        result: list[str] = []
        for item in loaded:
            item_text = str(item).strip()
            if item_text:
                result.append(item_text)
        return result
    return _split_env_list(text)


def _json_or_split_int_list(value: Any) -> list[int]:
    items = _json_or_split_str_list(value)
    result: list[int] = []
    for item in items:
        try:
            parsed = int(item)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            result.append(parsed)
    return result


def _normalize_redis_url(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "://" in text or text.startswith("unix://"):
        return text
    return f"redis://{text}"


@dataclass(frozen=True)
class AzureSpeechConfig:
    key: SecretStr
    region: str
    language: str

    def key_value(self) -> str:
        return self.key.get_secret_value()


@dataclass(frozen=True)
class AzureBlobConfig:
    account: str | None
    key: SecretStr | None
    container: str | None
    connection_string: str | None
    sas_ttl_min: int

    def key_value(self) -> str | None:
        return self.key.get_secret_value() if self.key else None


@dataclass(frozen=True)
class AzureConfig:
    speech: AzureSpeechConfig
    blob: AzureBlobConfig


@dataclass(frozen=True)
class StorageConfig:
    root: Path
    max_upload_mb: int

    def ensure_root_exists(self) -> Path:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return self.root

    def media_root(self) -> Path:
        return self.root / "media"

    def runtime_dir(self, *parts: str) -> Path:
        base = self.root / "runtime"
        for part in parts:
            base /= part
        return base


@dataclass(frozen=True)
class DatabaseConfig:
    url: str
    allow_sqlite_dev_fallback: bool
    test_url: str | None
    storage_root: Path

    def _sqlite_config(self, raw_url: str) -> dict[str, str]:
        path_str = raw_url.replace("sqlite:///", "", 1)
        path = Path(path_str)
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": str(path)}

    def _should_fallback(self, config: dict[str, Any]) -> bool:
        host = config.get("HOST")
        port = config.get("PORT") or None
        if not host:
            return False
        try:
            socket.getaddrinfo(host, int(port) if port else None)
        except (socket.gaierror, ValueError):
            return True
        return False

    def as_django_config(self, env_parser: Any, *, running_tests: bool) -> dict[str, Any]:
        candidate_url = self.url
        if running_tests and self.test_url:
            candidate_url = self.test_url
        if candidate_url.startswith("sqlite:///"):
            return {"default": self._sqlite_config(candidate_url)}
        config = env_parser.db_url_config(candidate_url)
        if running_tests:
            return {"default": config}
        if self.allow_sqlite_dev_fallback and self._should_fallback(config):
            fallback = f"sqlite:///{self.storage_root / 'udocket_django.db'}"
            return {"default": self._sqlite_config(fallback)}
        return {"default": config}


@dataclass(frozen=True)
class DjangoConfig:
    secret_key: SecretStr
    debug: bool
    allowed_hosts: tuple[str, ...]
    org_header_name: str
    language_code: str
    time_zone: str
    secure_ssl_redirect: bool
    session_cookie_secure: bool
    csrf_cookie_secure: bool
    csrf_trusted_origins: tuple[str, ...]
    secure_hsts_seconds: int
    secure_content_type_nosniff: bool
    secure_browser_xss_filter: bool
    platform_dev_open: bool

    def secret_key_value(self) -> str:
        return self.secret_key.get_secret_value()


@dataclass(frozen=True)
class RedisConfig:
    url: str | None


@dataclass(frozen=True)
class CeleryConfig:
    broker_url: str | None
    result_backend: str
    task_always_eager: bool
    task_time_limit: int
    task_soft_time_limit: int
    redis_url: str | None

    def effective_broker_url(self) -> str:
        return self.broker_url or self.redis_url or "redis://localhost:6379/1"


@dataclass(frozen=True)
class JobsUIConfig:
    limit_choices: tuple[int, ...]
    default_limit: int

    @property
    def max_limit(self) -> int:
        return max(self.limit_choices)


@dataclass(frozen=True)
class LoggingConfig:
    root_level: str
    logger_levels: dict[str, str]


@dataclass(frozen=True)
class OIDCConfig:
    discovery_url: str | None
    issuer: str | None
    audience: str | None
    client_id: str | None
    client_secret: SecretStr | None
    jwks_url: str | None
    op_auth_endpoint: str | None
    op_token_endpoint: str | None
    op_user_endpoint: str | None
    op_jwks_endpoint: str | None
    rp_sign_algo: str
    rp_scopes: str
    sync_memberships: bool
    case_group_prefix: str
    case_group_separator: str
    case_default_role: str

    def is_enabled(self) -> bool:
        return bool(self.discovery_url or self.op_token_endpoint or self.client_id or self.issuer)

    def authorization_endpoint(self) -> str | None:
        if self.op_auth_endpoint:
            return self.op_auth_endpoint
        if self.issuer:
            return self.issuer.rstrip("/") + "/protocol/openid-connect/auth"
        return None

    def token_endpoint(self) -> str | None:
        if self.op_token_endpoint:
            return self.op_token_endpoint
        if self.issuer:
            return self.issuer.rstrip("/") + "/protocol/openid-connect/token"
        return None

    def userinfo_endpoint(self) -> str | None:
        if self.op_user_endpoint:
            return self.op_user_endpoint
        if self.issuer:
            return self.issuer.rstrip("/") + "/protocol/openid-connect/userinfo"
        return None

    def jwks_endpoint(self) -> str | None:
        if self.op_jwks_endpoint:
            return self.op_jwks_endpoint
        if self.jwks_url:
            return self.jwks_url
        if self.issuer:
            return self.issuer.rstrip("/") + "/protocol/openid-connect/certs"
        return None

    def simple_jwt(self) -> dict[str, Any]:
        return {
            "JWK_URL": self.jwks_endpoint(),
            "ALGORITHMS": ["RS256"],
            "AUDIENCE": self.audience,
            "ISSUER": self.issuer,
        }

    def client_secret_value(self) -> str | None:
        return self.client_secret.get_secret_value() if self.client_secret else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True, env_ignore_empty=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        class _CsvEnvSource(EnvSettingsSource):
            _STR_LIST_FIELDS = {"DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS"}
            _INT_LIST_FIELDS = {"PLATFORM_UI_JOB_LIMIT_CHOICES"}

            def __init__(self, settings_cls: type[BaseSettings], **kwargs: Any) -> None:
                super().__init__(settings_cls, **kwargs)

            def decode_complex_value(self, field_name: str, field: Any, value: str) -> Any:  # type: ignore[override]
                if field_name in self._STR_LIST_FIELDS:
                    return _json_or_split_str_list(value)
                if field_name in self._INT_LIST_FIELDS:
                    return _json_or_split_int_list(value)
                return super().decode_complex_value(field_name, field, value)

        env_kwargs: dict[str, Any] = {}
        for attr in (
            "case_sensitive",
            "env_prefix",
            "env_nested_delimiter",
            "env_nested_max_split",
            "env_ignore_empty",
            "env_parse_none_str",
            "env_parse_enums",
        ):
            attr_value = getattr(env_settings, attr, None)
            if attr_value is not None:
                env_kwargs[attr] = attr_value

        class _CsvDotenvSource(DotEnvSettingsSource):
            _STR_LIST_FIELDS = _CsvEnvSource._STR_LIST_FIELDS
            _INT_LIST_FIELDS = _CsvEnvSource._INT_LIST_FIELDS

            def __init__(self, settings_cls: type[BaseSettings], **kwargs: Any) -> None:
                super().__init__(settings_cls, **kwargs)

            def decode_complex_value(self, field_name: str, field: Any, value: str) -> Any:  # type: ignore[override]
                if field_name in self._STR_LIST_FIELDS:
                    return _json_or_split_str_list(value)
                if field_name in self._INT_LIST_FIELDS:
                    return _json_or_split_int_list(value)
                return super().decode_complex_value(field_name, field, value)

        dotenv_kwargs: dict[str, Any] = {}
        for attr in (
            "env_file",
            "env_file_encoding",
            "case_sensitive",
            "env_prefix",
            "env_nested_delimiter",
            "env_ignore_empty",
            "env_parse_none_str",
            "env_parse_enums",
        ):
            attr_value = getattr(dotenv_settings, attr, None)
            if attr_value is not None:
                dotenv_kwargs[attr] = attr_value

        return (
            init_settings,
            _CsvEnvSource(settings_cls, **env_kwargs),
            _CsvDotenvSource(settings_cls, **dotenv_kwargs),
            file_secret_settings,
        )

    # Azure Speech + Agents
    AZURE_SPEECH_KEY: SecretStr = Field(default=SecretStr("dev-placeholder"))
    AZURE_SPEECH_REGION: str = "canadacentral"
    LANGUAGE: str = "en-CA"

    # Storage
    STORAGE_ROOT: Path = Field(default=Path("/app/storage"))
    MAX_UPLOAD_MB: int = 500

    # Database
    DATABASE_URL: str = "sqlite:///__AUTO__"
    ALLOW_SQLITE_DEV_FALLBACK: bool = False
    TEST_DATABASE_URL: str | None = None

    # Security / files
    ALLOWED_AUDIO_MIME: str = (
        "audio/wav,audio/x-wav,audio/mpeg,audio/mp4,audio/aac,audio/ogg,audio/flac,audio/x-flac"
    )

    # Azure Blob Storage
    AZURE_BLOB_ACCOUNT: str | None = None
    AZURE_BLOB_KEY: SecretStr | None = None
    AZURE_BLOB_CONTAINER: str | None = None
    AZURE_BLOB_CONNECTION_STRING: str | None = None
    AZURE_BLOB_SAS_TTL_MIN: int = 120

    # Django app
    DJANGO_SECRET_KEY: SecretStr = Field(default=SecretStr("dev-insecure-secret-key"))
    DJANGO_DEBUG: bool = True
    DJANGO_ALLOWED_HOSTS: list[str] = Field(default_factory=lambda: ["*"])
    ORG_HEADER_NAME: str = "HTTP_X_ORGANIZATION_ID"
    DJANGO_LANGUAGE_CODE: str = "en-ca"
    DJANGO_TIME_ZONE: str = "UTC"

    SECURE_SSL_REDIRECT: bool = False
    SESSION_COOKIE_SECURE: bool = False
    CSRF_COOKIE_SECURE: bool = False
    CSRF_TRUSTED_ORIGINS: list[str] = Field(default_factory=list)
    SECURE_HSTS_SECONDS: int = 0
    SECURE_CONTENT_TYPE_NOSNIFF: bool = True
    SECURE_BROWSER_XSS_FILTER: bool = True

    PLATFORM_DEV_OPEN: bool = False

    # Logging
    DJANGO_LOG_LEVEL: str = "INFO"
    PLATFORM_LOG_LEVEL: str = "DEBUG"
    AUTH_LOG_LEVEL: str = "INFO"
    AZURE_LOG_LEVEL: str = "INFO"
    LANGCHAIN_LOG_LEVEL: str = "INFO"
    DJANGO_AUTH_LOG_LEVEL: str = "INFO"
    DJANGO_REQUEST_LOG_LEVEL: str = "WARNING"

    # Redis / Celery
    REDIS_URL: str | None = None
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str = "django-db"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_TIME_LIMIT: int = 7200
    CELERY_TASK_SOFT_TIME_LIMIT: int = 7100

    # Jobs UI
    PLATFORM_UI_JOB_LIMIT_CHOICES: list[int] = Field(default_factory=lambda: [25, 50, 100, 200])
    PLATFORM_UI_JOB_DEFAULT_LIMIT: int = 25

    # OIDC / JWT
    OIDC_DISCOVERY_URL: str | None = None
    OIDC_ISSUER: str | None = None
    OIDC_AUDIENCE: str | None = None
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: SecretStr | None = None
    OIDC_JWKS_URL: str | None = None
    OIDC_OP_AUTHORIZATION_ENDPOINT: str | None = None
    OIDC_OP_TOKEN_ENDPOINT: str | None = None
    OIDC_OP_USER_ENDPOINT: str | None = None
    OIDC_OP_JWKS_ENDPOINT: str | None = None
    OIDC_RP_SIGN_ALGO: str = "RS256"
    OIDC_RP_SCOPES: str = "openid email profile"
    OIDC_SYNC_MEMBERSHIPS: bool = False
    OIDC_CASE_GROUP_PREFIX: str = "case:"
    OIDC_CASE_GROUP_SEPARATOR: str = ":"
    OIDC_CASE_DEFAULT_ROLE: str = "REVIEWER"

    @field_validator("AZURE_SPEECH_REGION")
    @classmethod
    def validate_region(cls, value: str) -> str:
        allowed = {"canadacentral", "canadaeast"}
        if value not in allowed:
            raise ValueError("AZURE_SPEECH_REGION must be canadacentral or canadaeast")
        return value

    @field_validator("DJANGO_ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: Any) -> list[str]:
        hosts = _json_or_split_str_list(value)
        return hosts or ["*"]

    @field_validator("CSRF_TRUSTED_ORIGINS", mode="before")
    @classmethod
    def parse_csrf_origins(cls, value: Any) -> list[str]:
        return _json_or_split_str_list(value)

    @field_validator("PLATFORM_UI_JOB_LIMIT_CHOICES", mode="before")
    @classmethod
    def parse_job_limit_choices(cls, value: Any) -> list[int]:
        parsed = _json_or_split_int_list(value)
        return parsed or [25, 50, 100, 200]

    @field_validator("PLATFORM_UI_JOB_DEFAULT_LIMIT", mode="before")
    @classmethod
    def parse_job_default(cls, value: Any) -> int:
        if value is None:
            return 25
        try:
            return int(value)
        except (TypeError, ValueError):
            return 25

    @field_validator("REDIS_URL", "CELERY_BROKER_URL", mode="before")
    @classmethod
    def normalize_redis_urls(cls, value: Any) -> str | None:
        return _normalize_redis_url(value)

    @field_validator(
        "AZURE_BLOB_SAS_TTL_MIN",
        "MAX_UPLOAD_MB",
        "CELERY_TASK_TIME_LIMIT",
        "CELERY_TASK_SOFT_TIME_LIMIT",
        "SECURE_HSTS_SECONDS",
        mode="before",
    )
    @classmethod
    def ensure_int(cls, value: Any, info: ValidationInfo) -> int:
        field_name = info.field_name
        default_value = cls.model_fields[field_name].default if field_name in cls.model_fields else 0  # type: ignore[index]
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = int(default_value) if default_value is not None else 0
        if parsed < 0:
            return int(default_value) if default_value is not None else 0
        return parsed

    @model_validator(mode="before")
    @classmethod
    def apply_secret_files(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            data = dict(data or {})
        field_names = cls.model_fields.keys()
        file_values = _collect_secret_file_values(field_names)
        for key, value in file_values.items():
            data.setdefault(key, value)
        storage_root = data.get("STORAGE_ROOT", Path("/app/storage"))
        if isinstance(storage_root, str):
            storage_root = Path(storage_root)
        db_url = data.get("DATABASE_URL", "sqlite:///__AUTO__")
        if db_url == "sqlite:///__AUTO__":
            data["DATABASE_URL"] = f"sqlite:///{Path(storage_root) / 'udocket.db'}"
        return data

    @model_validator(mode="after")
    def ensure_paths(self) -> "Settings":
        self.ensure_storage_root()
        self._ensure_sqlite_parent(self.DATABASE_URL)
        if self.TEST_DATABASE_URL:
            self._ensure_sqlite_parent(self.TEST_DATABASE_URL)
        self.REDIS_URL = _normalize_redis_url(self.REDIS_URL)
        broker_normalized = _normalize_redis_url(self.CELERY_BROKER_URL)
        if broker_normalized:
            self.CELERY_BROKER_URL = broker_normalized
        if not self.DJANGO_DEBUG and self.DJANGO_SECRET_KEY.get_secret_value() == "dev-insecure-secret-key":
            raise ValueError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false")
        return self

    def ensure_storage_root(self) -> Path:
        root = self.STORAGE_ROOT
        try:
            root.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        if root.exists():
            return root
        fallback_root = Path(__file__).resolve().parents[2] / "storage"
        try:
            fallback_root.mkdir(parents=True, exist_ok=True)
        except Exception:
            return root
        self.STORAGE_ROOT = fallback_root
        if self.DATABASE_URL.startswith("sqlite:///"):
            db_name = Path(self.DATABASE_URL.replace("sqlite:///", "", 1)).name or "udocket.db"
            self.DATABASE_URL = f"sqlite:///{fallback_root / db_name}"
        if self.TEST_DATABASE_URL and self.TEST_DATABASE_URL.startswith("sqlite:///"):
            test_name = Path(self.TEST_DATABASE_URL.replace("sqlite:///", "", 1)).name or "test_udocket.db"
            self.TEST_DATABASE_URL = f"sqlite:///{fallback_root / test_name}"
        return fallback_root

    def _ensure_sqlite_parent(self, db_url: str) -> None:
        if not db_url.startswith("sqlite:///"):
            return
        path_str = db_url.replace("sqlite:///", "", 1)
        path = Path(path_str)
        if not path.is_absolute():
            path = Path.cwd() / path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @property
    def azure(self) -> AzureConfig:
        return AzureConfig(
            speech=AzureSpeechConfig(
                key=self.AZURE_SPEECH_KEY,
                region=self.AZURE_SPEECH_REGION,
                language=self.LANGUAGE,
            ),
            blob=AzureBlobConfig(
                account=self.AZURE_BLOB_ACCOUNT,
                key=self.AZURE_BLOB_KEY,
                container=self.AZURE_BLOB_CONTAINER,
                connection_string=self.AZURE_BLOB_CONNECTION_STRING,
                sas_ttl_min=self.AZURE_BLOB_SAS_TTL_MIN,
            ),
        )

    @property
    def storage(self) -> StorageConfig:
        return StorageConfig(root=self.STORAGE_ROOT, max_upload_mb=self.MAX_UPLOAD_MB)

    @property
    def database(self) -> DatabaseConfig:
        return DatabaseConfig(
            url=self.DATABASE_URL,
            allow_sqlite_dev_fallback=self.ALLOW_SQLITE_DEV_FALLBACK,
            test_url=self.TEST_DATABASE_URL,
            storage_root=self.STORAGE_ROOT,
        )

    @property
    def django(self) -> DjangoConfig:
        return DjangoConfig(
            secret_key=self.DJANGO_SECRET_KEY,
            debug=self.DJANGO_DEBUG,
            allowed_hosts=tuple(self.DJANGO_ALLOWED_HOSTS),
            org_header_name=self.ORG_HEADER_NAME,
            language_code=self.DJANGO_LANGUAGE_CODE,
            time_zone=self.DJANGO_TIME_ZONE,
            secure_ssl_redirect=self.SECURE_SSL_REDIRECT,
            session_cookie_secure=self.SESSION_COOKIE_SECURE,
            csrf_cookie_secure=self.CSRF_COOKIE_SECURE,
            csrf_trusted_origins=tuple(self.CSRF_TRUSTED_ORIGINS),
            secure_hsts_seconds=self.SECURE_HSTS_SECONDS,
            secure_content_type_nosniff=self.SECURE_CONTENT_TYPE_NOSNIFF,
            secure_browser_xss_filter=self.SECURE_BROWSER_XSS_FILTER,
            platform_dev_open=self.PLATFORM_DEV_OPEN,
        )

    @property
    def redis(self) -> RedisConfig:
        return RedisConfig(url=_normalize_redis_url(self.REDIS_URL))

    @property
    def celery(self) -> CeleryConfig:
        normalized_broker = _normalize_redis_url(self.CELERY_BROKER_URL)
        normalized_redis = _normalize_redis_url(self.REDIS_URL)
        return CeleryConfig(
            broker_url=normalized_broker,
            result_backend=self.CELERY_RESULT_BACKEND,
            task_always_eager=self.CELERY_TASK_ALWAYS_EAGER,
            task_time_limit=self.CELERY_TASK_TIME_LIMIT,
            task_soft_time_limit=self.CELERY_TASK_SOFT_TIME_LIMIT,
            redis_url=normalized_redis,
        )

    @property
    def jobs_ui(self) -> JobsUIConfig:
        choices = sorted({value for value in self.PLATFORM_UI_JOB_LIMIT_CHOICES if value > 0})
        if not choices:
            choices = [25, 50, 100, 200]
        default = self.PLATFORM_UI_JOB_DEFAULT_LIMIT
        if default not in choices:
            default = next((value for value in choices if value >= default), choices[-1])
        return JobsUIConfig(limit_choices=tuple(choices), default_limit=default)

    @property
    def logging(self) -> LoggingConfig:
        overrides = {
            "apps.platform": self.PLATFORM_LOG_LEVEL,
            "apps.platform.accounts": self.PLATFORM_LOG_LEVEL,
            "apps.platform.accounts.auth": self.AUTH_LOG_LEVEL,
            "apps.platform.operations": self.PLATFORM_LOG_LEVEL,
            "apps.platform.operations.llm": self.PLATFORM_LOG_LEVEL,
            "apps.platform.jobs": self.PLATFORM_LOG_LEVEL,
            "apps.platform.ui": self.PLATFORM_LOG_LEVEL,
            "udocket": self.PLATFORM_LOG_LEVEL,
            "udocket.azure.client": self.AZURE_LOG_LEVEL,
            "azure": self.AZURE_LOG_LEVEL,
            "langchain": self.LANGCHAIN_LOG_LEVEL,
            "langchain_core": self.LANGCHAIN_LOG_LEVEL,
            "langgraph": self.LANGCHAIN_LOG_LEVEL,
            "django.contrib.auth": self.DJANGO_AUTH_LOG_LEVEL,
            "mozilla_django_oidc": self.DJANGO_AUTH_LOG_LEVEL,
            "oauthlib": self.DJANGO_AUTH_LOG_LEVEL,
            "django.request": self.DJANGO_REQUEST_LOG_LEVEL,
        }
        return LoggingConfig(root_level=self.DJANGO_LOG_LEVEL, logger_levels=overrides)

    @property
    def oidc(self) -> OIDCConfig:
        return OIDCConfig(
            discovery_url=self.OIDC_DISCOVERY_URL,
            issuer=self.OIDC_ISSUER,
            audience=self.OIDC_AUDIENCE,
            client_id=self.OIDC_CLIENT_ID,
            client_secret=self.OIDC_CLIENT_SECRET,
            jwks_url=self.OIDC_JWKS_URL,
            op_auth_endpoint=self.OIDC_OP_AUTHORIZATION_ENDPOINT,
            op_token_endpoint=self.OIDC_OP_TOKEN_ENDPOINT,
            op_user_endpoint=self.OIDC_OP_USER_ENDPOINT,
            op_jwks_endpoint=self.OIDC_OP_JWKS_ENDPOINT,
            rp_sign_algo=self.OIDC_RP_SIGN_ALGO,
            rp_scopes=self.OIDC_RP_SCOPES,
            sync_memberships=self.OIDC_SYNC_MEMBERSHIPS,
            case_group_prefix=self.OIDC_CASE_GROUP_PREFIX,
            case_group_separator=self.OIDC_CASE_GROUP_SEPARATOR,
            case_default_role=self.OIDC_CASE_DEFAULT_ROLE,
        )


def _collect_secret_file_values(field_names: Iterable[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    env_map = os.environ
    for name in field_names:
        if name in env_map:
            continue
        file_key = f"{name}_FILE"
        file_ref = env_map.get(file_key)
        if file_ref:
            data = _read_text(Path(file_ref))
            if data is not None:
                values[name] = data
    secrets_dir_env = env_map.get("UDOCKET_SECRETS_DIR") or env_map.get("SECRETS_DIR")
    if secrets_dir_env:
        secrets_path = Path(secrets_dir_env)
        if secrets_path.is_dir():
            for name in field_names:
                if name in env_map or name in values:
                    continue
                for candidate in (name, name.lower()):
                    candidate_path = secrets_path / candidate
                    data = _read_text(candidate_path)
                    if data is not None:
                        values[name] = data
                        break
    return values


def _build_settings_kwargs() -> dict[str, Any]:
    base_dir = Path(__file__).resolve().parents[1]
    env_kwargs: dict[str, Any] = {}
    env_file_override = os.environ.get("UDOCKET_ENV_FILE")
    if env_file_override:
        env_path = Path(env_file_override)
        if env_path.is_file():
            env_kwargs["_env_file"] = env_path
            env_kwargs["_env_file_encoding"] = "utf-8"
    elif os.environ.get("ENV_READ_DOTENV") == "1":
        default_env = base_dir / ".env"
        if default_env.is_file():
            env_kwargs["_env_file"] = default_env
            env_kwargs["_env_file_encoding"] = "utf-8"
    secrets_dir = os.environ.get("UDOCKET_SECRETS_DIR") or os.environ.get("SECRETS_DIR")
    if secrets_dir:
        secrets_path = Path(secrets_dir)
        if secrets_path.is_dir():
            env_kwargs["_secrets_dir"] = secrets_path
    return env_kwargs


settings = Settings(**_collect_secret_file_values(Settings.model_fields.keys()), **_build_settings_kwargs())
