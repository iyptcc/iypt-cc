# Generated by Django 2.0.3 on 2018-03-28 18:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0032_auto_20180327_0801'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userpropertyvalue',
            old_name='property',
            new_name='user_property',
        ),
    ]
