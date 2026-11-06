from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0060_pluginrun_eta_seconds_video_eta_seconds_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='camera_motion',
            field=models.CharField(blank=True, choices=[('static', 'STATIC'), ('pan', 'PAN'), ('zoom', 'ZOOM'), ('pan_zoom', 'PAN_ZOOM'), ('unknown', 'UNKNOWN')], max_length=16, null=True),
        ),
    ]
