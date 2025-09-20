from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


def create_historical_case(apps, schema_editor):
    try:
        existing = schema_editor.connection.introspection.table_names()
    except Exception:
        existing = []
    if "cases_historicalcase" in existing:
        return
    # Define a lightweight unmanaged model to let Django create the table with the correct backend types
    class HistoricalCaseCreate(models.Model):
        id = models.CharField(max_length=36, db_index=True, blank=True)
        title = models.CharField(max_length=200)
        created_at = models.DateTimeField(blank=True, editable=False)
        updated_at = models.DateTimeField(blank=True, editable=False)
        history_id = models.AutoField(primary_key=True)
        history_date = models.DateTimeField()
        history_change_reason = models.CharField(max_length=100, null=True)
        history_type = models.CharField(max_length=1)
        history_user = models.ForeignKey(
            settings.AUTH_USER_MODEL, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+"
        )
        class Meta:
            app_label = "cases"
            db_table = "cases_historicalcase"
            managed = False
    try:
        schema_editor.create_model(HistoricalCaseCreate)
    except Exception:
        # If created concurrently, ignore
        return


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0003_alter_casemembership_id"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(create_historical_case, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.CreateModel(
                    name="HistoricalCase",
                    fields=[
                        ("id", models.CharField(max_length=36, db_index=True, blank=True)),
                        ("title", models.CharField(max_length=200)),
                        ("created_at", models.DateTimeField(blank=True, editable=False)),
                        ("updated_at", models.DateTimeField(blank=True, editable=False)),
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
                        "verbose_name": "historical case",
                        "ordering": ("-history_date", "-history_id"),
                        "get_latest_by": "history_date",
                    },
                ),
            ],
        ),
    ]
