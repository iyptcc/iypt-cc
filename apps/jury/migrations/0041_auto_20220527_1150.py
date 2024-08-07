# Generated by Django 3.2.6 on 2022-05-27 11:50

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plan', '0049_round_reserved_jurors'),
        ('jury', '0040_auto_20220207_1136'),
    ]

    operations = [
        migrations.CreateModel(
            name='GradingCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False, verbose_name='order')),
                ('title', models.CharField(max_length=200)),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GradingGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(db_index=True, editable=False, verbose_name='order')),
                ('name', models.CharField(max_length=200)),
                ('minimum', models.FloatField()),
                ('maximum', models.FloatField()),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan.fightrole')),
            ],
            options={
                'ordering': ('order',),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='GroupGrade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField()),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jury.gradinggroup')),
                ('juror_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jury.jurorsession')),
            ],
        ),
        migrations.CreateModel(
            name='GradingElement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1000)),
                ('start', models.FloatField()),
                ('end', models.FloatField()),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jury.gradingcategory')),
            ],
        ),
        migrations.AddField(
            model_name='gradingcategory',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jury.gradinggroup'),
        ),
        migrations.CreateModel(
            name='CategoryGrade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.FloatField()),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jury.gradingcategory')),
                ('juror_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jury.jurorsession')),
            ],
        ),
    ]
