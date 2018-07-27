# Generated by Django 2.0.3 on 2018-05-04 11:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank', '0011_account_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='ref_type',
            field=models.CharField(blank=True, choices=[('team', 'Team'), ('role', 'Role'), ('property', 'Property')], max_length=30, null=True),
        ),
    ]