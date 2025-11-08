# pyright: strict

from __future__ import annotations

import json
import os
import socket
from collections.abc import Iterable as IterableABC, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Sequence, cast

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource, PydanticBaseSettingsSource

from packages.common.env import load_env_defaults


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("APP_ROOT", str(REPO_ROOT))
DEFAULT_APP_ROOT = Path(os.environ.get("APP_ROOT", str(REPO_ROOT))).expanduser()
DEFAULT_STORAGE_ROOT = DEFAULT_APP_ROOT / "storage"
FALLBACK_STORAGE_ROOT = REPO_ROOT / "storage"

load_env_defaults(
    env_var="UDOCKET_ENV_FILE",
    default_paths=(
        REPO_ROOT / ".env",
        REPO_ROOT / "apps" / "platform" / ".env",
    ),
)


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError:
        return None
    return data.strip()

def _parse_env_file(path: Path, encoding: str | None = None) -> dict[str, str]:
    try:
        text = path.read_text(encoding=encoding or "utf-8")
    except OSError:
        return {}
    overrides: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        overrides[key.strip()] = value.strip()
    return overrides

def _collect_iter_items(value: IterableABC[object]) -> list[str]:
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return result


def _split_env_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, IterableABC) and not isinstance(value, (str, bytes, bytearray)):
        iterable_value = cast(IterableABC[object], value)
        return _collect_iter_items(iterable_value)
    text = str(value).strip()
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip()]


def _json_or_split_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, IterableABC) and not isinstance(value, (str, bytes, bytearray)):
        iterable_value = cast(IterableABC[object], value)
        return _collect_iter_items(iterable_value)
    text = str(value).strip()
    if not text:
        return []
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return _split_env_list(text)
    if isinstance(loaded, str):
        return _split_env_list(loaded)
    if isinstance(loaded, IterableABC) and not isinstance(loaded, (str, bytes, bytearray)):
        iterable_loaded = cast(IterableABC[object], loaded)
        return _collect_iter_items(iterable_loaded)
    return _split_env_list(text)


def _json_or_split_int_list(value: object) -> list[int]:
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


def _json_or_mapping(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[object, object], value)
        items = [(str(k), str(v)) for k, v in mapping_value.items()]
    else:
        text = str(value).strip()
        if not text:
            return {}
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            pairs: list[tuple[str, str]] = []
            for part in text.split(","):
                key, sep, val = part.partition(":")
                if not sep:
                    key, sep, val = part.partition("=")
                key = key.strip()
                val = val.strip()
                if key and val:
                    pairs.append((key, val))
            items = pairs
        else:
            if isinstance(loaded, Mapping):
                mapping_loaded = cast(Mapping[object, object], loaded)
                items = [(str(k), str(v)) for k, v in mapping_loaded.items()]
            elif isinstance(loaded, IterableABC):
                pairs_list: list[tuple[str, str]] = []
                iterable_loaded = cast(IterableABC[object], loaded)
                for entry in iterable_loaded:
                    if isinstance(entry, Mapping):
                        entry_map = cast(Mapping[object, object], entry)
                        for k, v in entry_map.items():
                            pairs_list.append((str(k), str(v)))
                    elif isinstance(entry, (list, tuple)):
                        seq_entry = cast(Sequence[object], entry)
                        if len(seq_entry) == 2:
                            first_obj = seq_entry[0]
                            second_obj = seq_entry[1]
                            pairs_list.append((str(first_obj), str(second_obj)))
                items = pairs_list
            else:
                items = []
    normalized: dict[str, str] = {}
    for key, val in items:
        norm_key = key.strip().lower()
        norm_val = val.strip().upper()
        if norm_key and norm_val:
            normalized[norm_key] = norm_val
    return normalized


