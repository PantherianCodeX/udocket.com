from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


def create_historical_caseartifact(apps, schema_editor):
    try:
        existing = schema_editor.connection.introspection.table_names()
    except Exception:
        existing = []
    if "artifacts_historicalcaseartifact" in existing:
        return
    class HistoricalCaseArtifactCreate(models.Model):
        id = models.BigIntegerField(blank=True, db_index=True)
        case_id = models.CharField(max_length=36)
        job_id = models.CharField(max_length=36, null=True, blank=True)
        type = models.CharField(max_length=32)
        title = models.CharField(max_length=200, blank=True)
        path = models.TextField()
        checksum = models.CharField(max_length=64, blank=True)
        schema_version = models.CharField(max_length=16, blank=True)
        created_at = models.DateTimeField(blank=True, editable=False)
        metadata = models.JSONField(default=dict, blank=True)
        case_fk = models.ForeignKey(
            "cases.Case",
            on_delete=django.db.models.deletion.DO_NOTHING,
            related_name="+",
            null=True,
            blank=True,
        )
        history_id = models.AutoField(primary_key=True)
        history_date = models.DateTimeField()
        history_change_reason = models.CharField(max_length=100, null=True)
        history_type = models.CharField(max_length=1)
        history_user = models.ForeignKey(
            settings.AUTH_USER_MODEL, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+"
        )

        class Meta:
            app_label = "artifacts"
            db_table = "artifacts_historicalcaseartifact"
            managed = False
    try:
        schema_editor.create_model(HistoricalCaseArtifactCreate)
    except Exception:
        return


class Migration(migrations.Migration):

    dependencies = [
        ("artifacts", "0007_remove_caseartifact_artifacts_c_case_id_cfc414_idx_and_more"),
        ("cases", "0004_historicalcase"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_historical_caseartifact, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="HistoricalCaseArtifact",
                    fields=[
                        ("id", models.BigIntegerField(blank=True, db_index=True)),
                        ("case_id", models.CharField(max_length=36)),
                        ("job_id", models.CharField(blank=True, max_length=36, null=True)),
                        ("type", models.CharField(max_length=32)),
                        ("title", models.CharField(blank=True, max_length=200)),
                        ("path", models.TextField()),
                        ("checksum", models.CharField(blank=True, max_length=64)),
                        ("schema_version", models.CharField(blank=True, max_length=16)),
                        ("created_at", models.DateTimeField(blank=True, editable=False)),
                        ("metadata", models.JSONField(blank=True, default=dict)),
                        (
                            "case_fk",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                related_name="+",
                                on_delete=django.db.models.deletion.DO_NOTHING,
                                to="cases.case",
                            ),
                        ),
                        ("history_id", models.AutoField(primary_key=True, serialize=False)),
                        ("history_date", models.DateTimeField()),
                        ("history_change_reason", models.CharField(max_length=100, null=True)),
                        (
                            "history_type",
                            models.CharField(
                                max_length=1,
                                choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                            ),
                        ),
                        (
                            "history_user",
                            models.ForeignKey(
                                null=True,
                                related_name="+",
                                on_delete=django.db.models.deletion.SET_NULL,
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "historical case artifact",
                        "ordering": ("-history_date", "-history_id"),
                        "get_latest_by": "history_date",
                    },
                ),
            ],
        ),
    ]
