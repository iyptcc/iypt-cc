# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-02-14 21:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0013_auto_20180214_1438'),
    ]

    operations = [
        migrations.AddField(
            model_name='participationrole',
            name='fee',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
