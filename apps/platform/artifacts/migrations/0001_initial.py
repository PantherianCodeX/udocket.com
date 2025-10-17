from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("cases", "0001_initial"),
    ]

    operations = [
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
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "case_fk",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="cases.case",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="accounts.organization",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical case artifact",
                "verbose_name_plural": "historical case artifacts",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="CaseArtifact",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("case_id", models.CharField(max_length=36)),
                ("job_id", models.CharField(blank=True, max_length=36, null=True)),
                ("type", models.CharField(max_length=32)),
                ("title", models.CharField(blank=True, max_length=200)),
                ("path", models.TextField()),
                ("checksum", models.CharField(blank=True, max_length=64)),
                ("schema_version", models.CharField(blank=True, max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "case_fk",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="artifacts",
                        to="cases.case",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="artifacts",
                        to="accounts.organization",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["case_id", "type"], name="artifact_case_type_idx"
                    ),
                    models.Index(fields=["created_at"], name="artifact_created_idx"),
                ],
                "unique_together": {("case_id", "type", "title")},
            },
        ),
    ]
