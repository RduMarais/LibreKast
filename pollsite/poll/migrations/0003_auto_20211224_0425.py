# Generated by Django 2.1.7 on 2021-12-23 22:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0002_question_is_public'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='choice',
            name='question',
        ),
        migrations.DeleteModel(
            name='Question',
        ),
    ]
