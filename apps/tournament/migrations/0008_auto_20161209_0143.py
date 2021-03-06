# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-12-09 01:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0007_auto_20161125_1204'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScheduleTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250)),
                ('teams_nr', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='TemplateAttendance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('rep', 'Reporter'), ('opp', 'Opponent'), ('rev', 'Reviewer'), ('obs', 'Observer')], max_length=3)),
                ('team', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='TemplateFight',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='TemplateRound',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField()),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rounds', to='tournament.ScheduleTemplate')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.AddField(
            model_name='templatefight',
            name='round',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournament.TemplateRound'),
        ),
        migrations.AddField(
            model_name='templateattendance',
            name='fight',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournament.TemplateFight'),
        ),
    ]
