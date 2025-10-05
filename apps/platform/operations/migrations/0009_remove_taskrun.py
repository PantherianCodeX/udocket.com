# pyright: strict
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0008_guardiansettings"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TaskRun",
        ),
    ]
