# Generated by Django 4.0.3 on 2022-04-12 17:00

import django.db.models.deletion
import taggit.managers
import wagtail.core.blocks
import wagtail.core.fields
import wagtail.core.models.collections
import wagtail.embeds.blocks
import wagtail.images.models
import wagtail.search.index
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taggit", "0004_alter_taggeditem_content_type_alter_taggeditem_tag"),
        ("wagtailcore", "0066_collection_management_permissions"),
        ("wagtailimages", "0023_add_choose_permissions"),
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
            name="CustomImage",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                (
                    "file",
                    models.ImageField(
                        height_field="height",
                        upload_to=wagtail.images.models.get_upload_to,
                        verbose_name="file",
                        width_field="width",
                    ),
                ),
                ("width", models.IntegerField(editable=False, verbose_name="width")),
                ("height", models.IntegerField(editable=False, verbose_name="height")),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="created at"
                    ),
                ),
                ("focal_point_x", models.PositiveIntegerField(blank=True, null=True)),
                ("focal_point_y", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "focal_point_width",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "focal_point_height",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("file_size", models.PositiveIntegerField(editable=False, null=True)),
                (
                    "file_hash",
                    models.CharField(blank=True, editable=False, max_length=40),
                ),
                (
                    "alt_text",
                    models.CharField(
                        default="",
                        help_text="Describe this image as literally as possible. If you can close your eyes, have someone read the alt text to you, and imagine a reasonably accurate version of the image, you're on the right track.",
                        max_length=1024,
                    ),
                ),
                (
                    "collection",
                    models.ForeignKey(
                        default=wagtail.core.models.collections.get_root_collection_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="wagtailcore.collection",
                        verbose_name="collection",
                    ),
                ),
                (
                    "tags",
                    taggit.managers.TaggableManager(
                        blank=True,
                        help_text=None,
                        through="taggit.TaggedItem",
                        to="taggit.Tag",
                        verbose_name="tags",
                    ),
                ),
                (
                    "uploaded_by_user",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="uploaded by user",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=(
                wagtail.images.models.ImageFileMixin,
                wagtail.search.index.Indexed,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="InformationPage",
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
                        ]
                    ),
                ),
                (
                    "cover_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="app.customimage",
                    ),
                ),
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
                        ]
                    ),
                ),
                (
                    "feed_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="ImageRendition",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filter_spec", models.CharField(db_index=True, max_length=255)),
                (
                    "file",
                    models.ImageField(
                        height_field="height",
                        upload_to=wagtail.images.models.get_rendition_upload_to,
                        width_field="width",
                    ),
                ),
                ("width", models.IntegerField(editable=False)),
                ("height", models.IntegerField(editable=False)),
                (
                    "focal_point_key",
                    models.CharField(
                        blank=True, default="", editable=False, max_length=16
                    ),
                ),
                (
                    "image",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="renditions",
                        to="app.customimage",
                    ),
                ),
            ],
            options={
                "unique_together": {("image", "filter_spec", "focal_point_key")},
            },
            bases=(wagtail.images.models.ImageFileMixin, models.Model),
        ),
    ]
