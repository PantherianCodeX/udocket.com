import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Case",
            fields=[
                (
                    "id",
                    models.CharField(max_length=36, primary_key=True, serialize=False),
                ),
                ("title", models.CharField(max_length=200)),
                ("client_name", models.CharField(blank=True, max_length=200)),
                ("opposing_party", models.CharField(blank=True, max_length=200)),
                (
                    "client_position",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PLAINTIFF", "Plaintiff"),
                            ("DEFENDANT", "Defendant"),
                            ("APPLICANT", "Applicant"),
                            ("RESPONDENT", "Respondent"),
                            ("PROSECUTION", "Prosecution"),
                            ("DEFENCE", "Defence"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("court_location", models.CharField(blank=True, max_length=200)),
                (
                    "court_level",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PROVINCIAL", "Provincial"),
                            ("KINGS_BENCH", "King's Bench"),
                            ("APPEAL", "Court of Appeal"),
                            ("SUPREME", "Supreme Court"),
                            ("FEDERAL", "Federal Court"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "court_division",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("CIVIL", "Civil"),
                            ("FAMILY", "Family"),
                            ("CRIMINAL", "Criminal"),
                            ("TRAFFIC", "Traffic"),
                            ("IMMIGRATION", "Immigration"),
                            ("ADMIN", "Administrative"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("court_case_number", models.CharField(blank=True, max_length=100)),
                (
                    "representation",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("SELF", "Self-represented"),
                            ("LAWYER", "Lawyer"),
                            ("PARALEGAL", "Paralegal"),
                            ("ADVOCATE", "Advocate / Representative"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("legal_aid", models.BooleanField(default=False)),
                ("pro_bono", models.BooleanField(default=False)),
                ("court_date", models.DateTimeField(blank=True, null=True)),
                ("filing_deadline", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cases_as_client",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cases",
                        to="accounts.organization",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cases_reviewing",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="HistoricalCase",
            fields=[
                ("id", models.CharField(db_index=True, max_length=36)),
                ("title", models.CharField(max_length=200)),
                ("client_name", models.CharField(blank=True, max_length=200)),
                ("opposing_party", models.CharField(blank=True, max_length=200)),
                (
                    "client_position",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PLAINTIFF", "Plaintiff"),
                            ("DEFENDANT", "Defendant"),
                            ("APPLICANT", "Applicant"),
                            ("RESPONDENT", "Respondent"),
                            ("PROSECUTION", "Prosecution"),
                            ("DEFENCE", "Defence"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("court_location", models.CharField(blank=True, max_length=200)),
                (
                    "court_level",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PROVINCIAL", "Provincial"),
                            ("KINGS_BENCH", "King's Bench"),
                            ("APPEAL", "Court of Appeal"),
                            ("SUPREME", "Supreme Court"),
                            ("FEDERAL", "Federal Court"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "court_division",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("CIVIL", "Civil"),
                            ("FAMILY", "Family"),
                            ("CRIMINAL", "Criminal"),
                            ("TRAFFIC", "Traffic"),
                            ("IMMIGRATION", "Immigration"),
                            ("ADMIN", "Administrative"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("court_case_number", models.CharField(blank=True, max_length=100)),
                (
                    "representation",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("SELF", "Self-represented"),
                            ("LAWYER", "Lawyer"),
                            ("PARALEGAL", "Paralegal"),
                            ("ADVOCATE", "Advocate / Representative"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("legal_aid", models.BooleanField(default=False)),
                ("pro_bono", models.BooleanField(default=False)),
                ("court_date", models.DateTimeField(blank=True, null=True)),
                ("filing_deadline", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(blank=True, editable=False)),
                ("updated_at", models.DateTimeField(blank=True, editable=False)),
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
                    "client_user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
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
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="accounts.organization",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical case",
                "verbose_name_plural": "historical cases",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="CaseMembership",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("OWNER", "Owner"),
                            ("CONTRIBUTOR", "Contributor"),
                            ("REVIEWER", "Reviewer"),
                            ("ADMIN", "Admin"),
                            ("SUPERUSER", "Superuser"),
                            ("AUDITOR", "Auditor"),
                            ("EXTERNAL", "External"),
                            ("CLIENT", "Client"),
                        ],
                        default="CONTRIBUTOR",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "case",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="cases.case",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="case_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Case membership",
                "verbose_name_plural": "Case memberships",
                "unique_together": {("case", "user")},
            },
        ),
    ]
