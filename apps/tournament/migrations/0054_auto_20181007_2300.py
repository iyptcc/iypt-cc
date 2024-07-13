# Generated by Django 2.1.2 on 2018-10-07 23:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0053_tournament_jury_opt_weight_bias'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tournament',
            options={'permissions': (('app_team', 'Access to Team app'), ('app_tournament', 'Access to Tournament app'), ('app_plan', 'Access to Plan app'), ('app_jury', 'Access to Jury app'), ('app_feedback', 'Access to Feedback app'), ('app_fight', 'Access to Fight app'), ('app_printer', 'Access to Printer app'), ('app_schedule', 'Access to Schedule app'), ('app_management', 'Access to Management app'), ('app_bank', 'Access to Bank app'), ('app_postoffice', 'Access to Postoffice app'), ('change_attendee_data', 'Customise Participation Data'), ('delete_attendee_data', 'Delete Participation Data'))},
        ),
    ]