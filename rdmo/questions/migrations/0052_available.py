# Generated by Django 2.2.13 on 2020-08-20 14:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0051_sites_blank'),
    ]

    operations = [
        migrations.AddField(
            model_name='catalog',
            name='available',
            field=models.BooleanField(default=True, help_text='Designates whether this catalog is generally available for projects.', verbose_name='Available'),
        ),
    ]