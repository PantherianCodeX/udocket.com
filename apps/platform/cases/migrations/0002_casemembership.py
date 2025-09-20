from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("cases", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CaseMembership",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[
                    ("OWNER", "Owner"), ("CONTRIBUTOR", "Contributor"), ("REVIEWER", "Reviewer"), ("AUDITOR", "Auditor"), ("EXTERNAL", "External")
                ], default="CONTRIBUTOR", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("case", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="cases.case")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="case_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Case membership",
                "verbose_name_plural": "Case memberships",
                "unique_together": {("case", "user")},
            },
        ),
    ]

