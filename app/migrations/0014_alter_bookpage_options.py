# Generated by Django 4.0.4 on 2022-04-15 02:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0013_alter_bookpage_options_bookpage_published_date"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="bookpage",
            options={"ordering": ["published_date"]},
        ),
    ]
