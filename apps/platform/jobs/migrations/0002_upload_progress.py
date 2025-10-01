from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="upload_progress",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
