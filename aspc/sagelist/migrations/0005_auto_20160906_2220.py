# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-06 22:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sagelist', '0004_auto_20160906_0057'),
    ]

    operations = [
        migrations.AlterField(
            model_name='booksale',
            name='amazon_info',
            field=models.TextField(blank=True, null=True),
        ),
    ]