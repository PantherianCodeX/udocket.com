# pyright: strict

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.db.models import Model

from apps.platform.accounts.models import Organization, OrganizationMembership, User
from apps.platform.accounts.utils import sync_user_access_flags
from packages.common.json_utils import load_json_value

logger = logging.getLogger(__name__)


def _clean_env(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class SuperuserConfig:
    username: str
    email: str
    password: str
    reset_password: bool


@dataclass(frozen=True)
class OrganizationConfig:
    name: str
    display_name: str | None
    contact_email: str | None
    attach_superuser: bool


@dataclass(frozen=True)
class BootstrapDefaults:
    enabled: bool
    superuser_username: str | None
    superuser_email: str | None
    superuser_password: str | None
    superuser_reset_password: bool | None
    organization_name: str | None
    organization_display_name: str | None
    organization_contact_email: str | None
    organization_attach_superuser: bool | None
    import_presets: bool


@dataclass(frozen=True)
class BootstrapConfig:
    enabled: bool
    superuser: SuperuserConfig | None
    organization: OrganizationConfig | None
    import_presets: bool

    @classmethod
    def from_env(cls) -> BootstrapConfig:
        defaults = _load_bootstrap_defaults()

        enabled = _parse_bool(
            os.environ.get("PLATFORM_BOOTSTRAP_ENABLED"),
            default=defaults.enabled,
        )

        superuser_username = (
            _clean_env(os.environ.get("DJANGO_SUPERUSER_USERNAME")) or defaults.superuser_username
        )
        superuser_password = (
            _clean_env(os.environ.get("DJANGO_SUPERUSER_PASSWORD")) or defaults.superuser_password
        )
        superuser_email = (
            _clean_env(os.environ.get("DJANGO_SUPERUSER_EMAIL"))
            or defaults.superuser_email
            or "admin@example.com"
        )
        reset_password = _parse_bool(
            os.environ.get("PLATFORM_BOOTSTRAP_SUPERUSER_RESET_PASSWORD"),
            default=defaults.superuser_reset_password
            if defaults.superuser_reset_password is not None
            else True,
        )
        superuser_config: SuperuserConfig | None = None
        if superuser_username and superuser_password:
            superuser_config = SuperuserConfig(
                username=superuser_username,
                email=superuser_email,
                password=superuser_password,
                reset_password=reset_password,
            )

        org_name = (
            _clean_env(os.environ.get("PLATFORM_BOOTSTRAP_ORG_NAME"))
            or defaults.organization_name
            or "Demo Organization"
        )
        org_display = (
            _clean_env(os.environ.get("PLATFORM_BOOTSTRAP_ORG_DISPLAY_NAME"))
            or defaults.organization_display_name
            or org_name
        )
        org_email = (
            _clean_env(os.environ.get("PLATFORM_BOOTSTRAP_ORG_CONTACT_EMAIL"))
            or defaults.organization_contact_email
        )
        attach_superuser = _parse_bool(
            os.environ.get("PLATFORM_BOOTSTRAP_ATTACH_SUPERUSER"),
            default=defaults.organization_attach_superuser
            if defaults.organization_attach_superuser is not None
            else True,
        )
        organization_config = OrganizationConfig(
            name=org_name,
            display_name=org_display,
            contact_email=org_email,
            attach_superuser=attach_superuser,
        )

        import_presets = _parse_bool(
            os.environ.get("PLATFORM_BOOTSTRAP_IMPORT_PRESETS"),
            default=defaults.import_presets,
        )

        return cls(
            enabled=enabled,
            superuser=superuser_config,
            organization=organization_config,
            import_presets=import_presets,
        )


@dataclass(frozen=True)
class BootstrapSummary:
    superuser_created: bool
    superuser_updated: bool
    organization_created: bool
    organization_updated: bool
    membership_created: bool
    membership_updated: bool
    presets_imported: bool


def bootstrap_stack(config: BootstrapConfig) -> BootstrapSummary:
    if not config.enabled:
        return BootstrapSummary(
            superuser_created=False,
            superuser_updated=False,
            organization_created=False,
            organization_updated=False,
            membership_created=False,
            membership_updated=False,
            presets_imported=False,
        )

    superuser_created = False
    superuser_updated = False
    organization_created = False
    organization_updated = False
    membership_created = False
    membership_updated = False

    user_instance: User | None = None
    organization_instance: Organization | None = None

    with transaction.atomic():
        if config.superuser is not None:
            user_instance, superuser_created, superuser_updated = _ensure_superuser(
                config.superuser
            )

        if config.organization is not None:
            organization_instance, organization_created, organization_updated = (
                _ensure_organization(config.organization)
            )

        if (
            config.organization is not None
            and config.organization.attach_superuser
            and user_instance is not None
            and organization_instance is not None
        ):
            membership_created, membership_updated = _ensure_membership(
                user_instance, organization_instance
            )
            sync_user_access_flags(user_instance)

    presets_imported = False
    if config.import_presets:
        call_command("import_presets")
        presets_imported = True

    return BootstrapSummary(
        superuser_created=superuser_created,
        superuser_updated=superuser_updated,
        organization_created=organization_created,
        organization_updated=organization_updated,
        membership_created=membership_created,
        membership_updated=membership_updated,
        presets_imported=presets_imported,
    )


def _ensure_superuser(config: SuperuserConfig) -> tuple[User, bool, bool]:
    user, created = User.typed_objects().get_or_create(
        username=config.username,
        defaults={
            "email": config.email,
            "is_staff": True,
            "is_superuser": True,
        },
    )

    if created:
        user.set_password(config.password)
        cast(Model, user).save(update_fields=["password"])

    return user, created, False


def _ensure_organization(config: OrganizationConfig) -> tuple[Organization, bool, bool]:
    organization, created = Organization.typed_objects().get_or_create(
        name=config.name,
        defaults={
            "display_name": config.display_name or config.name,
            "contact_email": config.contact_email or "",
        },
    )

    return organization, created, False


def _ensure_membership(user: User, organization: Organization) -> tuple[bool, bool]:
    _membership, created = OrganizationMembership.typed_objects().get_or_create(
        organization=organization,
        user=user,
        defaults={"role": OrganizationMembership.Role.SUPERUSER},
    )
    return created, False


def _load_bootstrap_defaults() -> BootstrapDefaults:
    config_path_env = _clean_env(os.environ.get("PLATFORM_BOOTSTRAP_CONFIG"))
    candidate_paths: list[Path] = []
    if config_path_env:
        candidate_paths.append(Path(config_path_env))
    base_dir = getattr(settings, "BASE_DIR", None)
    if isinstance(base_dir, (str, Path)):
        candidate_paths.append(Path(base_dir) / "config" / "bootstrap_defaults.json")

    for path in candidate_paths:
        try:
            if not path.exists():
                continue
            data = load_json_value(path, context=str(path))
            return _parse_defaults_payload(data)
        except Exception:
            logger.exception("Failed to load bootstrap defaults from %s", path)

    return BootstrapDefaults(
        enabled=False,
        superuser_username=None,
        superuser_email=None,
        superuser_password=None,
        superuser_reset_password=None,
        organization_name=None,
        organization_display_name=None,
        organization_contact_email=None,
        organization_attach_superuser=None,
        import_presets=True,
    )


def _parse_defaults_payload(payload: object) -> BootstrapDefaults:
    if not isinstance(payload, dict):
        raise ValueError("Bootstrap defaults payload must be an object.")

    payload_map = cast(dict[str, object], payload)

    superuser_raw = payload_map.get("superuser")
    superuser_section: dict[str, object] | None = (
        cast(dict[str, object], superuser_raw) if isinstance(superuser_raw, dict) else None
    )
    org_raw = payload_map.get("organization")
    organization_section: dict[str, object] | None = (
        cast(dict[str, object], org_raw) if isinstance(org_raw, dict) else None
    )

    def _optional_bool(value: object) -> bool | None:
        if isinstance(value, bool):
            return value
        return None

    def _optional_str(value: object) -> str | None:
        return str(value) if isinstance(value, str) and value.strip() else None

    enabled = bool(payload_map.get("enabled", False))
    import_presets = bool(payload_map.get("import_presets", True))

    superuser_username = (
        _optional_str(superuser_section.get("username")) if superuser_section else None
    )
    superuser_email = _optional_str(superuser_section.get("email")) if superuser_section else None
    superuser_password = (
        _optional_str(superuser_section.get("password")) if superuser_section else None
    )
    superuser_reset_password = (
        _optional_bool(superuser_section.get("reset_password")) if superuser_section else None
    )

    organization_name = (
        _optional_str(organization_section.get("name")) if organization_section else None
    )
    organization_display_name = (
        _optional_str(organization_section.get("display_name")) if organization_section else None
    )
    organization_contact_email = (
        _optional_str(organization_section.get("contact_email")) if organization_section else None
    )
    organization_attach_superuser = (
        _optional_bool(organization_section.get("attach_superuser"))
        if organization_section
        else None
    )

    return BootstrapDefaults(
        enabled=enabled,
        superuser_username=superuser_username,
        superuser_email=superuser_email,
        superuser_password=superuser_password,
        superuser_reset_password=superuser_reset_password,
        organization_name=organization_name,
        organization_display_name=organization_display_name,
        organization_contact_email=organization_contact_email,
        organization_attach_superuser=organization_attach_superuser,
        import_presets=import_presets,
    )
