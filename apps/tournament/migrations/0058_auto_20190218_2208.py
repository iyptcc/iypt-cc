# Generated by Django 2.1.5 on 2019-02-18 22:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0057_auto_20190218_2202'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='possiblejuror_ask_experience',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='tournament',
            name='possiblejuror_ask_occupation',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='tournament',
            name='possiblejuror_ask_remark',
            field=models.BooleanField(default=False),
        ),
    ]