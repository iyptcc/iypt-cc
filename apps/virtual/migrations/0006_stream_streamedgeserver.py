# Generated by Django 3.1.6 on 2021-04-02 13:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0075_tournament_fight_room_guest_policy'),
        ('virtual', '0005_hall_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='Stream',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='Name')),
                ('stream_name', models.CharField(blank=True, max_length=200, null=True)),
                ('hls_format', models.CharField(blank=True, max_length=1024, null=True)),
                ('mpd_format', models.CharField(blank=True, max_length=1024, null=True)),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournament.tournament')),
            ],
        ),
        migrations.CreateModel(
            name='StreamEdgeServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(max_length=1024)),
                ('stream', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='virtual.stream')),
            ],
        ),
    ]
