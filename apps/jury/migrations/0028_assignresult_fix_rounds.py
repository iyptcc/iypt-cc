# Generated by Django 2.0.3 on 2018-07-19 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jury', '0027_juror_bias'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignresult',
            name='fix_rounds',
            field=models.IntegerField(default=0),
        ),
    ]
