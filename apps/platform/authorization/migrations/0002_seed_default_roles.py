from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model('authorization', 'Role')
    RoleCapability = apps.get_model('authorization', 'RoleCapability')
    db = schema_editor.connection.alias
    defaults = {
        'OWNER': {
            'name': 'Owner', 'system': True,
            'caps': ['case.view','case.update','job.create','artifact.view','artifact.download','artifact.field.path.view','artifact.field.checksum.view']
        },
        'CONTRIBUTOR': {
            'name': 'Contributor', 'system': True,
            'caps': ['case.view','job.create','artifact.view','artifact.download','artifact.field.path.view','artifact.field.checksum.view']
        },
        'REVIEWER': {
            'name': 'Reviewer', 'system': True,
            'caps': ['case.view','artifact.view','artifact.field.checksum.view']
        },
        'AUDITOR': {
            'name': 'Auditor', 'system': True,
            'caps': ['case.view','artifact.view','artifact.field.checksum.view']
        },
        'EXTERNAL': {
            'name': 'External', 'system': True,
            'caps': ['case.view','artifact.view']
        },
        'CLIENT': {
            'name': 'Client', 'system': True,
            'caps': ['case.view','artifact.view','artifact.download']
        },
    }
    for slug, cfg in defaults.items():
        role, _ = Role.objects.using(db).get_or_create(slug=slug, defaults={'name': cfg['name'], 'system': cfg['system']})
        for c in cfg['caps']:
            RoleCapability.objects.using(db).get_or_create(role=role, capability=c)


class Migration(migrations.Migration):
    dependencies = [
        ("authorization", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
    ]
