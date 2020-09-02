# Generated by Django 2.2.13 on 2020-08-24 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('options', '0023_require_uri_prefix'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optionset',
            name='conditions',
            field=models.ManyToManyField(blank=True, help_text='The list of conditions evaluated for this option set.', related_name='optionsets', to='conditions.Condition', verbose_name='Conditions'),
        ),
    ]
