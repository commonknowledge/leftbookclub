# Generated by Django 4.0.4 on 2022-04-28 09:57

import wagtail.core.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0021_membershipplanpage_pick_product_title_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipplanprice",
            name="description",
            field=wagtail.core.fields.RichTextField(blank=True, null=True),
        ),
    ]
