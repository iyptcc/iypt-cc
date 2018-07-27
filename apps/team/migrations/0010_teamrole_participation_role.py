# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-01-04 13:21
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0008_auto_20170909_2138'),
        ('team', '0009_team_join_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='teamrole',
            name='participation_role',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='account.ParticipationRole'),
        ),
    ]