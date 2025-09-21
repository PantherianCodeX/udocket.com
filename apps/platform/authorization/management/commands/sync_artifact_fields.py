from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.platform.artifacts.registry import artifact_field, artifact_field_keys
from apps.platform.authorization.models import PermissionPreset, PresetFieldPolicy


class Command(BaseCommand):
    help = "Ensure permission presets cover all registered artifact fields."

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with non-zero status if missing or stale policies are detected without modifying data.",
        )
        parser.add_argument(
            "--no-apply",
            action="store_true",
            help="Do not create missing PresetFieldPolicy entries (useful for dry runs).",
        )
        parser.add_argument(
            "--delete-stale",
            action="store_true",
            help="Delete PresetFieldPolicy rows referencing unknown artifact fields.",
        )

    def handle(self, *args, **options):  # type: ignore[override]
        check_only: bool = options["check"]
        apply_missing: bool = not options["no_apply"] and not check_only
        delete_stale: bool = bool(options["delete_stale"])
        registry_keys = artifact_field_keys()
        missing: dict[str, set[tuple[str, str]]] = defaultdict(set)
        stale: dict[str, set[tuple[str, str]]] = defaultdict(set)

        presets = list(PermissionPreset.objects.all().prefetch_related("field_policies"))
        for preset in presets:
            existing = set((fp.type, fp.field_name) for fp in preset.field_policies.all())
            for key in registry_keys - existing:
                missing[preset.name].add(key)
            for key in existing - registry_keys:
                stale[preset.name].add(key)

        if check_only:
            if missing or (stale and not delete_stale):
                problems = []
                if missing:
                    problems.append(
                        "missing: "
                        + ", ".join(
                            f"{name} -> {sorted(list(keys))}" for name, keys in sorted(missing.items())
                        )
                    )
                if stale and not delete_stale:
                    problems.append(
                        "stale: "
                        + ", ".join(
                            f"{name} -> {sorted(list(keys))}" for name, keys in sorted(stale.items())
                        )
                    )
                raise CommandError("; ".join(problems))
            self.stdout.write(self.style.SUCCESS("All presets cover registered artifact fields."))
            return

        created = 0
        deleted = 0
        with transaction.atomic():
            if apply_missing and missing:
                for preset in presets:
                    todo = missing.get(preset.name)
                    if not todo:
                        continue
                    for artifact_type, field_name in sorted(todo):
                        meta = artifact_field(artifact_type, field_name)
                        actions = list(meta.default_actions) if meta else []
                        PresetFieldPolicy.objects.create(
                            preset=preset,
                            type=artifact_type,
                            field_name=field_name,
                            actions=actions,
                        )
                        created += 1
            if delete_stale and stale:
                for preset in presets:
                    extraneous = stale.get(preset.name)
                    if not extraneous:
                        continue
                    deleted += PresetFieldPolicy.objects.filter(
                        preset=preset,
                        type__in=[t for (t, _) in extraneous],
                        field_name__in=[f for (_, f) in extraneous],
                    ).delete()[0]

        summary_parts: list[str] = []
        if created:
            summary_parts.append(f"created {created} missing policies")
        if deleted:
            summary_parts.append(f"removed {deleted} stale policies")
        if not summary_parts:
            summary_parts.append("no changes")
        self.stdout.write(self.style.SUCCESS("sync complete: " + ", ".join(summary_parts)))

        if missing and not apply_missing:
            self.stdout.write(self.style.WARNING("Missing policies remain (use default apply behaviour to create them)."))
        if stale and not delete_stale:
            self.stdout.write(
                self.style.WARNING("Stale policies remain; rerun with --delete-stale to remove them."),
            )
