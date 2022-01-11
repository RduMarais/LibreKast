# Generated by Django 4.0 on 2022-01-06 17:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0012_alter_question_options_question_question_order_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='question',
            name='featured',
        ),
        migrations.RemoveField(
            model_name='question',
            name='is_public',
        ),
        migrations.AddField(
            model_name='question',
            name='is_done',
            field=models.BooleanField(default=False, verbose_name='Question currently asking'),
        ),
    ]