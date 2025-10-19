from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
        ("cases", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("audio_input", models.TextField()),
                (
                    "mode",
                    models.CharField(
                        choices=[("batch", "Batch"), ("on-demand", "On Demand")],
                        default="on-demand",
                        max_length=16,
                    ),
                ),
                ("diarization", models.BooleanField(default=False)),
                ("language", models.CharField(default="en-CA", max_length=16)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("CONVERTING", "Converting"),
                            ("UPLOADING", "Uploading"),
                            ("CANCELLING", "Cancelling"),
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
                ("error_message", models.TextField(blank=True, null=True)),
                ("transcript_path", models.TextField(blank=True, null=True)),
                ("duration_s", models.FloatField(blank=True, null=True)),
                ("display_title", models.CharField(blank=True, max_length=255)),
                (
                    "agent_type",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                ("agent_label", models.CharField(blank=True, max_length=128)),
                (
                    "job_kind",
                    models.CharField(blank=True, db_index=True, max_length=64),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "started_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "finished_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("upload_progress", models.FloatField(blank=True, null=True)),
                (
                    "review_status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_comment", models.TextField(blank=True)),
                (
                    "review_activity_id",
                    models.UUIDField(blank=True, editable=False, null=True),
                ),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="jobs",
                        to="cases.case",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="jobs",
                        to="accounts.organization",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "source_job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_jobs",
                        to="jobs.job",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="JobNote",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("text", models.TextField()),
                ("created_by_name", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="job_notes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notes",
                        to="jobs.job",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["job", "-created_at"],
                        name="jobs_jobnot_job_id_e629a8_idx",
                    )
                ],
            },
        ),
    ]
