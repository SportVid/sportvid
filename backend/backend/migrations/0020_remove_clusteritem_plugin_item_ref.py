# Generated by Django 3.1.1 on 2024-04-22 10:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0019_timeline_colormap_inverse'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clusteritem',
            name='plugin_item_ref',
        ),
    ]
