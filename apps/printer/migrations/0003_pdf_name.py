# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-22 17:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0002_auto_20170122_1705'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdf',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
