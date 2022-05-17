# Generated by Django 4.0.4 on 2022-04-27 14:33

import wagtail.core.blocks
import wagtail.core.fields
import wagtail.images.blocks
from django.db import migrations

import app.models.wagtail


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0018_remove_homepage_body_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepage",
            name="layout",
            field=wagtail.core.fields.StreamField(
                [
                    (
                        "heading",
                        wagtail.core.blocks.CharBlock(form_classname="full title"),
                    ),
                    ("paragraph", wagtail.core.blocks.RichTextBlock()),
                    (
                        "membership_options",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "heading",
                                    wagtail.core.blocks.CharBlock(
                                        blank=True,
                                        default="Choose your plan",
                                        form_classname="full title",
                                        null=True,
                                    ),
                                ),
                                (
                                    "description",
                                    wagtail.core.blocks.RichTextBlock(
                                        blank=True,
                                        default="<p>Your subscription will begin with the most recently published book in your chosen collection.</p>",
                                        null=True,
                                    ),
                                ),
                                (
                                    "plans",
                                    wagtail.core.blocks.ListBlock(
                                        app.models.wagtail.PlanBlock
                                    ),
                                ),
                            ]
                        ),
                    ),
                    ("image", wagtail.images.blocks.ImageChooserBlock()),
                ],
                blank=True,
                null=True,
            ),
        ),
    ]
