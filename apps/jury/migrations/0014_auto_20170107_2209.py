# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-07 22:09
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jury', '0013_auto_20170105_1906'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='jurorgrade',
            options={'permissions': (('view_results', 'View published results'),)},
        ),
    ]