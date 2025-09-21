from django.db import migrations


PRESETS = [
    {
        "slug": "owner_core",
        "name": "Case Owner Core",
        "description": "Full control of own cases; can view/download all artifacts.",
        "capabilities": [
            "case.view",
            "case.update",
            "job.create",
            "artifact.view",
            "artifact.download",
            "artifact.field.path.view",
            "artifact.field.checksum.view",
        ],
        "field_policies": [
            {"type": "TRANSCRIPT", "field": "path", "actions": ["view", "download"]},
            {"type": "TRANSCRIPT", "field": "checksum", "actions": ["view"]},
            {"type": "SUMMARY", "field": "path", "actions": ["view", "download"]},
            {"type": "TIMELINE", "field": "path", "actions": ["view", "download"]},
            {"type": "ENTITIES", "field": "path", "actions": ["view", "download"]},
            {"type": "GRAPH", "field": "path", "actions": ["view", "download"]},
        ],
    },
    {
        "slug": "contributor_core",
        "name": "Contributor Core",
        "description": "Create jobs; view and download working artifacts; cannot change case metadata.",
        "capabilities": [
            "case.view",
            "job.create",
            "artifact.view",
            "artifact.download",
            "artifact.field.path.view",
            "artifact.field.checksum.view",
        ],
        "field_policies": [
            {"type": "TRANSCRIPT", "field": "path", "actions": ["view", "download"]},
            {"type": "TRANSCRIPT", "field": "checksum", "actions": ["view"]},
            {"type": "SUMMARY", "field": "path", "actions": ["view", "download"]},
            {"type": "TIMELINE", "field": "path", "actions": ["view", "download"]},
        ],
    },
    {
        "slug": "reviewer_readonly",
        "name": "Reviewer Read-Only",
        "description": "Read-only access; no downloads of source paths by default.",
        "capabilities": [
            "case.view",
            "artifact.view",
            "artifact.field.checksum.view",
        ],
        "field_policies": [
            {"type": "TRANSCRIPT", "field": "path", "actions": []},
            {"type": "SUMMARY", "field": "path", "actions": ["view"]},
            {"type": "TIMELINE", "field": "path", "actions": ["view"]},
        ],
    },
    {
        "slug": "auditor_strict",
        "name": "Auditor Strict",
        "description": "Auditing access to verify provenance; can see checksums but not raw paths.",
        "capabilities": [
            "case.view",
            "artifact.view",
            "artifact.field.checksum.view",
        ],
        "field_policies": [
            {"type": "TRANSCRIPT", "field": "checksum", "actions": ["view"]},
            {"type": "SUMMARY", "field": "path", "actions": ["view"]},
        ],
    },
    {
        "slug": "external_share_min",
        "name": "External Share (Minimal)",
        "description": "Minimal viewing of select derived artifacts; no downloads, no checksums.",
        "capabilities": [
            "case.view",
            "artifact.view",
        ],
        "field_policies": [
            {"type": "SUMMARY", "field": "path", "actions": ["view"]},
        ],
    },
    {
        "slug": "client_portal",
        "name": "Client Portal",
        "description": "Client-facing access to review and download approved artifacts.",
        "capabilities": [
            "case.view",
            "artifact.view",
            "artifact.download",
        ],
        "field_policies": [
            {"type": "SUMMARY", "field": "path", "actions": ["view", "download"]},
            {"type": "TIMELINE", "field": "path", "actions": ["view", "download"]},
        ],
    },
]

ROLE_BINDINGS = {
    "OWNER": ["owner_core"],
    "CONTRIBUTOR": ["contributor_core"],
    "REVIEWER": ["reviewer_readonly"],
    "AUDITOR": ["auditor_strict"],
    "EXTERNAL": ["external_share_min"],
    "CLIENT": ["client_portal"],
}


def seed_presets(apps, schema_editor):
    Role = apps.get_model("authorization", "Role")
    RoleCapability = apps.get_model("authorization", "RoleCapability")
    PermissionPreset = apps.get_model("authorization", "PermissionPreset")
    PresetCapability = apps.get_model("authorization", "PresetCapability")
    PresetFieldPolicy = apps.get_model("authorization", "PresetFieldPolicy")

    db_alias = schema_editor.connection.alias

    for preset_def in PRESETS:
        preset, created = PermissionPreset.objects.using(db_alias).get_or_create(
            slug=preset_def["slug"],
            defaults={
                "name": preset_def.get("name", preset_def["slug"]),
                "description": preset_def.get("description", ""),
                "system": True,
            },
        )
        if not created:
            preset.name = preset_def.get("name", preset.name)
            preset.description = preset_def.get("description", preset.description)
            preset.system = True
            preset.save(update_fields=["name", "description", "system"])

        desired_caps = set(preset_def.get("capabilities", []))
        PresetCapability.objects.using(db_alias).filter(preset=preset).exclude(
            capability__in=desired_caps
        ).delete()
        for cap in desired_caps:
            PresetCapability.objects.using(db_alias).get_or_create(preset=preset, capability=cap)

        desired_policies = {}
        for policy in preset_def.get("field_policies", []):
            atype = (policy.get("type") or "").upper()
            field = (policy.get("field") or "").strip()
            actions = list(policy.get("actions", []) or [])
            if not atype or not field:
                continue
            desired_policies[(atype, field)] = actions

        existing = {
            (fp.type, fp.field_name): fp
            for fp in PresetFieldPolicy.objects.using(db_alias).filter(preset=preset)
        }

        for (atype, field), actions in desired_policies.items():
            inst = existing.get((atype, field))
            if inst is None:
                PresetFieldPolicy.objects.using(db_alias).create(
                    preset=preset,
                    type=atype,
                    field_name=field,
                    actions=actions,
                )
            elif list(inst.actions or []) != actions:
                inst.actions = actions
                inst.save(update_fields=["actions"])

        for key, inst in existing.items():
            if key not in desired_policies:
                inst.delete()

    # Remove contributor case.update capability
    RoleCapability.objects.using(db_alias).filter(
        role__slug="CONTRIBUTOR", capability="case.update"
    ).delete()

    # Bind presets to roles
    for role_slug, preset_slugs in ROLE_BINDINGS.items():
        role = Role.objects.using(db_alias).filter(slug=role_slug).first()
        if not role:
            continue
        preset_qs = PermissionPreset.objects.using(db_alias).filter(slug__in=preset_slugs)
        role.presets.set(preset_qs)


class Migration(migrations.Migration):
    dependencies = [
        ("authorization", "0003_presets_models"),
    ]

    operations = [
        migrations.RunPython(seed_presets, migrations.RunPython.noop),
    ]
