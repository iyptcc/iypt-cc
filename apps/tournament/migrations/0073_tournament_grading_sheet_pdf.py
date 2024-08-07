# Generated by Django 3.1.6 on 2021-03-11 14:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('printer', '0027_auto_20190408_1159'),
        ('tournament', '0072_tournament_fa_show_grades'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='grading_sheet_pdf',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='grading_sheet', to='printer.pdf'),
        ),
    ]
