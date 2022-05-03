# Generated by Django 4.0.4 on 2022-05-03 12:45

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0034_alter_homepage_layout_alter_informationpage_layout"),
    ]

    operations = [
        migrations.AlterField(
            model_name="legacygifts",
            name="giving_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="legacy_gifts_given",
                to=settings.AUTH_USER_MODEL,
                to_field="old_id",
            ),
        ),
    ]
