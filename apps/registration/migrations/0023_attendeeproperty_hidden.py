# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-01-22 20:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0022_auto_20180116_2209'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendeeproperty',
            name='hidden',
            field=models.BooleanField(default=False),
        ),
    ]