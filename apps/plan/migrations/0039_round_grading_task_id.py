# Generated by Django 2.1.9 on 2019-07-11 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plan', '0038_round_feedback_task_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='grading_task_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]