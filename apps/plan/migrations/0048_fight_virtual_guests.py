# Generated by Django 3.2.1 on 2021-07-16 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('virtual', '0009_bbbguest'),
        ('plan', '0047_fight_virtual_attendees'),
    ]

    operations = [
        migrations.AddField(
            model_name='fight',
            name='virtual_guests',
            field=models.ManyToManyField(blank=True, to='virtual.BBBGuest'),
        ),
    ]
