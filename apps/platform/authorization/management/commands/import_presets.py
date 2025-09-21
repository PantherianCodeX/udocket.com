from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.platform.accounts.models import Organization
from apps.platform.authorization.models import (
    PermissionPreset,
    PresetCapability,
    PresetFieldPolicy,
    Role,
)
from apps.platform.artifacts.registry import artifact_field


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
            for p in presets:
                org = None
                org_slug = p.get("organization")
                if org_slug:
                    org = Organization.objects.filter(id=org_slug).first()
                    if org is None:
                        raise CommandError(
                            f"Organization not found for preset '{p.get('name') or p.get('slug') or 'UNKNOWN'}': {org_slug}"
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
                have_caps = set(PresetCapability.objects.filter(preset=preset).values_list("capability", flat=True))
                for c in want_caps - have_caps:
                    PresetCapability.objects.create(preset=preset, capability=c)
                PresetCapability.objects.filter(preset=preset, capability__in=list(have_caps - want_caps)).delete()
                # Field policies
                want_fps = {}
                for fp in (p.get("field_policies") or []):
                    typ = (fp.get("type") or "").upper()
                    field = (fp.get("field") or "").strip()
                    if artifact_field(typ, field) is None:
                        raise CommandError(
                            f"Unknown artifact field in preset '{preset.name}': {typ}.{field}"
                        )
                    inferred_resource = "CASE" if typ == "CASE" else "ARTIFACT"
                    resource = (fp.get("resource") or inferred_resource).upper()
                    want_fps[(resource, typ, field)] = fp.get("actions", []) or []
                have = {
                    (fp.resource, fp.type, fp.field_name): fp
                    for fp in PresetFieldPolicy.objects.filter(preset=preset)
                }
                # Upsert
                for (resource, typ, field), actions in want_fps.items():
                    inst = have.get((resource, typ, field))
                    if inst is None:
                        PresetFieldPolicy.objects.create(
                            preset=preset,
                            resource=resource,
                            type=typ,
                            field_name=field,
                            actions=actions,
                        )
                    else:
                        if (inst.actions or []) != actions:
                            inst.actions = actions
                            inst.save(update_fields=["actions"])
                # Remove extras
                for (resource, typ, field), inst in have.items():
                    if (resource, typ, field) not in want_fps:
                        inst.delete()

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
