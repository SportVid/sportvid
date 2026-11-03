from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0063_calibrationassets_reprojection_error'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='lens_crop',
            field=models.FloatField(default=1.0),
        ),
    ]
