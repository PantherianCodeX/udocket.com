# pyright: strict
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0003_llmprovidercredential"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmprovidercredential",
            name="uid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

