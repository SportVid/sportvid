# Generated by Django 5.1.7 on 2025-03-28 11:25

import backend.models
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0023_alter_pluginrunresult_type_alter_video_file'),
    ]

    operations = [
        migrations.CreateModel(
            name='CalibrationAssets',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=1024)),
                ('homography_matrix', models.JSONField(default=backend.models.default_homography_matrix)),
                ('template', models.CharField(max_length=1024, null=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('video', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='backend.video')),
            ],
        ),
        migrations.CreateModel(
            name='PointCorrespondence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=1024)),
                ('active', models.BooleanField(default=False)),
                ('compAreaCoord_x', models.FloatField()),
                ('compAreaCoord_y', models.FloatField()),
                ('compAreaCoord_z', models.FloatField(default=0.0)),
                ('videoCoord_x', models.FloatField()),
                ('videoCoord_y', models.FloatField()),
                ('videoCoord_z', models.FloatField(default=0.0)),
                ('calibration_asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='marker_data', to='backend.calibrationassets')),
            ],
        ),
    ]
