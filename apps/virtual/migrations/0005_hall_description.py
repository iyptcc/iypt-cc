# Generated by Django 3.1.6 on 2021-02-24 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('virtual', '0004_auto_20210224_2155'),
    ]

    operations = [
        migrations.AddField(
            model_name='hall',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]