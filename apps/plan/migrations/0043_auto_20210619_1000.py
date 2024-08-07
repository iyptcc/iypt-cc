# Generated by Django 3.2.1 on 2021-06-19 10:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0082_origin_timezone'),
        ('team', '0022_team_storage_link'),
        ('plan', '0042_round_currently_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teamplaceholder',
            name='team',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='team.team'),
        ),
        migrations.CreateModel(
            name='RoundPlaceholder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField()),
                ('type', models.CharField(choices=[('s', 'selective PF'), ('f', 'final PF')], default='s', max_length=1)),
                ('time_start', models.DateTimeField(blank=True, null=True)),
                ('time_end', models.DateTimeField(blank=True, null=True)),
                ('round', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='plan.round')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournament.tournament')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('order', 'tournament')},
            },
        ),
    ]
