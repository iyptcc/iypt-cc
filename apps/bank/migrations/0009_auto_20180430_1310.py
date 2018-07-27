# Generated by Django 2.0.3 on 2018-04-30 13:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0020_participationrole_attending'),
        ('team', '0018_auto_20180314_1814'),
        ('bank', '0008_auto_20180410_1352'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='ref_property',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='bank.PropertyFee'),
        ),
        migrations.AddField(
            model_name='payment',
            name='ref_role',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='account.ParticipationRole'),
        ),
        migrations.AddField(
            model_name='payment',
            name='ref_team',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='team.Team'),
        ),
        migrations.AddField(
            model_name='payment',
            name='ref_type',
            field=models.CharField(blank=True, choices=[('team', 'Team'), ('role', 'Role'), ('property', 'Property')], max_length=3, null=True),
        ),
    ]