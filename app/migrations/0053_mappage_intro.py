# Generated by Django 4.0.7 on 2022-09-15 12:16

import wagtail.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0052_user_coordinates"),
    ]

    operations = [
        migrations.AddField(
            model_name="mappage",
            name="intro",
            field=wagtail.fields.RichTextField(default=""),
            preserve_default=False,
        ),
    ]
