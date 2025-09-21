from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0009_case_add_metadata_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalcase",
            name="client_name",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="client_position",
            field=models.CharField(blank=True, choices=[("PLAINTIFF", "Plaintiff"), ("DEFENDANT", "Defendant"), ("APPLICANT", "Applicant"), ("RESPONDENT", "Respondent"), ("PROSECUTION", "Prosecution"), ("DEFENCE", "Defence"), ("OTHER", "Other")], max_length=20),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="court_case_number",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="court_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="court_division",
            field=models.CharField(blank=True, choices=[("CIVIL", "Civil"), ("FAMILY", "Family"), ("CRIMINAL", "Criminal"), ("TRAFFIC", "Traffic"), ("IMMIGRATION", "Immigration"), ("ADMIN", "Administrative"), ("OTHER", "Other")], max_length=20),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="court_level",
            field=models.CharField(blank=True, choices=[("PROVINCIAL", "Provincial"), ("KINGS_BENCH", "King's Bench"), ("APPEAL", "Court of Appeal"), ("SUPREME", "Supreme Court"), ("FEDERAL", "Federal Court"), ("OTHER", "Other")], max_length=20),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="court_location",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="filing_deadline",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="legal_aid",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="opposing_party",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="pro_bono",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="historicalcase",
            name="representation",
            field=models.CharField(blank=True, choices=[("SELF", "Self-represented"), ("LAWYER", "Lawyer"), ("PARALEGAL", "Paralegal"), ("ADVOCATE", "Advocate / Representative"), ("OTHER", "Other")], max_length=20),
        ),
    ]
