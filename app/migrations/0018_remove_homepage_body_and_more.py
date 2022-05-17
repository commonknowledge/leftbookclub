# Generated by Django 4.0.4 on 2022-04-27 13:49

import modelcluster.fields
import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0017_membershipplanpage_homepage_layout_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="homepage",
            name="body",
        ),
        migrations.RemoveField(
            model_name="membershipplanpage",
            name="active",
        ),
        migrations.AlterField(
            model_name="homepage",
            name="layout",
            field=wagtail.fields.StreamField(
                [
                    (
                        "heading",
                        wagtail.blocks.CharBlock(form_classname="full title"),
                    ),
                    ("paragraph", wagtail.blocks.RichTextBlock()),
                    (
                        "membership_options",
                        wagtail.blocks.StructBlock(
                            [
                                (
                                    "heading",
                                    wagtail.blocks.CharBlock(
                                        blank=True,
                                        default="Choose your plan",
                                        form_classname="full title",
                                        null=True,
                                    ),
                                ),
                                (
                                    "description",
                                    wagtail.blocks.RichTextBlock(
                                        blank=True,
                                        default="<p>Your subscription will begin with the most recently published book in your chosen collection.</p>",
                                        null=True,
                                    ),
                                ),
                                (
                                    "plans",
                                    wagtail.blocks.ListBlock(
                                        wagtail.blocks.PageChooserBlock(
                                            can_choose_root=False,
                                            page_type=["app.MembershipPlanPage"],
                                        )
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
        migrations.AlterField(
            model_name="membershipplanpage",
            name="products",
            field=modelcluster.fields.ParentalManyToManyField(
                blank=True, to="app.lbcproduct"
            ),
        ),
    ]
