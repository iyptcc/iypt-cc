# Generated by Django 4.2.1 on 2023-07-17 13:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0030_fileserver'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileserver',
            name='fingerprint',
            field=models.CharField(default='', max_length=4000),
        ),
    ]
