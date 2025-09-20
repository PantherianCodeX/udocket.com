from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0003_constraints_indexes"),
        ("cases", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="caseartifact",
            name="case_fk",
            field=models.ForeignKey(
                related_name="artifacts",
                to="cases.case",
                on_delete=models.PROTECT,
                null=True,
                blank=True,
            ),
        ),
    ]
