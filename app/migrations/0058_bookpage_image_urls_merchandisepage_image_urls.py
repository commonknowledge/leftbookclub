# Generated by Django 4.0.7 on 2022-11-01 09:00

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0057_merchandisepage_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookpage",
            name="image_urls",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.URLField(blank=True, max_length=500),
                blank=True,
                null=True,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="merchandisepage",
            name="image_urls",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.URLField(blank=True, max_length=500),
                blank=True,
                null=True,
                size=None,
            ),
        ),
    ]
