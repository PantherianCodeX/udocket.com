from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="job",
            name="finished_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
    ]
