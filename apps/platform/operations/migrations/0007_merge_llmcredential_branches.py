# pyright: strict
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("operations", "0004_llmprovidercredential_uid"),
        ("operations", "0006_llmprovidercredential_is_enabled_and_more"),
    ]

    operations = []
