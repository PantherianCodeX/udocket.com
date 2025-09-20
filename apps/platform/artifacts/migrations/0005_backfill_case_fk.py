from django.db import migrations


def backfill_case_fk(apps, schema_editor):
    CaseArtifact = apps.get_model('artifacts', 'CaseArtifact')
    Case = apps.get_model('cases', 'Case')
    db = schema_editor.connection.alias
    for art in CaseArtifact.objects.using(db).filter(case_fk__isnull=True):
        try:
            case = Case.objects.using(db).get(pk=art.case_id)
            art.case_fk_id = case.pk
            art.save(update_fields=['case_fk'])
        except Exception:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0004_add_case_fk"),
    ]

    operations = [
        migrations.RunPython(backfill_case_fk, migrations.RunPython.noop),
    ]
