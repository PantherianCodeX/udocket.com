# pyright: strict
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0004_llmconfiguration"),
    ]

    operations = [
        migrations.DeleteModel(
            name="LLMProviderSetting",
        ),
    ]
