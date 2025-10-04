from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import Settings


def _make_settings(tmp_path: Path, **kwargs: Any) -> Settings:
    storage_root = tmp_path / "storage"
    return Settings(STORAGE_ROOT=storage_root, **kwargs)


def _make_env_settings(tmp_path: Path, env_content: str, **kwargs: Any) -> Settings:
    env_path = tmp_path / ".env"
    env_path.write_text(env_content, encoding="utf-8")
    storage_root = tmp_path / "storage"
    return Settings(
        STORAGE_ROOT=storage_root,
        _env_file=env_path,
        _env_file_encoding="utf-8",
        **kwargs,
    )


def test_allowed_hosts_accepts_json_array(tmp_path: Path) -> None:
    cfg = _make_settings(tmp_path, DJANGO_ALLOWED_HOSTS='["alpha.example","beta.example"]')
    assert cfg.DJANGO_ALLOWED_HOSTS == ["alpha.example", "beta.example"]


def test_allowed_hosts_defaults_when_blank(tmp_path: Path) -> None:
    cfg = _make_settings(tmp_path, DJANGO_ALLOWED_HOSTS="  ")
    assert cfg.DJANGO_ALLOWED_HOSTS == ["*"]


def test_csrf_trusted_origins_accepts_csv(tmp_path: Path) -> None:
    cfg = _make_settings(tmp_path, CSRF_TRUSTED_ORIGINS="https://a.test, https://b.test ")
    assert cfg.CSRF_TRUSTED_ORIGINS == ["https://a.test", "https://b.test"]


def test_job_limit_choices_from_json_and_property_sorting(tmp_path: Path) -> None:
    cfg = _make_settings(
        tmp_path,
        PLATFORM_UI_JOB_LIMIT_CHOICES="[200, 50, 25]",
        PLATFORM_UI_JOB_DEFAULT_LIMIT="50",
    )
    assert cfg.PLATFORM_UI_JOB_LIMIT_CHOICES == [200, 50, 25]
    assert cfg.jobs_ui.limit_choices == (25, 50, 200)
    assert cfg.jobs_ui.default_limit == 50


def test_job_limit_choices_fallback_when_empty(tmp_path: Path) -> None:
    cfg = _make_settings(tmp_path, PLATFORM_UI_JOB_LIMIT_CHOICES="[]")
    assert cfg.PLATFORM_UI_JOB_LIMIT_CHOICES == [25, 50, 100, 200]
    assert cfg.jobs_ui.limit_choices == (25, 50, 100, 200)


def test_redis_urls_normalize_strings(tmp_path: Path) -> None:
    cfg = _make_settings(
        tmp_path,
        REDIS_URL="cache.internal:6379/0",
        CELERY_BROKER_URL="redis://other-host:6380/1",
    )
    assert cfg.REDIS_URL == "redis://cache.internal:6379/0"
    assert cfg.redis.url == "redis://cache.internal:6379/0"
    assert cfg.CELERY_BROKER_URL == "redis://other-host:6380/1"
    assert cfg.celery.broker_url == "redis://other-host:6380/1"
    assert cfg.celery.redis_url == "redis://cache.internal:6379/0"


def test_dotenv_blank_allowed_hosts(tmp_path: Path) -> None:
    cfg = _make_env_settings(tmp_path, "DJANGO_ALLOWED_HOSTS=\n")
    assert cfg.DJANGO_ALLOWED_HOSTS == ["*"]


def test_dotenv_csv_allowed_hosts(tmp_path: Path) -> None:
    cfg = _make_env_settings(tmp_path, "DJANGO_ALLOWED_HOSTS=example.com, api.example.com\n")
    assert cfg.DJANGO_ALLOWED_HOSTS == ["example.com", "api.example.com"]
