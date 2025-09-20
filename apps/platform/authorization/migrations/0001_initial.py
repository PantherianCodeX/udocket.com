from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("slug", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("system", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["slug"]},
        ),
        migrations.CreateModel(
            name="RoleCapability",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("capability", models.CharField(max_length=100, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "role",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="capabilities", to="authorization.role"),
                ),
            ],
            options={
                "unique_together": {("role", "capability")},
            },
        ),
        migrations.AddIndex(
            model_name="rolecapability",
            index=models.Index(fields=["capability"], name="authz_capability_idx"),
        ),
    ]
