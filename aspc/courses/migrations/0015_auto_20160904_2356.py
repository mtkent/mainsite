# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-04 23:56
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_auto_20160904_2350'),
    ]

    operations = [
        migrations.RenameField(
            model_name='section',
            old_name='cached_rating',
            new_name='cached_overall_rating',
        ),
    ]
