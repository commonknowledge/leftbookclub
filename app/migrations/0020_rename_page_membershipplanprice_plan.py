# Generated by Django 4.0.4 on 2022-04-28 06:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0019_alter_homepage_layout"),
    ]

    operations = [
        migrations.RenameField(
            model_name="membershipplanprice",
            old_name="page",
            new_name="plan",
        ),
    ]
