from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.platform.accounts.models import Organization
from apps.platform.authorization.capabilities import DEFAULT_CAPS
from apps.platform.authorization.models import (
    PermissionPreset,
    PresetCapability,
    Role,
)


class Command(BaseCommand):
    help = "Import permission presets from YAML file and bind to roles"

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument("path", nargs="?", default="apps/platform/authorization/presets.yaml")

    def handle(self, *args, **options):  # type: ignore[override]
        path = Path(options["path"]).resolve()
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        try:
            import yaml  # type: ignore
        except Exception as e:  # pragma: no cover - dependency
            raise CommandError("PyYAML is required (pip install pyyaml)") from e
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        presets = data.get("presets") or []
        bindings = data.get("bindings") or {}

        with transaction.atomic():
            # Ensure baseline roles exist so bindings succeed on fresh databases.
            base_role_names = set(DEFAULT_CAPS.keys()) | set(bindings.keys())
            for role_name in sorted(base_role_names):
                role, created = Role.objects.get_or_create(
                    name=role_name,
                    organization=None,
                    defaults={
                        "description": f"System role: {role_name.title()}",
                        "system": True,
                    },
                )
                if not created and (role.system is False or role.description == ""):
                    role.system = True
                    if not role.description:
                        role.description = f"System role: {role_name.title()}"
                    role.save(update_fields=["system", "description"])
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Role '{role_name}' created."))

            for p in presets:
                org = None
                org_slug = p.get("organization")
                if org_slug:
                    org = Organization.objects.filter(id=org_slug).first()
                    if org is None:
                        preset_hint = p.get("name") or p.get("slug") or "UNKNOWN"
                        raise CommandError(
                            f"Preset '{preset_hint}' references missing organization '{org_slug}'"
                        )
                preset_name = p.get("name") or p.get("slug")
                if not preset_name:
                    raise CommandError("Preset entry missing 'name'.")
                preset, created = PermissionPreset.objects.get_or_create(
                    name=preset_name,
                    organization=org,
                    defaults={
                        "description": p.get("description", ""),
                        "system": True,
                    },
                )
                if not created:
                    preset.description = p.get("description", preset.description)
                    preset.system = True
                    preset.organization = org
                    preset.save(update_fields=["description", "system", "organization"])
                # Capabilities
                want_caps = set(p.get("capabilities", []) or [])
                have_caps = set(
                    PresetCapability.objects.filter(preset=preset).values_list(
                        "capability", flat=True
                    )
                )
                for c in want_caps - have_caps:
                    PresetCapability.objects.create(preset=preset, capability=c)
                PresetCapability.objects.filter(
                    preset=preset, capability__in=list(have_caps - want_caps)
                ).delete()
                if p.get("field_policies"):
                    self.stderr.write(
                        self.style.WARNING(
                            (
                                f"Preset '{preset.name}' defines field-level policies; "
                                "deprecated entries were ignored."
                            )
                        )
                    )

            # Bindings: role -> presets
            for role_name, preset_names in bindings.items():
                roles = Role.objects.filter(name=role_name)
                if not roles.exists():
                    self.stderr.write(self.style.WARNING(f"Role not found: {role_name}"))
                    continue
                for role in roles:
                    presets_qs = PermissionPreset.objects.filter(name__in=preset_names)
                    if role.organization_id:
                        presets_qs = presets_qs.filter(
                            Q(organization=role.organization) | Q(organization__isnull=True)
                        )
                    else:
                        presets_qs = presets_qs.filter(organization__isnull=True)
                    role.presets.set(presets_qs)
        self.stdout.write(self.style.SUCCESS("Presets imported and bindings applied."))
