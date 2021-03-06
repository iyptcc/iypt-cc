# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-06-25 12:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jury', '0017_auto_20170423_1139'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='juror',
            name='independent',
        ),
        migrations.AddField(
            model_name='juror',
            name='local',
            field=models.NullBooleanField(),
        ),
        migrations.AlterField(
            model_name='jurorrole',
            name='type',
            field=models.CharField(blank=True, choices=[('0ch', 'Chair'), ('1ju', 'Juror'), ('2nv', 'Non-Voting')], max_length=3, null=True),
        ),
    ]
