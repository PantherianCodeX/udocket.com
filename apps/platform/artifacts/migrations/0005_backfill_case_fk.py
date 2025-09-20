from django.db import migrations


def backfill_case_fk(apps, schema_editor):
    CaseArtifact = apps.get_model('artifacts', 'CaseArtifact')
    Case = apps.get_model('cases', 'Case')
    db = schema_editor.connection.alias
    qs = CaseArtifact.objects.using(db).filter(case_fk__isnull=True)
    try:
        rows = list(qs.values_list('id', 'case_id'))
    except Exception:
        return
    for pk, case_id in rows:
        try:
            case = Case.objects.using(db).get(pk=case_id)
            CaseArtifact.objects.using(db).filter(pk=pk).update(case_fk=case.pk)
        except Exception:
            continue


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0004_add_case_fk"),
    ]

    operations = [
        migrations.RunPython(backfill_case_fk, migrations.RunPython.noop),
    ]
