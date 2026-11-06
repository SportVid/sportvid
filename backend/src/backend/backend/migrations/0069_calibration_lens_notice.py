from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0068_pointcorrespondence_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='calibration',
            name='lens_notice',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
