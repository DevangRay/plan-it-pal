# Generated by Django 4.1.7 on 2023-04-14 19:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0007_alter_schedule_status_alter_scheduleitem_schedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='approved_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schedule',
            name='comment_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schedule',
            name='denied_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]