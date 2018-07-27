# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-11-25 10:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0007_auto_20171111_1455'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userproperty',
            options={'ordering': ('order',)},
        ),
        migrations.AddField(
            model_name='userproperty',
            name='order',
            field=models.PositiveIntegerField(db_index=True, default='0', editable=False),
            preserve_default=False,
        ),
    ]