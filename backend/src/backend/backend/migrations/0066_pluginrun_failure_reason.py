from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0065_pluginrun_parameters_provenance'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginrun',
            name='failure_reason',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
