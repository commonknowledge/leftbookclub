from wagtail.blocks import CharBlock, ChoiceBlock, IntegerBlock
from wagtail.blocks import ListBlock as WagtailListBlock
from wagtail.blocks import (
    PageChooserBlock,
    RichTextBlock,
    StreamBlock,
    StructBlock,
    URLBlock,
)
from wagtail.embeds.blocks import EmbedBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock

block_features = [
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
]


def ArticleContentStream(block_types=None, **kwargs):
    common_block_types = [
        (
            "text",
            RichTextBlock(
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
        ("embed", EmbedBlock(template="app/content/embed.html")),
    ]

    return StreamField(
        common_block_types + (block_types or []), use_json_field=True, **kwargs
    )


book_types = [
    ("classic", "classic"),
    ("contemporary", "contemporary"),
    ("all-books", "all-books"),
]


class PlanTitleBlock(StructBlock):
    class Meta:
        template = "app/blocks/plan_title_block.html"


class PlanPricingBlock(StructBlock):
    class Meta:
        template = "app/blocks/plan_pricing_block.html"


class SyllabusTitleBlock(StructBlock):
    class Meta:
        template = "app/blocks/syllabus_title_block.html"


class BookTypeChoice(ChoiceBlock):
    choices = book_types

    class Meta:
        default = "all-books"


class BackgroundColourChoiceBlock(ChoiceBlock):
    choices = [
        ("bg-black text-white", "black"),
        ("bg-white", "white"),
        # ('primary', 'primary'),
        ("tw-bg-yellow", "yellow"),
        # ('black', 'black'),
        ("tw-bg-teal", "teal"),
        ("tw-bg-darkgreen", "darkgreen"),
        ("tw-bg-lilacgrey", "lilacgrey"),
        ("tw-bg-coral", "coral"),
        ("tw-bg-purple", "purple"),
        ("tw-bg-magenta", "magenta"),
        ("tw-bg-pink", "pink"),
        ("tw-bg-lightgreen", "lightgreen"),
    ]

    class Meta:
        icon = "fa-paint"


class AlignmentChoiceBlock(ChoiceBlock):
    choices = [
        ("left", "left"),
        ("center", "center"),
        ("right", "right"),
    ]

    class Meta:
        icon = "fa-arrows-h"
        default = "center"


class BootstrapButtonSizeChoiceBlock(ChoiceBlock):
    choices = [
        ("sm", "small"),
        ("md", "medium"),
        ("lg", "large"),
    ]

    class Meta:
        icon = "fa-arrows-alt"
        default = "md"


class BootstrapButtonStyleChoiceBlock(ChoiceBlock):
    choices = [
        ("btn-outline-dark", "outlined"),
        ("btn-dark text-yellow", "filled"),
    ]

    class Meta:
        default = "btn-outline-dark"


class PlanBlock(StructBlock):
    plan = PageChooserBlock(
        page_type="app.membershipplanpage",
        target_model="app.membershipplanpage",
        can_choose_root=False,
    )
    background_color = BackgroundColourChoiceBlock(required=False)
    promotion_label = CharBlock(
        required=False, help_text="Label that highlights this product"
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["request_price"] = value["plan"].get_price_for_request(
            parent_context.get("request")
        )
        return context

    class Meta:
        template = "app/blocks/membership_option_card.html"
        icon = "fa-money"


class MembershipOptionsBlock(StructBlock):
    heading = CharBlock(
        required=False,
        form_classname="full title",
        default="Choose your plan",
    )
    description = RichTextBlock(
        required=False,
        default="<p>Your subscription will begin with the most recently published book in your chosen collection.</p>",
    )
    plans = WagtailListBlock(PlanBlock)

    class Meta:
        template = "app/blocks/membership_options_grid.html"
        icon = "fa-users"


class ButtonBlock(StructBlock):
    text = CharBlock(max_length=100, required=False)
    page = PageChooserBlock(required=False, help_text="Pick a page or specify a URL")
    href = URLBlock(
        required=False, help_text="Pick a page or specify a URL", label="URL"
    )
    size = BootstrapButtonSizeChoiceBlock(required=False, default="md")
    style = BootstrapButtonStyleChoiceBlock(required=False, default="btn-outline-dark")

    class Meta:
        template = "app/blocks/cta.html"


class HeroTextBlock(StructBlock):
    heading = CharBlock(max_length=250, form_classname="full title")
    background_color = BackgroundColourChoiceBlock(required=False)
    button = ButtonBlock(required=False)

    class Meta:
        template = "app/blocks/hero_block.html"
        icon = "fa fa-alphabet"


class ListItemBlock(StructBlock):
    title = CharBlock(max_length=250, form_classname="full title")
    image = ImageChooserBlock(required=False)
    image_css = CharBlock(max_length=500, required=False)
    caption = RichTextBlock(max_length=500)
    background_color = BackgroundColourChoiceBlock(required=False)
    button = ButtonBlock(required=False)

    class Meta:
        template = "app/blocks/list_item_block.html"
        icon = "fa fa-alphabet"


class ColumnWidthChoiceBlock(ChoiceBlock):
    choices = [
        ("small", "small"),
        ("medium", "medium"),
        ("large", "large"),
    ]

    class Meta:
        icon = "fa-arrows-alt"
        default = "small"


class ListBlock(StructBlock):
    column_width = ColumnWidthChoiceBlock()
    items = WagtailListBlock(ListItemBlock)

    class Meta:
        template = "app/blocks/list_block.html"
        icon = "fa fa-alphabet"


class FeaturedBookBlock(StructBlock):
    book = PageChooserBlock(
        page_type="app.bookpage",
        target_model="app.bookpage",
        can_choose_root=False,
    )
    background_color = BackgroundColourChoiceBlock(required=False)
    promotion_label = CharBlock(
        required=False, help_text="Label that highlights this product"
    )
    description = RichTextBlock(
        required=False,
        help_text="This will replace the book's default description. You can use this to provide a more contextualised description of the book",
    )

    class Meta:
        template = "app/blocks/featured_book_block.html"
        icon = "fa fa-book"


class FeaturedProductBlock(StructBlock):
    product = PageChooserBlock(
        page_type="app.merchandisepage",
        target_model="app.merchandisepage",
        can_choose_root=False,
    )
    background_color = BackgroundColourChoiceBlock(required=False)
    promotion_label = CharBlock(
        required=False, help_text="Label that highlights this product"
    )
    description = RichTextBlock(
        required=False,
        help_text="This will replace the product's default description. You can use this to provide a more contextualised description of the product",
    )

    class Meta:
        template = "app/blocks/featured_product_block.html"
        icon = "fa fa-shopping-cart"


class BookGridBlock(StructBlock):
    column_width = ColumnWidthChoiceBlock()

    class Meta:
        template = "app/blocks/book_grid_block.html"
        icon = "fa fa-book"


class ProductGridBlock(StructBlock):
    column_width = ColumnWidthChoiceBlock()

    class Meta:
        template = "app/blocks/product_grid_block.html"
        icon = "fa fa-shopping-cart"


class SelectedBooksBlock(BookGridBlock):
    books = WagtailListBlock(
        PageChooserBlock(
            page_type="app.bookpage",
            target_model="app.bookpage",
            can_choose_root=False,
        )
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["books"] = value["books"]
        return context


class SelectedProductsBlock(ProductGridBlock):
    products = WagtailListBlock(
        PageChooserBlock(
            page_type="app.merchandisepage",
            target_model="app.merchandisepage",
            can_choose_root=False,
        )
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["products"] = list(value["products"])
        return context


class RecentlyPublishedBooks(BookGridBlock):
    max_books = IntegerBlock(default=4, help_text="How many books should show up?")
    type = BookTypeChoice(default="all-books")

    def get_context(self, value, parent_context=None):
        from app.models.wagtail import BookPage

        context = super().get_context(value, parent_context)
        filters = {}
        if value["type"] != None and value["type"] != "all-books":
            filters["type"] = value["type"]
        context["books"] = (
            BookPage.objects.order_by("-published_date")
            .live()
            .public()
            .filter(published_date__isnull=False, **filters)
            .all()[: value["max_books"]]
        )
        return context


class FullProductList(ProductGridBlock):
    max_products = IntegerBlock(
        default=10, help_text="How many products should show up?"
    )

    def get_context(self, value, parent_context=None):
        from app.models.wagtail import MerchandisePage

        context = super().get_context(value, parent_context)
        context["products"] = list(
            MerchandisePage.objects.live().public().all()[: value["max_products"]]
        )
        return context


class YourBooks(BookGridBlock):
    class Meta:
        template = "app/blocks/your_books_grid_block.html"
        icon = "fa fa-book"


class SingleBookBlock(StructBlock):
    book = PageChooserBlock(
        page_type="app.bookpage",
        target_model="app.bookpage",
        can_choose_root=False,
    )

    class Meta:
        template = "app/blocks/single_book_block.html"
        icon = "fa fa-book"


class NewsletterSignupBlock(StructBlock):
    heading = CharBlock(required=False, max_length=150)

    class Meta:
        template = "app/blocks/newsletter_signup_block.html"
        icon = "fa fa-email"


class ArticleText(StructBlock):
    text = RichTextBlock(form_classname="full", features=block_features)
    alignment = AlignmentChoiceBlock(
        help_text="Doesn't apply when used inside a column."
    )

    class Meta:
        template = "app/blocks/richtext.html"


class ColumnBlock(StructBlock):
    stream_blocks = [
        ("hero_text", HeroTextBlock()),
        ("title_image_caption", ListItemBlock()),
        ("image", ImageChooserBlock()),
        ("single_book", SingleBookBlock()),
        ("membership_plan", PlanBlock()),
        ("richtext", RichTextBlock(features=block_features)),
        ("button", ButtonBlock()),
        ("newsletter_signup", NewsletterSignupBlock()),
    ]
    background_color = BackgroundColourChoiceBlock(required=False)
    content = StreamBlock(stream_blocks, required=False)


class SingleColumnBlock(ColumnBlock):
    column_width = ColumnWidthChoiceBlock()
    alignment = AlignmentChoiceBlock(
        help_text="Doesn't apply when used inside a column."
    )

    class Meta:
        template = "app/blocks/single_column_block.html"
        icon = "fa fa-th-large"


class MultiColumnBlock(StructBlock):
    background_color = BackgroundColourChoiceBlock(required=False)
    columns = WagtailListBlock(ColumnBlock, min_num=1, max_num=5)

    class Meta:
        template = "app/blocks/columns_block.html"
        icon = "fa fa-th-large"


class EventsListBlock(StructBlock):
    number_of_events = IntegerBlock(required=True, default=3)

    def get_context(self, value, parent_context=None):
        from app.models.wagtail import MapPage

        context = super().get_context(value, parent_context)
        context.update(MapPage.get_map_context())
        return context

    class Meta:
        template = "app/blocks/event_list_block.html"
        icon = "fa fa-calendar"


class ReadingGroupsListAndMap(StructBlock):
    title = CharBlock(required=False)
    intro = RichTextBlock(required=False)
    number_of_reading_groups = IntegerBlock(required=True, default=3)

    def get_context(self, value, parent_context=None):
        from app.models.wagtail import MapPage

        context = super().get_context(value, parent_context)
        context.update(MapPage.get_map_context())
        return context

    class Meta:
        template = "app/blocks/reading_groups_list_and_map_block.html"
        icon = "fa fa-map"


def create_streamfield(additional_blocks=None, **kwargs):
    blcks = [
        ("membership_options", MembershipOptionsBlock()),
        ("image", ImageChooserBlock()),
        ("featured_book", FeaturedBookBlock()),
        ("book_selection", SelectedBooksBlock()),
        ("recently_published_books", RecentlyPublishedBooks()),
        ("featured_product", FeaturedProductBlock()),
        ("product_selection", SelectedProductsBlock()),
        ("full_product_list", FullProductList()),
        ("hero_text", HeroTextBlock()),
        ("heading", CharBlock(form_classname="full title")),
        ("richtext", ArticleText()),
        ("list_of_heading_image_text", ListBlock()),
        ("single_column", SingleColumnBlock()),
        ("columns", MultiColumnBlock()),
        ("reading_groups_list_and_map", ReadingGroupsListAndMap()),
        ("events_list_block", EventsListBlock()),
    ]

    if isinstance(additional_blocks, list):
        blcks += additional_blocks

    return StreamField(blcks, null=True, blank=True, use_json_field=True, **kwargs)
