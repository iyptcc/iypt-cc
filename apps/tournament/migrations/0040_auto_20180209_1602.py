# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-02-09 16:02
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0039_auto_20180209_1557'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tournament',
            options={'permissions': (('app_team', 'Access to Team app'), ('app_tournament', 'Access to Tournament app'), ('app_plan', 'Access to Plan app'), ('app_jury', 'Access to Jury app'), ('app_fight', 'Access to Fight app'), ('app_printer', 'Access to Printer app'), ('app_schedule', 'Access to Schedule app'), ('app_management', 'Access to Management app'), ('app_bank', 'Access to Bank app'), ('change_attendee_data', 'Customise Participation Data'), ('delete_attendee_data', 'Delete Participation Data'))},
        ),
    ]