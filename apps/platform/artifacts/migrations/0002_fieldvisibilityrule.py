from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("artifacts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FieldVisibilityRule",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("type", models.CharField(max_length=32)),
                ("field_name", models.CharField(max_length=64)),
                ("allowed_roles", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "unique_together": {("type", "field_name")},
            },
        ),
        migrations.AddIndex(
            model_name="fieldvisibilityrule",
            index=models.Index(fields=["type", "field_name"], name="artv_type_field_idx"),
        ),
    ]

