from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("RUNNING", "Running"),
                    ("CONVERTING", "Converting"),
                    ("UPLOADING", "Uploading"),
                    ("CANCELLING", "Cancelling"),
                    ("STALLED", "Stalled"),
                    ("SUCCEEDED", "Succeeded"),
                    ("FAILED", "Failed"),
                    ("CANCELLED", "Cancelled"),
                    ("CORRUPTED", "Corrupted"),
                ],
                db_index=True,
                default="PENDING",
                max_length=16,
            ),
        ),
    ]
