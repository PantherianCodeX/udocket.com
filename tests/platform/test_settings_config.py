from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

import config.settings as settings_module
from config.settings import Settings, _collect_secret_file_values

ALL_ENV_KEYS = tuple(Settings.model_fields.keys())
FALLBACK_STORAGE_ROOT = Path(settings_module.__file__).resolve().parents[1] / "storage"


@pytest.fixture
def configure_env(monkeypatch: pytest.MonkeyPatch):
    def _configure(**overrides: Any) -> dict[str, Any]:
        for key in ALL_ENV_KEYS:
            monkeypatch.delenv(key, raising=False)
            monkeypatch.delenv(f"{key}_FILE", raising=False)
        monkeypatch.delenv("UDOCKET_SECRETS_DIR", raising=False)
        monkeypatch.delenv("SECRETS_DIR", raising=False)
        for key, value in overrides.items():
            monkeypatch.setenv(key, str(value))
        return overrides

    return _configure


def test_secret_key_loaded_from_file_and_env_override(tmp_path: Path, configure_env) -> None:
    secret_path = tmp_path / "django_secret"
    secret_path.write_text("file-secret", encoding="utf-8")

    configure_env(STORAGE_ROOT=tmp_path / "storage", DJANGO_SECRET_KEY_FILE=secret_path)
    settings_from_file = Settings()
    assert settings_from_file.DJANGO_SECRET_KEY.get_secret_value() == "file-secret"

    configure_env(
        STORAGE_ROOT=tmp_path / "storage_env",
        DJANGO_SECRET_KEY_FILE=secret_path,
        DJANGO_SECRET_KEY="env-secret",
    )
    settings_from_env = Settings()
    assert settings_from_env.DJANGO_SECRET_KEY.get_secret_value() == "env-secret"


def test_secrets_dir_populates_missing_values(tmp_path: Path, configure_env) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "django_secret_key").write_text("dir-secret", encoding="utf-8")

    configure_env(STORAGE_ROOT=tmp_path / "storage", UDOCKET_SECRETS_DIR=secrets_dir)
    settings_from_dir = Settings()
    assert settings_from_dir.DJANGO_SECRET_KEY.get_secret_value() == "dir-secret"


def test_database_defaults_to_sqlite_under_storage_root(tmp_path: Path, configure_env) -> None:
    storage_root = tmp_path / "storage"
    configure_env(STORAGE_ROOT=storage_root)
    settings_default_db = Settings()
    expected_db = f"sqlite:///{storage_root / 'udocket.db'}"
    assert settings_default_db.DATABASE_URL == expected_db
    assert settings_default_db.storage.media_root() == storage_root / "media"


def test_database_config_fallbacks_to_sqlite(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, configure_env) -> None:
    storage_root = tmp_path / "storage"
    configure_env(
        STORAGE_ROOT=storage_root,
        DATABASE_URL="postgresql://user:pass@invalid.invalid:5432/udocket",
        ALLOW_SQLITE_DEV_FALLBACK=1,
    )

    settings_with_fallback = Settings()

    class DummyParser:
        def db_url_config(self, value: str) -> dict[str, Any]:
            return {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "udocket",
                "HOST": "invalid.invalid",
                "PORT": 5432,
            }

    config = settings_with_fallback.database.as_django_config(DummyParser(), running_tests=False)
    default_db = config["default"]
    assert default_db["ENGINE"] == "django.db.backends.sqlite3"
    assert Path(default_db["NAME"]).name == "udocket_django.db"
    assert Path(default_db["NAME"]).parent == storage_root


def test_database_config_prefers_test_url(tmp_path: Path, configure_env) -> None:
    storage_root = tmp_path / "storage"
    test_db = tmp_path / "test.sqlite3"
    configure_env(
        STORAGE_ROOT=storage_root,
        DATABASE_URL="postgresql://user:pass@host:5432/udocket",
        TEST_DATABASE_URL=f"sqlite:///{test_db}",
    )

    settings_for_tests = Settings()

    class DummyParser:
        def db_url_config(self, value: str) -> dict[str, Any]:
            return {"ENGINE": "django.db.backends.postgresql", "NAME": "udocket"}

    config = settings_for_tests.database.as_django_config(DummyParser(), running_tests=True)
    default_db = config["default"]
    assert default_db["ENGINE"] == "django.db.backends.sqlite3"
    assert default_db["NAME"] == str(test_db)


