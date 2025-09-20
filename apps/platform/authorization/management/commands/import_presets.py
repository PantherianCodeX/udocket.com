from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.platform.authorization.models import (
    Role,
    PermissionPreset,
    PresetCapability,
    PresetFieldPolicy,
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
            for p in presets:
                preset, created = PermissionPreset.objects.get_or_create(
                    slug=p["slug"], defaults={"name": p.get("name", p["slug"]), "description": p.get("description", ""), "system": True}
                )
                if not created:
                    preset.name = p.get("name", preset.name)
                    preset.description = p.get("description", preset.description)
                    preset.system = True
                    preset.save(update_fields=["name", "description", "system"])
                # Capabilities
                want_caps = set(p.get("capabilities", []) or [])
                have_caps = set(PresetCapability.objects.filter(preset=preset).values_list("capability", flat=True))
                for c in want_caps - have_caps:
                    PresetCapability.objects.create(preset=preset, capability=c)
                PresetCapability.objects.filter(preset=preset, capability__in=list(have_caps - want_caps)).delete()
                # Field policies
                want_fps = {(fp.get("type"), fp.get("field")): fp.get("actions", []) for fp in (p.get("field_policies") or [])}
                have = {(fp.type, fp.field_name): fp for fp in PresetFieldPolicy.objects.filter(preset=preset)}
                # Upsert
                for (typ, field), actions in want_fps.items():
                    inst = have.get((typ, field))
                    if inst is None:
                        PresetFieldPolicy.objects.create(preset=preset, type=typ, field_name=field, actions=actions)
                    else:
                        if (inst.actions or []) != actions:
                            inst.actions = actions
                            inst.save(update_fields=["actions"])
                # Remove extras
                for (typ, field), inst in have.items():
                    if (typ, field) not in want_fps:
                        inst.delete()

            # Bindings: role -> presets
            for role_slug, preset_slugs in bindings.items():
                r = Role.objects.filter(slug=role_slug).first()
                if not r:
                    self.stderr.write(self.style.WARNING(f"Role not found: {role_slug}"))
                    continue
                preset_objs = list(PermissionPreset.objects.filter(slug__in=preset_slugs))
                r.presets.set(preset_objs)
        self.stdout.write(self.style.SUCCESS("Presets imported and bindings applied."))

