# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-06-22 17:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0022_tournament_default_round_juryplan'),
    ]

    operations = [
        migrations.AddField(
            model_name='origin',
            name='flag',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]