def test_jobs_ui_config_normalizes_choices(tmp_path: Path, configure_env) -> None:
    configure_env(
        STORAGE_ROOT=tmp_path / "storage",
        PLATFORM_UI_JOB_LIMIT_CHOICES="[200, 50, -10, 0]",
        PLATFORM_UI_JOB_DEFAULT_LIMIT="75",
    )
    settings_with_limits = Settings()
    jobs_ui = settings_with_limits.jobs_ui
    assert jobs_ui.limit_choices == (50, 200)
    assert jobs_ui.default_limit == 200


def test_invalid_region_rejected(tmp_path: Path, configure_env) -> None:
    configure_env(STORAGE_ROOT=tmp_path / "storage", AZURE_SPEECH_REGION="uswest")
    with pytest.raises(ValidationError):
        Settings()


def test_prod_requires_secret_key(tmp_path: Path, configure_env) -> None:
    configure_env(STORAGE_ROOT=tmp_path / "storage", DJANGO_DEBUG="0")
    with pytest.raises(ValidationError):
        Settings()


def test_oidc_endpoints_build_from_issuer(tmp_path: Path, configure_env) -> None:
    configure_env(STORAGE_ROOT=tmp_path / "storage", OIDC_ISSUER="https://idp.example.ca/auth")
    settings_with_oidc = Settings()
    oidc = settings_with_oidc.oidc
    assert oidc.authorization_endpoint() == "https://idp.example.ca/auth/protocol/openid-connect/auth"
    assert oidc.token_endpoint() == "https://idp.example.ca/auth/protocol/openid-connect/token"
    assert oidc.userinfo_endpoint() == "https://idp.example.ca/auth/protocol/openid-connect/userinfo"
    assert oidc.jwks_endpoint() == "https://idp.example.ca/auth/protocol/openid-connect/certs"


def test_collect_secret_file_values_uses_secrets_dir(tmp_path: Path, configure_env) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "django_secret_key").write_text("secrets-dir", encoding="utf-8")

    configure_env(STORAGE_ROOT=tmp_path / "storage", UDOCKET_SECRETS_DIR=secrets_dir)
    values = _collect_secret_file_values(["DJANGO_SECRET_KEY"])
    assert values["DJANGO_SECRET_KEY"] == "secrets-dir"


def test_collect_secret_file_values_skips_when_env_present(tmp_path: Path, configure_env, monkeypatch: pytest.MonkeyPatch) -> None:
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("file-secret", encoding="utf-8")
    configure_env(
        STORAGE_ROOT=tmp_path / "storage",
        DJANGO_SECRET_KEY_FILE=secret_path,
    )
    monkeypatch.setenv("DJANGO_SECRET_KEY", "env-secret")
    values = _collect_secret_file_values(["DJANGO_SECRET_KEY"])
    assert "DJANGO_SECRET_KEY" not in values


def test_ensure_storage_root_fallback_updates_sqlite_paths(tmp_path: Path, configure_env, monkeypatch: pytest.MonkeyPatch) -> None:
    primary_root = tmp_path / "unwritable"
    original_mkdir = Path.mkdir

    def fake_mkdir(self: Path, parents: bool = False, exist_ok: bool = False) -> None:
        if self == primary_root:
            raise PermissionError("denied")
        original_mkdir(self, parents=parents, exist_ok=exist_ok)

    configure_env(STORAGE_ROOT=primary_root)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir, raising=False)

    settings_with_fallback = Settings()
    assert settings_with_fallback.STORAGE_ROOT == FALLBACK_STORAGE_ROOT
    assert settings_with_fallback.DATABASE_URL == f"sqlite:///{FALLBACK_STORAGE_ROOT / 'udocket.db'}"
