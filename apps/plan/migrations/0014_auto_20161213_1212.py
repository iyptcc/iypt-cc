# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-12-13 12:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('plan', '0013_auto_20161213_0931'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fight',
            options={'ordering': ['room__name'], 'permissions': (('view_fight_operator', 'Can list fight operators/locks'), ('change_fight_operator', 'Can change fight operators/locks'))},
        ),
    ]