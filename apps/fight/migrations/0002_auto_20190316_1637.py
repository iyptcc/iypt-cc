# Generated by Django 2.1.5 on 2019-03-16 16:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fight', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='clockstate',
            options={'ordering': ('server_time',)},
        ),
        migrations.AlterField(
            model_name='clockstate',
            name='server_time',
            field=models.DateTimeField(),
        ),
    ]