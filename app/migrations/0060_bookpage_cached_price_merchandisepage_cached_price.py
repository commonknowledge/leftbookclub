# Generated by Django 4.0.7 on 2022-11-14 10:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0059_alter_bookindexpage_layout_alter_bookpage_layout_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="bookpage",
            name="cached_price",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="merchandisepage",
            name="cached_price",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
