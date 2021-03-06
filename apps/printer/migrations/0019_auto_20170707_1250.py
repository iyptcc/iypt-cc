# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-07-07 12:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0018_auto_20170705_1708'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pdftag',
            name='type',
            field=models.CharField(blank=True, choices=[('preview', 'Preview'), ('ranking', 'Ranking'), ('results', 'Results'), ('jury_round', 'Jury Round Plan'), ('team_round', 'Team Round Plan'), ('jury_feedback', 'Jury Fight Feedback'), ('problem_select', 'Problem Selection for last PF')], max_length=25, null=True),
        ),
        migrations.AlterField(
            model_name='template',
            name='type',
            field=models.CharField(blank=True, choices=[('preview', 'Preview'), ('ranking', 'Ranking'), ('results', 'Results'), ('jury_round', 'Jury Round Plan'), ('team_round', 'Team Round Plan'), ('jury_feedback', 'Jury Fight Feedback'), ('problem_select', 'Problem Selection for last PF')], max_length=25, null=True),
        ),
    ]
