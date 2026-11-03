import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0061_video_camera_motion'),
    ]

    operations = [
        migrations.CreateModel(
            name='LensProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('key', models.CharField(max_length=512, unique=True)),
                ('name', models.CharField(max_length=512)),
                ('group', models.CharField(max_length=128)),
                ('brand', models.CharField(db_index=True, max_length=128)),
                ('model', models.CharField(db_index=True, max_length=256)),
                ('lens_model', models.CharField(blank=True, default='', max_length=256)),
                ('camera_setting', models.CharField(blank=True, default='', max_length=256)),
                ('note', models.CharField(blank=True, default='', max_length=1024)),
                ('calib_width', models.IntegerField()),
                ('calib_height', models.IntegerField()),
                ('fps', models.FloatField(blank=True, null=True)),
                ('camera_matrix', models.JSONField()),
                ('distortion_coeffs', models.JSONField()),
                ('rms_error', models.FloatField(blank=True, null=True)),
                ('official', models.BooleanField(default=False)),
                ('eis', models.CharField(choices=[('on', 'ON'), ('off', 'OFF'), ('unknown', 'UNKNOWN')], default='unknown', max_length=8)),
                ('unsupported_reason', models.CharField(blank=True, max_length=256, null=True)),
                ('source_commit', models.CharField(max_length=64)),
                ('raw', models.JSONField()),
            ],
            options={
                'ordering': ['brand', 'model', 'lens_model', 'calib_width'],
            },
        ),
        migrations.AddField(
            model_name='video',
            name='lens_profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='videos', to='backend.lensprofile'),
        ),
        migrations.AddField(
            model_name='calibrationassets',
            name='lens_intrinsics',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='calibrationassets',
            name='camera_pose',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
