# Generated by Django 2.1.2 on 2018-11-11 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('postoffice', '0002_auto_20180321_1714'),
    ]

    operations = [
        migrations.AlterField(
            model_name='template',
            name='type',
            field=models.CharField(blank=True, choices=[('registration', 'Registration'), ('jurorfeedback', 'Juror Feedback')], max_length=25, null=True),
        ),
    ]