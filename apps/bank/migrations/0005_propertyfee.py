# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2018-02-15 12:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0030_auto_20180214_0930'),
        ('bank', '0004_payment_aborted_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='PropertyFee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('if_not_true', models.ManyToManyField(related_name='not_true_propertyfee', to='registration.AttendeeProperty')),
                ('if_true', models.ManyToManyField(related_name='true_propertyfee', to='registration.AttendeeProperty')),
            ],
        ),
    ]
