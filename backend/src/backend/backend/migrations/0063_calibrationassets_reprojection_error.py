from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0062_lensprofile_video_lens_profile_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='calibrationassets',
            name='reprojection_error',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
