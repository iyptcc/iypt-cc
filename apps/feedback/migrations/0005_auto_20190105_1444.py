# Generated by Django 2.1.2 on 2019-01-05 14:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0004_auto_20181110_1643'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedback',
            options={'permissions': (('change_all_feedback', 'Can change any feedback'), ('stats', 'Can see feedback statistics'))},
        ),
    ]
