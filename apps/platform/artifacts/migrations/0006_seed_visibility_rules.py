from django.db import migrations


def seed_rules(apps, schema_editor):
    Rule = apps.get_model('artifacts', 'FieldVisibilityRule')
    db = schema_editor.connection.alias
    defaults = [
        {"type": "TRANSCRIPT", "field_name": "path", "allowed_roles": ["OWNER", "CONTRIBUTOR"]},
        {"type": "TRANSCRIPT", "field_name": "checksum", "allowed_roles": ["OWNER", "CONTRIBUTOR", "AUDITOR"]},
    ]
    for r in defaults:
        Rule.objects.using(db).get_or_create(type=r["type"], field_name=r["field_name"], defaults={"allowed_roles": r["allowed_roles"]})


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0005_backfill_case_fk"),
    ]

    operations = [
        migrations.RunPython(seed_rules, migrations.RunPython.noop),
    ]
