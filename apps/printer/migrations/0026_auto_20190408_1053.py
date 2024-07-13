# Generated by Django 2.2 on 2019-04-08 10:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0025_auto_20180430_1620'),
    ]

    operations = [
        migrations.AlterField(
            model_name='defaulttemplate',
            name='type',
            field=models.CharField(choices=[('preview', 'Preview'), ('ranking', 'Ranking'), ('results', 'Results'), ('jury_round', 'Jury Round Plan'), ('grading', 'Grading Sheet'), ('team_round', 'Team Round Plan'), ('jury_feedback', 'Jury Fight Feedback'), ('problem_select', 'Problem Selection for last PF'), ('persons', 'Persons'), ('registration', 'Registration'), ('invoice', 'Invoice')], max_length=25),
        ),
        migrations.AlterField(
            model_name='pdftag',
            name='type',
            field=models.CharField(blank=True, choices=[('preview', 'Preview'), ('ranking', 'Ranking'), ('results', 'Results'), ('jury_round', 'Jury Round Plan'), ('grading', 'Grading Sheet'), ('team_round', 'Team Round Plan'), ('jury_feedback', 'Jury Fight Feedback'), ('problem_select', 'Problem Selection for last PF'), ('persons', 'Persons'), ('registration', 'Registration'), ('invoice', 'Invoice')], max_length=25, null=True),
        ),
        migrations.AlterField(
            model_name='template',
            name='type',
            field=models.CharField(blank=True, choices=[('preview', 'Preview'), ('ranking', 'Ranking'), ('results', 'Results'), ('jury_round', 'Jury Round Plan'), ('grading', 'Grading Sheet'), ('team_round', 'Team Round Plan'), ('jury_feedback', 'Jury Fight Feedback'), ('problem_select', 'Problem Selection for last PF'), ('persons', 'Persons'), ('registration', 'Registration'), ('invoice', 'Invoice')], max_length=25, null=True),
        ),
    ]