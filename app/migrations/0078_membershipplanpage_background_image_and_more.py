# Generated by Django 4.2 on 2024-01-16 15:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0077_membershipplanpage_product_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershipplanpage",
            name="background_image",
            field=models.ForeignKey(
                blank=True,
                help_text="1400 x 1024 optimal resolution.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="app.customimage",
            ),
        ),
        migrations.AlterField(
            model_name="membershipplanpage",
            name="product_image",
            field=models.ForeignKey(
                blank=True,
                help_text="600 x 300 optimal resolution.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="app.customimage",
            ),
        ),
    ]
