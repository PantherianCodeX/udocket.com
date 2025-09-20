from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0002_seed_default_roles"),
    ]

    operations = [
        migrations.CreateModel(
            name="PermissionPreset",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("system", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["slug"]},
        ),
        migrations.CreateModel(
            name="PresetCapability",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("capability", models.CharField(db_index=True, max_length=100)),
                ("preset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="capabilities", to="authorization.permissionpreset")),
            ],
            options={"unique_together": {("preset", "capability")}},
        ),
        migrations.CreateModel(
            name="PresetFieldPolicy",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("type", models.CharField(max_length=32)),
                ("field_name", models.CharField(max_length=64)),
                ("actions", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("preset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="field_policies", to="authorization.permissionpreset")),
            ],
            options={
                "unique_together": {("preset", "type", "field_name")},
                "indexes": [models.Index(fields=["type", "field_name"], name="authz_pf_type_field_idx")],
            },
        ),
        migrations.AddField(
            model_name="role",
            name="presets",
            field=models.ManyToManyField(blank=True, related_name="roles", to="authorization.permissionpreset"),
        ),
    ]

