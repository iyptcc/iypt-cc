# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-11-15 15:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('team', '0002_auto_20161008_2317'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamrole',
            name='type',
            field=models.CharField(blank=True, choices=[('captain', 'Captain'), ('member', 'Member')], max_length=15, null=True),
        ),
    ]