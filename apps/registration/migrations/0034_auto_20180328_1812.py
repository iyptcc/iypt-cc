# Generated by Django 2.0.3 on 2018-03-28 18:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0033_auto_20180328_1812'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userpropertyvalue',
            old_name='user_property',
            new_name='property',
        ),
    ]
