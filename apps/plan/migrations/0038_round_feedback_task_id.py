# Generated by Django 2.1.9 on 2019-07-11 14:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plan', '0037_fight_publish_partials'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='feedback_task_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]