# Generated by Django 2.1.5 on 2019-02-25 20:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registration', '0043_auto_20190222_2046'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationquestion',
            name='required_if',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='registration.ApplicationQuestion'),
        ),
    ]