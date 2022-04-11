# Generated by Django 4.0.3 on 2022-04-11 10:56

import django.db.models.deletion
import wagtail.core.blocks
import wagtail.core.fields
import wagtail.embeds.blocks
import wagtail.images.blocks
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0066_collection_management_permissions"),
        ("app", "0005_alter_featuredcontent_current_book"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogIndexPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                ("intro", wagtail.core.fields.RichTextField(blank=True)),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="BlogPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                ("date", models.DateField(verbose_name="Post date")),
                ("intro", models.CharField(max_length=250)),
                (
                    "body",
                    wagtail.core.fields.StreamField(
                        [
                            (
                                "text",
                                wagtail.core.blocks.RichTextBlock(
                                    features=[
                                        "h3",
                                        "h4",
                                        "bold",
                                        "italic",
                                        "link",
                                        "ol",
                                        "ul",
                                    ],
                                    template="app/content/text.html",
                                ),
                            ),
                            (
                                "embed",
                                wagtail.embeds.blocks.EmbedBlock(
                                    template="app/content/embed.html"
                                ),
                            ),
                            (
                                "image",
                                wagtail.core.blocks.StructBlock(
                                    [
                                        (
                                            "image",
                                            wagtail.images.blocks.ImageChooserBlock(
                                                required=False
                                            ),
                                        ),
                                        ("caption", wagtail.core.blocks.CharBlock()),
                                    ]
                                ),
                            ),
                        ]
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
    ]
