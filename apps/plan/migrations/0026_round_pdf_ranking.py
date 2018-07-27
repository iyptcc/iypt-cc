# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-07-04 00:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0016_auto_20170628_2034'),
        ('plan', '0025_auto_20170628_2046'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='pdf_ranking',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ranking', to='printer.Pdf'),
        ),
    ]