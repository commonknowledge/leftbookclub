# Generated by Django 4.0.4 on 2022-05-07 19:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0042_alter_bookindexpage_layout_alter_homepage_layout_and_more"),
    ]

    operations = [
        migrations.DeleteModel(
            name="FeaturedContent",
        ),
    ]
