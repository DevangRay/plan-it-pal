# Generated by Django 4.1.5 on 2023-04-18 16:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_nbr', models.IntegerField()),
                ('subject', models.CharField(max_length=10)),
                ('catalog_nbr', models.CharField(max_length=10)),
                ('instructor_name', models.CharField(max_length=50)),
                ('title', models.CharField(max_length=200)),
                ('units', models.IntegerField(default=3)),
                ('cart', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='schedule.cart')),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(default='untitled', max_length=40)),
                ('total_units', models.IntegerField(default=0)),
                ('submitted', models.BooleanField(default=False)),
                ('approved', models.BooleanField(default=False)),
                ('approved_date', models.DateTimeField(blank=True, null=True)),
                ('denied_date', models.DateTimeField(blank=True, null=True)),
                ('comment_date', models.DateTimeField(blank=True, null=True)),
                ('status',
                 models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Denied', 'Denied')],
                                  default='Pending', max_length=10)),
                ('comments', models.TextField(blank=True, null=True)),
                ('advisor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                              related_name='schedules_advised', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ScheduleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='schedule.course')),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedule_items', to='schedule.schedule')),
            ],
        ),
        migrations.CreateModel(
            name='CourseTime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('days', models.CharField(max_length=10)),
                ('starting_time', models.CharField(default='00:00', max_length=10)),
                ('ending_time', models.CharField(default='00:00', max_length=10)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='schedule.course')),
            ],
        ),
        migrations.CreateModel(
            name='ClassSearch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('text', models.TextField()),
                ('created_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('published_date', models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
