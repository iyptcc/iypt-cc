# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-11-11 14:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0008_auto_20170909_2138'),
        ('tournament', '0031_auto_20170909_2203'),
        ('registration', '0005_auto_20171111_1433'),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendeeProperty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('type', models.CharField(blank=True, choices=[('int', 'Integer'), ('string', 'String'), ('datetime', 'datetime'), ('date', 'date'), ('image', 'image'), ('text', 'text')], max_length=30, null=True)),
                ('edit_deadline', models.DateTimeField(blank=True, null=True)),
                ('optional', models.ManyToManyField(related_name='optional_properties', to='account.ParticipationRole')),
                ('required', models.ManyToManyField(related_name='required_properties', to='account.ParticipationRole')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournament.Tournament')),
                ('user_property', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='registration.UserProperty')),
            ],
        ),
        migrations.CreateModel(
            name='AttendeePropertyValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('int_value', models.IntegerField(blank=True, null=True)),
                ('string_value', models.CharField(blank=True, max_length=255, null=True)),
                ('datetime_value', models.DateTimeField(blank=True, null=True)),
                ('date_value', models.DateField(blank=True, null=True)),
                ('image_value', models.ImageField(blank=True, null=True, upload_to='')),
                ('text_value', models.TextField(blank=True, null=True)),
                ('attendee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Attendee')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='registration.AttendeeProperty')),
            ],
        ),
        migrations.AddField(
            model_name='userpropertyvalue',
            name='user',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='account.ActiveUser'),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name='userpropertyvalue',
            name='attendee',
        ),
        migrations.AlterUniqueTogether(
            name='userpropertyvalue',
            unique_together=set([('property', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='attendeepropertyvalue',
            unique_together=set([('property', 'attendee')]),
        ),
    ]