def _normalize_redis_url(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "://" in text or text.startswith("unix://"):
        return text
    return f"redis://{text}"


def _as_bool(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_mkdir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    if not path.exists():
        return False
    if not os.access(path, os.W_OK | os.X_OK):
        return False
    return True


def _coerce_path(value: Path | str | None, default: Path) -> Path:
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text:
            return Path(text).expanduser()
    return default


def _settings_field_info(settings_cls: type[BaseSettings]) -> dict[str, FieldInfo]:
    raw_fields = getattr(settings_cls, "model_fields", {})
    if isinstance(raw_fields, Mapping):
        mapping_fields = cast(Mapping[object, object], raw_fields)
        result: dict[str, FieldInfo] = {}
        for key, info in mapping_fields.items():
            if isinstance(key, str) and isinstance(info, FieldInfo):
                result[key] = info
        return result
    return {}


def _settings_field_default(settings_cls: type[BaseSettings], field_name: str, fallback: Any = None) -> Any:
    fields = _settings_field_info(settings_cls)
    info = fields.get(field_name)
    if info is None:
        return fallback
    default_value = getattr(info, "default", fallback)
    if default_value is None:
        return fallback
    if default_value.__class__.__name__ == "PydanticUndefinedType":
        return fallback
    return default_value


def _normalize_storage_values(
    storage_root: Path | None,
    database_url: str,
    test_database_url: str | None,
) -> tuple[Path, str, str | None]:
    normalized_root = _coerce_path(storage_root, DEFAULT_STORAGE_ROOT)
    normalized_db = database_url
    normalized_test_db = test_database_url

    if not _safe_mkdir(normalized_root):
        fallback_root = FALLBACK_STORAGE_ROOT
        if _safe_mkdir(fallback_root):
            normalized_root = fallback_root
            if database_url.startswith("sqlite:///"):
                db_name = Path(database_url.replace("sqlite:///", "", 1)).name or "udocket.db"
                normalized_db = f"sqlite:///{fallback_root / db_name}"
            if test_database_url and test_database_url.startswith("sqlite:///"):
                test_name = Path(test_database_url.replace("sqlite:///", "", 1)).name or "test_udocket.db"
                normalized_test_db = f"sqlite:///{fallback_root / test_name}"

    return normalized_root, normalized_db, normalized_test_db


def _ensure_sqlite_parent(db_url: str) -> None:
    if not db_url.startswith("sqlite:///"):
        return
    path_str = db_url.replace("sqlite:///", "", 1)
    path = Path(path_str)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return


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
    organization_claim: str
    organization_id_field: str
    organization_name_field: str
    organization_roles_field: str
    organization_default_role: str
    organization_role_map: dict[str, str]
    case_memberships_claim: str
    case_id_field: str
    case_role_field: str
    case_role_map: dict[str, str]
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

    def __init__(self, **values: Any) -> None:
        env_file_value = values.get("_env_file")
        env_encoding = values.get("_env_file_encoding")
        if env_file_value is not None:
            env_path = Path(str(env_file_value))
            overrides = _parse_env_file(env_path, encoding=env_encoding)
            for key, raw in overrides.items():
                if key not in values:
                    values[key] = raw
        super().__init__(**values)

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
            STR_LIST_FIELDS: ClassVar[set[str]] = {"DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS"}
            INT_LIST_FIELDS: ClassVar[set[str]] = {"PLATFORM_UI_JOB_LIMIT_CHOICES"}

            def __init__(self, settings_cls: type[BaseSettings], **kwargs: Any) -> None:
                super().__init__(settings_cls, **kwargs)

            def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
                if field_name in self.STR_LIST_FIELDS:
                    return _json_or_split_str_list(str(value))
                if field_name in self.INT_LIST_FIELDS:
                    return _json_or_split_int_list(str(value))
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
            STR_LIST_FIELDS: ClassVar[set[str]] = _CsvEnvSource.STR_LIST_FIELDS
            INT_LIST_FIELDS: ClassVar[set[str]] = _CsvEnvSource.INT_LIST_FIELDS

            def __init__(self, settings_cls: type[BaseSettings], **kwargs: Any) -> None:
                super().__init__(settings_cls, **kwargs)

            def decode_complex_value(self, field_name: str, field: Any, value: Any) -> Any:
                if field_name in self.STR_LIST_FIELDS:
                    return _json_or_split_str_list(str(value))
                if field_name in self.INT_LIST_FIELDS:
                    return _json_or_split_int_list(str(value))
                return super().decode_complex_value(field_name, field, value)

            def __call__(self) -> dict[str, Any]:
                data = super().__call__()
                try:
                    env_vars = getattr(self, "env_vars", {}) or {}
                except Exception:
                    env_vars = {}
                if env_vars:
                    for key, raw in env_vars.items():
                        if not isinstance(key, str):
                            continue
                        normalized = key.upper()
                        data[normalized] = raw
                return data

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
        sources_tuple = (
            init_settings,
            _CsvEnvSource(settings_cls, **env_kwargs),
            _CsvDotenvSource(settings_cls, **dotenv_kwargs),
            file_secret_settings,
        )
        return sources_tuple

    # Azure Speech + Agents
    AZURE_SPEECH_KEY: SecretStr = Field(default=SecretStr("dev-placeholder"))
    AZURE_SPEECH_REGION: str = "canadacentral"
    LANGUAGE: str = "en-CA"

    # Paths
    APP_ROOT: Path | None = None
    STORAGE_ROOT: Path | None = None
    MAX_UPLOAD_MB: int = 500

    # Database
    DATABASE_URL: str = "sqlite:///__AUTO__"
    ALLOW_SQLITE_DEV_FALLBACK: bool = True
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
    OIDC_SYNC_MEMBERSHIPS: bool = True
    OIDC_ORG_CLAIM: str = "organizations"
    OIDC_ORG_ID_FIELD: str = "id"
    OIDC_ORG_NAME_FIELD: str = "name"
    OIDC_ORG_ROLES_FIELD: str = "roles"
    OIDC_ORG_DEFAULT_ROLE: str = "MEMBER"
    OIDC_ORG_ROLE_MAP: dict[str, str] = Field(
        default_factory=lambda: {
            "admin": "ADMIN",
            "manager": "MANAGER",
            "member": "MEMBER",
            "owner": "ADMIN",
            "superuser": "SUPERUSER",
        }
    )
    OIDC_CASE_MEMBERSHIPS_CLAIM: str = "case_memberships"
    OIDC_CASE_ID_FIELD: str = "id"
    OIDC_CASE_ROLE_FIELD: str = "role"
    OIDC_CASE_ROLE_MAP: dict[str, str] = Field(
        default_factory=lambda: {
            "owner": "OWNER",
            "contributor": "CONTRIBUTOR",
            "reviewer": "REVIEWER",
            "admin": "ADMIN",
            "superuser": "SUPERUSER",
            "auditor": "AUDITOR",
            "external": "EXTERNAL",
            "client": "CLIENT",
        }
    )
    OIDC_CASE_DEFAULT_ROLE: str = "REVIEWER"

    @field_validator("AZURE_SPEECH_REGION")
    @classmethod
    def validate_region(cls, value: str) -> str:
        allowed = {"canadacentral", "canadaeast"}
        if value not in allowed:
            raise ValueError("AZURE_SPEECH_REGION must be canadacentral or canadaeast")
        return value

    @field_validator("DJANGO_ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS", mode="before")
    @classmethod
    def parse_csv_lists(cls, value: object, info: ValidationInfo) -> list[str]:
        items = _json_or_split_str_list(value)
        if info.field_name == "DJANGO_ALLOWED_HOSTS":
            return items or ["*"]
        return items

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
 
    @field_validator("OIDC_ORG_ROLE_MAP", "OIDC_CASE_ROLE_MAP", mode="before")
    @classmethod
    def parse_role_maps(cls, value: Any) -> dict[str, str]:
        return _json_or_mapping(value)

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
        field_name = info.field_name or ""
        default_raw = _settings_field_default(cls, field_name, 0) if field_name else 0
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = int(default_raw) if default_raw is not None else 0
        if parsed < 0:
            return int(default_raw) if default_raw is not None else 0
        return parsed

    @model_validator(mode="before")
    @classmethod
    def apply_secret_files(cls, data: Any) -> dict[str, Any]:
        field_map = _settings_field_info(cls)
        if data is None:
            data_dict: dict[str, Any] = {}
        elif isinstance(data, Mapping):
            mapping_data = cast(Mapping[str, Any], data)
            data_dict = dict(mapping_data)
        else:
            data_iter = cast(IterableABC[tuple[str, Any]], data)
            data_dict = dict(data_iter)

        file_values = _collect_secret_file_values(field_map.keys())
        for key, value in file_values.items():
            data_dict.setdefault(key, value)

        app_root_value = data_dict.get("APP_ROOT")
        if isinstance(app_root_value, Path):
            app_root = app_root_value
        elif isinstance(app_root_value, str) and app_root_value.strip():
            app_root = Path(app_root_value.strip()).expanduser()
        else:
            app_root = DEFAULT_APP_ROOT
        data_dict["APP_ROOT"] = app_root

        storage_root_value = data_dict.get("STORAGE_ROOT")
        if isinstance(storage_root_value, Path):
            storage_root = storage_root_value
        elif isinstance(storage_root_value, str) and storage_root_value.strip():
            storage_root = Path(storage_root_value.strip()).expanduser()
        else:
            storage_root = app_root / "storage"
        data_dict["STORAGE_ROOT"] = storage_root

        db_url_value = data_dict.get("DATABASE_URL")
        if isinstance(db_url_value, str):
            db_url = db_url_value
        else:
            db_url = "sqlite:///__AUTO__"
        allow_sqlite_raw = data_dict.get("ALLOW_SQLITE_DEV_FALLBACK")
        if allow_sqlite_raw is None:
            allow_sqlite_raw = _settings_field_default(cls, "ALLOW_SQLITE_DEV_FALLBACK", False)
        allow_sqlite = _as_bool(allow_sqlite_raw, default=False)
        if db_url == "sqlite:///__AUTO__":
            if allow_sqlite:
                data_dict["DATABASE_URL"] = f"sqlite:///{storage_root / 'udocket.db'}"
            else:
                raise ValueError(
                    "DATABASE_URL must be configured (Postgres recommended). "
                    "Set ALLOW_SQLITE_DEV_FALLBACK=1 to opt into the development SQLite fallback."
                )
        elif isinstance(db_url_value, str):
            data_dict["DATABASE_URL"] = db_url_value
        return data_dict

    @model_validator(mode="after")
    def ensure_paths(self) -> "Settings":
        updates: dict[str, Any] = {}

        normalized_redis = _normalize_redis_url(self.REDIS_URL)
        if normalized_redis != self.REDIS_URL:
            updates["REDIS_URL"] = normalized_redis

        normalized_broker = _normalize_redis_url(self.CELERY_BROKER_URL)
        if normalized_broker != self.CELERY_BROKER_URL:
            updates["CELERY_BROKER_URL"] = normalized_broker

        normalized_root, normalized_db, normalized_test_db = _normalize_storage_values(
            self.STORAGE_ROOT,
            self.DATABASE_URL,
            self.TEST_DATABASE_URL,
        )

        if normalized_root != self.STORAGE_ROOT:
            updates["STORAGE_ROOT"] = normalized_root
        if normalized_db != self.DATABASE_URL:
            updates["DATABASE_URL"] = normalized_db
        if normalized_test_db != self.TEST_DATABASE_URL:
            updates["TEST_DATABASE_URL"] = normalized_test_db

        if updates:
            for key, value in updates.items():
                setattr(self, key, value)

        self.ensure_storage_root()
        _ensure_sqlite_parent(self.DATABASE_URL)
        if self.TEST_DATABASE_URL:
            _ensure_sqlite_parent(self.TEST_DATABASE_URL)

        if not self.DJANGO_DEBUG and self.DJANGO_SECRET_KEY.get_secret_value() == "dev-insecure-secret-key":
            raise ValueError("DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is false")
        return self

    def ensure_storage_root(self) -> Path:
        from config.paths import ensure_storage_root as _ensure_root

        return _ensure_root(self)

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
        from config.paths import resolve_storage_root

        return StorageConfig(root=resolve_storage_root(self), max_upload_mb=self.MAX_UPLOAD_MB)

    @property
    def database(self) -> DatabaseConfig:
        from config.paths import resolve_storage_root

        return DatabaseConfig(
            url=self.DATABASE_URL,
            allow_sqlite_dev_fallback=self.ALLOW_SQLITE_DEV_FALLBACK,
            test_url=self.TEST_DATABASE_URL,
            storage_root=resolve_storage_root(self),
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
            organization_claim=self.OIDC_ORG_CLAIM,
            organization_id_field=self.OIDC_ORG_ID_FIELD,
            organization_name_field=self.OIDC_ORG_NAME_FIELD,
            organization_roles_field=self.OIDC_ORG_ROLES_FIELD,
            organization_default_role=self.OIDC_ORG_DEFAULT_ROLE,
            organization_role_map=dict(self.OIDC_ORG_ROLE_MAP),
            case_memberships_claim=self.OIDC_CASE_MEMBERSHIPS_CLAIM,
            case_id_field=self.OIDC_CASE_ID_FIELD,
            case_role_field=self.OIDC_CASE_ROLE_FIELD,
            case_role_map=dict(self.OIDC_CASE_ROLE_MAP),
            case_default_role=self.OIDC_CASE_DEFAULT_ROLE,
        )


def _collect_secret_file_values(field_names: IterableABC[str]) -> dict[str, str]:
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
    if "_env_file" not in env_kwargs:
        app_root = Path(os.environ.get("APP_ROOT", str(DEFAULT_APP_ROOT))).expanduser()
        platform_env = app_root / "apps" / "platform" / ".env"
        if platform_env.is_file():
            env_kwargs["_env_file"] = platform_env
            env_kwargs["_env_file_encoding"] = "utf-8"
    secrets_dir = os.environ.get("UDOCKET_SECRETS_DIR") or os.environ.get("SECRETS_DIR")
    if secrets_dir:
        secrets_path = Path(secrets_dir)
        if secrets_path.is_dir():
            env_kwargs["_secrets_dir"] = secrets_path
    return env_kwargs


def _load_settings() -> Settings:
    secret_values = _collect_secret_file_values(_settings_field_info(Settings).keys())
    env_kwargs = _build_settings_kwargs()
    combined: dict[str, Any] = {**secret_values}
    combined.update(env_kwargs)
    return Settings(**combined)


settings = _load_settings()
