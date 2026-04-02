from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0047_remove_pointcorrespondence_set'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackingdata',
            name='delimiter',
            field=models.CharField(default=';', max_length=10),
        ),
    ]
