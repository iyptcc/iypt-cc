# Generated by Django 3.1.6 on 2021-02-24 21:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0026_auto_20210220_2117'),
        ('virtual', '0002_auto_20210224_2033'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='hallrole',
            unique_together={('hall', 'role')},
        ),
    ]
