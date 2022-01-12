# Generated by Django 4.0 on 2022-01-12 10:31

import datetime
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0026_alter_meeting_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meeting',
            name='date',
        ),
        migrations.AddField(
            model_name='meeting',
            name='date_end',
            field=models.DateTimeField(default=datetime.datetime(2022, 1, 12, 18, 1, 22, 889034), verbose_name='End date and time of the meeting'),
        ),
        migrations.AddField(
            model_name='meeting',
            name='date_start',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Start date and time of the meeting'),
        ),
    ]