# Generated by Django 4.0 on 2022-01-17 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_alter_homepage_middesc_alter_homepage_teamdesc_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='homepage',
            name='midDesc',
            field=models.TextField(default='A comprehensive guide to deployment is available on GitHub README. In order to setup LibreKast in an deployment envionment, one needs to setup a web server (such as Apache or Nginx), setup the server for delivering a django app and clone the repository to start the app. Then for deployment a comprehensive checklist is available on GitHub to explain how to seed the application secrets; remove debugging functionalities; create an admin user etc.', max_length=430, verbose_name='Content 1st paragraph'),
        ),
    ]
