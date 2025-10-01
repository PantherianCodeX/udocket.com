from django.db import migrations, models
import uuid


def set_default_flags(apps, schema_editor):
    Configuration = apps.get_model("operations", "LLMConfiguration")
    for config in Configuration.objects.all():
        # ensure provider_chain/stage_map not None
        if config.provider_chain is None:
            config.provider_chain = []
        if config.stage_map is None:
            config.stage_map = {}
        config.save(update_fields=["provider_chain", "stage_map"])


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0003_llmprovidercredential"),
    ]

    operations = [
        migrations.CreateModel(
            name="LLMConfiguration",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="llm_configurations",
                        to="accounts.organization",
                    ),
                ),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True)),
                ("target", models.CharField(default="summary", max_length=64)),
                ("provider_chain", models.JSONField(blank=True, default=list)),
                ("stage_map", models.JSONField(blank=True, default=dict)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="llmconfiguration",
            unique_together={("organization", "name", "target")},
        ),
        migrations.RunPython(set_default_flags, migrations.RunPython.noop),
    ]
