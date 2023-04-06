# Generated by Django 4.1.7 on 2023-04-06 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0005_schedule_comments_schedule_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Denied', 'Denied')], default='pending', max_length=10),
        ),
    ]
