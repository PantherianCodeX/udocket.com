from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0003_alter_job_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                max_length=16,
                choices=[
                    ("PENDING", "Pending"),
                    ("RUNNING", "Running"),
                    ("CONVERTING", "Converting"),
                    ("UPLOADING", "Uploading"),
                    ("CANCELLING", "Cancelling"),
                    ("SUCCEEDED", "Succeeded"),
                    ("FAILED", "Failed"),
                    ("CANCELLED", "Cancelled"),
                ],
                default="PENDING",
                db_index=True,
            ),
        ),
    ]
