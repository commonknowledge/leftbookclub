# Generated by Django 4.0.4 on 2022-05-03 12:25

import wagtail.core.blocks
import wagtail.core.fields
import wagtail.images.blocks
from django.db import migrations

import app.models.wagtail


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0033_alter_homepage_layout_alter_informationpage_layout"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homepage",
            name="layout",
            field=wagtail.core.fields.StreamField(
                [
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
                    (
                        "featured_book",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "book",
                                    wagtail.core.blocks.PageChooserBlock(
                                        can_choose_root=False,
                                        page_type=["app.BookPage"],
                                    ),
                                ),
                                (
                                    "background_color",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("bg-black text-white", "black"),
                                            ("bg-white", "white"),
                                            ("tw-bg-yellow", "yellow"),
                                            ("tw-bg-teal", "teal"),
                                            ("tw-bg-darkgreen", "darkgreen"),
                                            ("tw-bg-lilacgrey", "lilacgrey"),
                                            ("tw-bg-coral", "coral"),
                                            ("tw-bg-purple", "purple"),
                                            ("tw-bg-magenta", "magenta"),
                                            ("tw-bg-pink", "pink"),
                                            ("tw-bg-lightgreen", "lightgreen"),
                                        ],
                                        required=False,
                                    ),
                                ),
                                (
                                    "promotion_label",
                                    wagtail.core.blocks.CharBlock(
                                        help_text="Label that highlights this product",
                                        required=False,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "book_selection",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "column_width",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("small", "small"),
                                            ("medium", "medium"),
                                            ("large", "large"),
                                        ]
                                    ),
                                ),
                                (
                                    "books",
                                    wagtail.core.blocks.ListBlock(
                                        wagtail.core.blocks.PageChooserBlock(
                                            can_choose_root=False,
                                            page_type=["app.BookPage"],
                                        )
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "recently_published_books",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "column_width",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("small", "small"),
                                            ("medium", "medium"),
                                            ("large", "large"),
                                        ]
                                    ),
                                ),
                                (
                                    "max_books",
                                    wagtail.core.blocks.IntegerBlock(
                                        default=4,
                                        help_text="How many books should show up?",
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "hero_text",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "heading",
                                    wagtail.core.blocks.CharBlock(
                                        form_classname="full title", max_length=250
                                    ),
                                ),
                                (
                                    "background_color",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("bg-black text-white", "black"),
                                            ("bg-white", "white"),
                                            ("tw-bg-yellow", "yellow"),
                                            ("tw-bg-teal", "teal"),
                                            ("tw-bg-darkgreen", "darkgreen"),
                                            ("tw-bg-lilacgrey", "lilacgrey"),
                                            ("tw-bg-coral", "coral"),
                                            ("tw-bg-purple", "purple"),
                                            ("tw-bg-magenta", "magenta"),
                                            ("tw-bg-pink", "pink"),
                                            ("tw-bg-lightgreen", "lightgreen"),
                                        ],
                                        required=False,
                                    ),
                                ),
                                (
                                    "button",
                                    wagtail.core.blocks.StructBlock(
                                        [
                                            (
                                                "text",
                                                wagtail.core.blocks.CharBlock(
                                                    max_length=15, required=False
                                                ),
                                            ),
                                            (
                                                "page",
                                                wagtail.core.blocks.PageChooserBlock(
                                                    help_text="Pick a page or specify a URL",
                                                    required=False,
                                                ),
                                            ),
                                            (
                                                "href",
                                                wagtail.core.blocks.URLBlock(
                                                    help_text="Pick a page or specify a URL",
                                                    label="URL",
                                                    required=False,
                                                ),
                                            ),
                                            (
                                                "size",
                                                wagtail.core.blocks.ChoiceBlock(
                                                    choices=[
                                                        ("sm", "small"),
                                                        ("md", "medium"),
                                                        ("lg", "large"),
                                                    ],
                                                    required=False,
                                                ),
                                            ),
                                            (
                                                "style",
                                                wagtail.core.blocks.ChoiceBlock(
                                                    choices=[
                                                        (
                                                            "btn-outline-dark",
                                                            "outlined",
                                                        ),
                                                        (
                                                            "btn-dark text-yellow",
                                                            "filled",
                                                        ),
                                                    ],
                                                    required=False,
                                                ),
                                            ),
                                        ],
                                        required=False,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "heading",
                        wagtail.core.blocks.CharBlock(form_classname="full title"),
                    ),
                    (
                        "richtext",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "text",
                                    wagtail.core.blocks.RichTextBlock(
                                        features=[
                                            "h1",
                                            "h2",
                                            "h3",
                                            "h4",
                                            "h5",
                                            "bold",
                                            "italic",
                                            "link",
                                            "ol",
                                            "ul",
                                            "hr",
                                            "link",
                                            "document-link",
                                            "image",
                                            "embed",
                                            "blockquote",
                                        ],
                                        form_classname="full",
                                    ),
                                ),
                                (
                                    "alignment",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("left", "left"),
                                            ("center", "center"),
                                            ("right", "right"),
                                        ],
                                        help_text="Doesn't apply when used inside a column.",
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "list_of_heading_image_text",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "column_width",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("small", "small"),
                                            ("medium", "medium"),
                                            ("large", "large"),
                                        ]
                                    ),
                                ),
                                (
                                    "items",
                                    wagtail.core.blocks.ListBlock(
                                        app.models.wagtail.ListItemBlock
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "columns",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "background_color",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("bg-black text-white", "black"),
                                            ("bg-white", "white"),
                                            ("tw-bg-yellow", "yellow"),
                                            ("tw-bg-teal", "teal"),
                                            ("tw-bg-darkgreen", "darkgreen"),
                                            ("tw-bg-lilacgrey", "lilacgrey"),
                                            ("tw-bg-coral", "coral"),
                                            ("tw-bg-purple", "purple"),
                                            ("tw-bg-magenta", "magenta"),
                                            ("tw-bg-pink", "pink"),
                                            ("tw-bg-lightgreen", "lightgreen"),
                                        ],
                                        required=False,
                                    ),
                                ),
                                (
                                    "columns",
                                    wagtail.core.blocks.ListBlock(
                                        app.models.wagtail.ColumnBlock,
                                        max_num=5,
                                        min_num=1,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    ("newsletter_signup", wagtail.core.blocks.StructBlock([])),
                ],
                blank=True,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="informationpage",
            name="layout",
            field=wagtail.core.fields.StreamField(
                [
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
                    (
                        "featured_book",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "book",
                                    wagtail.core.blocks.PageChooserBlock(
                                        can_choose_root=False,
                                        page_type=["app.BookPage"],
                                    ),
                                ),
                                (
                                    "background_color",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("bg-black text-white", "black"),
                                            ("bg-white", "white"),
                                            ("tw-bg-yellow", "yellow"),
                                            ("tw-bg-teal", "teal"),
                                            ("tw-bg-darkgreen", "darkgreen"),
                                            ("tw-bg-lilacgrey", "lilacgrey"),
                                            ("tw-bg-coral", "coral"),
                                            ("tw-bg-purple", "purple"),
                                            ("tw-bg-magenta", "magenta"),
                                            ("tw-bg-pink", "pink"),
                                            ("tw-bg-lightgreen", "lightgreen"),
                                        ],
                                        required=False,
                                    ),
                                ),
                                (
                                    "promotion_label",
                                    wagtail.core.blocks.CharBlock(
                                        help_text="Label that highlights this product",
                                        required=False,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "book_selection",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "column_width",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("small", "small"),
                                            ("medium", "medium"),
                                            ("large", "large"),
                                        ]
                                    ),
                                ),
                                (
                                    "books",
                                    wagtail.core.blocks.ListBlock(
                                        wagtail.core.blocks.PageChooserBlock(
                                            can_choose_root=False,
                                            page_type=["app.BookPage"],
                                        )
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "recently_published_books",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "column_width",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("small", "small"),
                                            ("medium", "medium"),
                                            ("large", "large"),
                                        ]
                                    ),
                                ),
                                (
                                    "max_books",
                                    wagtail.core.blocks.IntegerBlock(
                                        default=4,
                                        help_text="How many books should show up?",
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "hero_text",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "heading",
                                    wagtail.core.blocks.CharBlock(
                                        form_classname="full title", max_length=250
                                    ),
                                ),
                                (
                                    "background_color",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("bg-black text-white", "black"),
                                            ("bg-white", "white"),
                                            ("tw-bg-yellow", "yellow"),
                                            ("tw-bg-teal", "teal"),
                                            ("tw-bg-darkgreen", "darkgreen"),
                                            ("tw-bg-lilacgrey", "lilacgrey"),
                                            ("tw-bg-coral", "coral"),
                                            ("tw-bg-purple", "purple"),
                                            ("tw-bg-magenta", "magenta"),
                                            ("tw-bg-pink", "pink"),
                                            ("tw-bg-lightgreen", "lightgreen"),
                                        ],
                                        required=False,
                                    ),
                                ),
                                (
                                    "button",
                                    wagtail.core.blocks.StructBlock(
                                        [
                                            (
                                                "text",
                                                wagtail.core.blocks.CharBlock(
                                                    max_length=15, required=False
                                                ),
                                            ),
                                            (
                                                "page",
                                                wagtail.core.blocks.PageChooserBlock(
                                                    help_text="Pick a page or specify a URL",
                                                    required=False,
                                                ),
                                            ),
                                            (
                                                "href",
                                                wagtail.core.blocks.URLBlock(
                                                    help_text="Pick a page or specify a URL",
                                                    label="URL",
                                                    required=False,
                                                ),
                                            ),
                                            (
                                                "size",
                                                wagtail.core.blocks.ChoiceBlock(
                                                    choices=[
                                                        ("sm", "small"),
                                                        ("md", "medium"),
                                                        ("lg", "large"),
                                                    ],
                                                    required=False,
                                                ),
                                            ),
                                            (
                                                "style",
                                                wagtail.core.blocks.ChoiceBlock(
                                                    choices=[
                                                        (
                                                            "btn-outline-dark",
                                                            "outlined",
                                                        ),
                                                        (
                                                            "btn-dark text-yellow",
                                                            "filled",
                                                        ),
                                                    ],
                                                    required=False,
                                                ),
                                            ),
                                        ],
                                        required=False,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "heading",
                        wagtail.core.blocks.CharBlock(form_classname="full title"),
                    ),
                    (
                        "richtext",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "text",
                                    wagtail.core.blocks.RichTextBlock(
                                        features=[
                                            "h1",
                                            "h2",
                                            "h3",
                                            "h4",
                                            "h5",
                                            "bold",
                                            "italic",
                                            "link",
                                            "ol",
                                            "ul",
                                            "hr",
                                            "link",
                                            "document-link",
                                            "image",
                                            "embed",
                                            "blockquote",
                                        ],
                                        form_classname="full",
                                    ),
                                ),
                                (
                                    "alignment",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("left", "left"),
                                            ("center", "center"),
                                            ("right", "right"),
                                        ],
                                        help_text="Doesn't apply when used inside a column.",
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "list_of_heading_image_text",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "column_width",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("small", "small"),
                                            ("medium", "medium"),
                                            ("large", "large"),
                                        ]
                                    ),
                                ),
                                (
                                    "items",
                                    wagtail.core.blocks.ListBlock(
                                        app.models.wagtail.ListItemBlock
                                    ),
                                ),
                            ]
                        ),
                    ),
                    (
                        "columns",
                        wagtail.core.blocks.StructBlock(
                            [
                                (
                                    "background_color",
                                    wagtail.core.blocks.ChoiceBlock(
                                        choices=[
                                            ("bg-black text-white", "black"),
                                            ("bg-white", "white"),
                                            ("tw-bg-yellow", "yellow"),
                                            ("tw-bg-teal", "teal"),
                                            ("tw-bg-darkgreen", "darkgreen"),
                                            ("tw-bg-lilacgrey", "lilacgrey"),
                                            ("tw-bg-coral", "coral"),
                                            ("tw-bg-purple", "purple"),
                                            ("tw-bg-magenta", "magenta"),
                                            ("tw-bg-pink", "pink"),
                                            ("tw-bg-lightgreen", "lightgreen"),
                                        ],
                                        required=False,
                                    ),
                                ),
                                (
                                    "columns",
                                    wagtail.core.blocks.ListBlock(
                                        app.models.wagtail.ColumnBlock,
                                        max_num=5,
                                        min_num=1,
                                    ),
                                ),
                            ]
                        ),
                    ),
                    ("newsletter_signup", wagtail.core.blocks.StructBlock([])),
                ],
                blank=True,
                null=True,
            ),
        ),
    ]