# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-11-06 17:47
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jury', '0005_auto_20161106_1523'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='jurorsession',
            options={'permissions': (('change_all_jurorsessions', 'Can change jury any time'),)},
        ),
    ]
