# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-06-28 20:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0016_auto_20170628_2034'),
        ('tournament', '0023_origin_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='default_round_teamplan',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='teamround_tournament', to='printer.Template'),
        ),
    ]
