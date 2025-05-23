# Generated by Django 4.0.8 on 2023-03-21 12:49

import django.core.validators
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0064_reviewfeesettings_donation_text_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="upsellplansettings",
            options={"verbose_name": "Review Fee Settings"},
        ),
        migrations.AddField(
            model_name="upsellplansettings",
            name="upgrade_membership_text",
            field=wagtail.fields.RichTextField(
                default="\n    <p>Here is some text that can be edited blah blah blah</p>\n    "
            ),
        ),
        migrations.AlterField(
            model_name="membershipplanpage",
            name="deliveries_per_year",
            field=models.PositiveIntegerField(
                default=0, validators=[django.core.validators.MinValueValidator(0)]
            ),
        ),
        migrations.AlterField(
            model_name="upsellplansettings",
            name="intro_text",
            field=wagtail.fields.RichTextField(
                default="\n    <h1>Review your fee</h1>\n    <p>Since you signed up, our operating costs have increased dramatically due to the economic times we’re all living through.</p>\n    <p>We’ve increased the price of new memberships and protected your fee, but we are beginning to struggle. Can you afford to increase your membership fee?</p>\n    "
            ),
        ),
    ]
