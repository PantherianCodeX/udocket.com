from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0002_fieldvisibilityrule"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="caseartifact",
            unique_together={("case_id", "type", "title")},
        ),
        migrations.AddIndex(
            model_name="caseartifact",
            index=models.Index(fields=["case_id", "type"], name="artifact_case_type_idx"),
        ),
        migrations.AddIndex(
            model_name="caseartifact",
            index=models.Index(fields=["created_at"], name="artifact_created_idx"),
        ),
    ]
