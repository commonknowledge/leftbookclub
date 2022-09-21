# Generated by Django 4.0.7 on 2022-09-21 16:46

import django.contrib.gis.db.models.fields
from django.db import migrations
import wagtail.fields


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0054_circleevent_alter_bookindexpage_layout_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='circleevent',
            name='body_html',
            field=wagtail.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='circleevent',
            name='coordinates',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
    ]
