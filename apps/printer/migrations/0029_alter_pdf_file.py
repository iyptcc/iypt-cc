# Generated by Django 3.2.1 on 2021-05-05 10:21

import apps.printer.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0028_auto_20210405_1610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdf',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to=apps.printer.models.tournament_directory_path),
        ),
    ]