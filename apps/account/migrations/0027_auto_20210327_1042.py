# Generated by Django 3.1.6 on 2021-03-27 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0026_auto_20210220_2117'),
    ]

    operations = [
        migrations.AddField(
            model_name='participationrole',
            name='virtual_name_tag',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='participationrole',
            name='virtual_show_team',
            field=models.BooleanField(default=False),
        ),
    ]
