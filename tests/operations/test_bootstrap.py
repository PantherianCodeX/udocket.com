# pyright: strict

from __future__ import annotations

from pathlib import Path

import json
import os
import pytest

from django.contrib.auth import get_user_model

from apps.platform.accounts.models import Organization, OrganizationMembership
from apps.platform.operations.bootstrap import (
    BootstrapConfig,
    OrganizationConfig,
    SuperuserConfig,
    bootstrap_stack,
)


def _clear_bootstrap_env(monkeypatch: pytest.MonkeyPatch) -> None:
    keys = [
        "PLATFORM_BOOTSTRAP_ENABLED",
        "PLATFORM_BOOTSTRAP_CONFIG",
        "DJANGO_SUPERUSER_USERNAME",
        "DJANGO_SUPERUSER_PASSWORD",
        "DJANGO_SUPERUSER_EMAIL",
        "PLATFORM_BOOTSTRAP_SUPERUSER_RESET_PASSWORD",
        "PLATFORM_BOOTSTRAP_ORG_NAME",
        "PLATFORM_BOOTSTRAP_ORG_DISPLAY_NAME",
        "PLATFORM_BOOTSTRAP_ORG_CONTACT_EMAIL",
        "PLATFORM_BOOTSTRAP_ATTACH_SUPERUSER",
        "PLATFORM_BOOTSTRAP_IMPORT_PRESETS",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_bootstrap_config_defaults_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bootstrap_env(monkeypatch)
    defaults_path = tmp_path / "bootstrap.json"
    defaults_payload = {
        "enabled": True,
        "superuser": {
            "username": "file-admin",
            "password": "file-secret",
            "email": "file@example.com",
            "reset_password": False,
        },
        "organization": {
            "name": "File Org",
            "display_name": "File Org Display",
            "contact_email": "contact@example.com",
            "attach_superuser": False,
        },
        "import_presets": False,
    }
    defaults_path.write_text(json.dumps(defaults_payload), encoding="utf-8")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_CONFIG", str(defaults_path))

    config = BootstrapConfig.from_env()

    assert config.enabled is True
    assert config.import_presets is False
    assert config.superuser is not None
    assert config.superuser.username == "file-admin"
    assert config.superuser.password == "file-secret"
    assert config.superuser.email == "file@example.com"
    assert config.superuser.reset_password is False

    assert config.organization is not None
    assert config.organization.name == "File Org"
    assert config.organization.display_name == "File Org Display"
    assert config.organization.contact_email == "contact@example.com"
    assert config.organization.attach_superuser is False


def test_bootstrap_config_env_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bootstrap_env(monkeypatch)
    defaults_path = tmp_path / "bootstrap.json"
    defaults_path.write_text(json.dumps({"enabled": False}), encoding="utf-8")

    monkeypatch.setenv("PLATFORM_BOOTSTRAP_CONFIG", str(defaults_path))
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ENABLED", "1")
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "env-admin")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "env-secret")
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "env@example.com")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_SUPERUSER_RESET_PASSWORD", "1")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ORG_NAME", "Env Org")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ORG_DISPLAY_NAME", "Env Org Display")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_ATTACH_SUPERUSER", "1")
    monkeypatch.setenv("PLATFORM_BOOTSTRAP_IMPORT_PRESETS", "0")

    config = BootstrapConfig.from_env()

    assert config.enabled is True
    assert config.import_presets is False
    assert config.superuser is not None
    assert config.superuser.username == "env-admin"
    assert config.superuser.password == "env-secret"
    assert config.superuser.email == "env@example.com"
    assert config.superuser.reset_password is True
    assert config.organization is not None
    assert config.organization.name == "Env Org"
    assert config.organization.display_name == "Env Org Display"
    assert config.organization.attach_superuser is True


@pytest.mark.django_db
def test_bootstrap_stack_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bootstrap_env(monkeypatch)

    config = BootstrapConfig(
        enabled=True,
        superuser=SuperuserConfig(
            username="bootstrap-admin",
            email="bootstrap@example.com",
            password="initial-secret",
            reset_password=True,
        ),
        organization=OrganizationConfig(
            name="Bootstrap Org",
            display_name="Bootstrap Org",
            contact_email="org@example.com",
            attach_superuser=True,
        ),
        import_presets=False,
    )

    summary_first = bootstrap_stack(config)
    assert summary_first.superuser_created is True
    assert summary_first.organization_created is True
    assert summary_first.membership_created is True
    assert summary_first.superuser_updated is False
    assert summary_first.organization_updated is False
    assert summary_first.membership_updated is False
    assert summary_first.presets_imported is False

    user_model = get_user_model()
    user = user_model.objects.get(username="bootstrap-admin")
    assert user.is_superuser is True
    assert user.is_staff is True

    organization = Organization.objects.get(name="Bootstrap Org")
    membership = OrganizationMembership.objects.get(user=user, organization=organization)
    assert membership.role == OrganizationMembership.Role.SUPERUSER

    # Apply manual changes that bootstrap should not override.
    organization.display_name = "Bootstrap Org Updated"
    organization.save(update_fields=["display_name"])
    membership.role = OrganizationMembership.Role.ADMIN
    membership.save(update_fields=["role"])
    user.email = "bootstrap+custom@example.com"
    user.set_password("custom-secret")
    user.save(update_fields=["email", "password"])

    # Second run should skip updates but still succeed.
    config_repeat = BootstrapConfig(
        enabled=True,
        superuser=SuperuserConfig(
            username="bootstrap-admin",
            email="bootstrap@example.com",
            password="new-secret",
            reset_password=True,
        ),
        organization=OrganizationConfig(
            name="Bootstrap Org",
            display_name="Bootstrap Org Updated",
            contact_email="org@example.com",
            attach_superuser=True,
        ),
        import_presets=False,
    )

    summary_second = bootstrap_stack(config_repeat)
    assert summary_second.superuser_created is False
    assert summary_second.superuser_updated is False
    assert summary_second.organization_created is False
    assert summary_second.organization_updated is False
    assert summary_second.membership_created is False
    assert summary_second.membership_updated is False

    organization.refresh_from_db()
    assert organization.display_name == "Bootstrap Org Updated"

    user.refresh_from_db()
    assert user.check_password("custom-secret") is True
    assert user.email == "bootstrap+custom@example.com"

    membership.refresh_from_db()
    assert membership.role == OrganizationMembership.Role.ADMIN
