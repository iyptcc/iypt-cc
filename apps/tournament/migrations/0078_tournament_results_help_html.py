# Generated by Django 3.1 on 2021-04-07 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0077_tournament_fight_room_public_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='results_help_html',
            field=models.TextField(blank=True, null=True),
        ),
    ]
