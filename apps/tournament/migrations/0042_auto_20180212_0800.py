# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-02-12 08:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0041_auto_20180212_0738'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='registration_teamleaderjurors_required',
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name='tournament',
            name='registration_teamleaderjurors_required_guest',
            field=models.IntegerField(default=0),
        ),
    ]
