# Generated by Django 3.2.6 on 2022-02-08 10:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jury', '0040_auto_20220207_1136'),
        ('plan', '0048_fight_virtual_guests'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='reserved_jurors',
            field=models.ManyToManyField(to='jury.Juror'),
        ),
    ]
