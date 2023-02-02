import time
import urllib.parse
from datetime import datetime
from importlib.metadata import metadata
from urllib.parse import urlencode

import djstripe.models
import shopify
import stripe
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from django.http.response import Http404
from django.shortcuts import get_object_or_404, redirect
from django.templatetags.static import static
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.html import strip_tags
from django_countries import countries
from djmoney.models.fields import Money, MoneyField
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.models import ClusterableModel
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
    FieldRowPanel,
    HelpPanel,
    InlinePanel,
    MultiFieldPanel,
    PageChooserPanel,
    StreamFieldPanel,
)
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.models import Orderable, Page, Site
from wagtail.rich_text import get_text_for_indexing
from wagtail.search import index
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.snippets.models import register_snippet
from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtailcache.cache import WagtailCacheMixin, cache_page
from wagtailseo import utils
from wagtailseo.models import SeoMixin, SeoType, TwitterCard

from app.forms import CountrySelectorForm
from app.models.blocks import ArticleContentStream
from app.models.circle import CircleEvent
from app.models.django import User
from app.utils import include_keys
from app.utils.abstract_model_querying import abstract_page_query_filter
from app.utils.cache import django_cached
from app.utils.shopify import metafields_to_dict
from app.utils.stripe import create_shipping_zone_metadata, get_shipping_product

from .stripe import LBCProduct, ShippingZone

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


class SeoMetadataMixin(SeoMixin, Page):
    class Meta:
        abstract = True

    promote_panels = SeoMixin.seo_panels

    seo_image_sources = ["og_image", "homepage_seo_image"]  # Explicit sharing image

    seo_description_sources = [
        "search_description",  # Explicit sharing description
        "homepage_search_description",
    ]

    @property
    def homepage_search_description(self):
        home = HomePage.objects.first()
        return home.search_description

    @property
    def homepage_seo_image(self):
        home = HomePage.objects.first()
        return home.og_image

    @property
    def seo_image_url(self) -> str:
        """
        Gets the absolute URL for the primary Open Graph image of this page.
        """
        base_url = utils.get_absolute_media_url(self.get_site())

        url = static("images/sharecard.png")

        if self.seo_image:
            url = self.seo_image.get_rendition("original").url

        return utils.ensure_absolute_url(url, base_url)

    @property
    def seo_description(self) -> str:
        """
        Middleware for seo_description_sources
        """
        for attr in self.seo_description_sources:
            if hasattr(self, attr):
                text = getattr(self, attr)
                if text:
                    # Strip HTML if there is any
                    return get_text_for_indexing(text)
        return ""


class IndexPageSeoMixin(SeoMetadataMixin):
    class Meta:
        abstract = True

    seo_content_type = SeoType.WEBSITE
    seo_twitter_card = TwitterCard.LARGE
    promote_panels = SeoMixin.seo_panels


class ArticleSeoMixin(SeoMetadataMixin):
    class Meta:
        abstract = True

    seo_content_type = SeoType.ARTICLE
    seo_twitter_card = TwitterCard.SUMMARY
    promote_panels = SeoMixin.seo_panels


# class ProductBlock(StructBlock):
#     page = ParentalKey("app.MembershipPlanPage", related_name="products")
#     product = SnippetChooserBlock(djstripe.models.LBCProduct)


@register_snippet
class MembershipPlanPrice(Orderable, ClusterableModel):
    # name = models.CharField(max_length=150, blank=True)
    plan = ParentalKey("app.MembershipPlanPage", related_name="prices")

    price = MoneyField(
        default=Money(0, "GBP"),
        max_digits=14,
        decimal_places=2,
        default_currency="GBP",
        null=False,
        blank=False,
    )

    class Interval(models.TextChoices):
        year = "year"
        month = "month"
        week = "week"
        day = "day"

    interval = models.CharField(
        max_length=10,
        choices=Interval.choices,
        default=Interval.month,
        null=False,
        blank=True,
    )

    interval_count = models.IntegerField(default=1, null=False, blank=True)

    description = RichTextField(null=True, blank=True)

    free_shipping_zones = ParentalManyToManyField(
        ShippingZone,
        related_name="excluded_prices",
        help_text="Waive shipping fees for customers in these shipping zones.",
        blank=True,
    )

    should_advertise_postage_price = models.BooleanField(
        default=True,
        help_text="Whether to advertise that the price is + p&p, before the shipping zone is known.",
    )

    products = ParentalManyToManyField(
        LBCProduct,
        blank=True,
        help_text="The stripe product that the user will be subscribed to. If multiple products are set here, then the user will be asked to pick which one they want, e.g. Classic or Contemporary books.",
    )

    panels = [
        FieldRowPanel(
            [
                FieldPanel("price"),
            ]
        ),
        MultiFieldPanel(
            [
                AutocompletePanel("products", target_model=LBCProduct),
            ],
            heading="Product",
        ),
        FieldRowPanel(
            [
                FieldPanel("interval_count"),
                FieldPanel("interval"),
            ],
            heading="billing schedule",
        ),
        MultiFieldPanel(
            [
                FieldPanel("should_advertise_postage_price"),
                AutocompletePanel("free_shipping_zones", target_model=ShippingZone),
            ],
            heading="Shipping fees",
        ),
        FieldPanel(
            "description",
            classname="full",
            help_text="Displayed to visitors who are considering purchasing a plan at this price.",
        ),
    ]

    @property
    def deliveries_per_billing_period(self) -> float:
        if self.interval == "year":
            return self.plan.deliveries_per_year * self.interval_count
        if self.interval == "month":
            return (self.plan.deliveries_per_year / 12) * self.interval_count
        if self.interval == "week":
            return (self.plan.deliveries_per_year / 52) * self.interval_count
        if self.interval == "day":
            return (self.plan.deliveries_per_year / 365.25) * self.interval_count
        return self.plan.deliveries_per_year

    def shipping_fee(self, zone) -> Money:
        if self.free_shipping_zones.filter(code=zone.code).exists():
            return Money(0, zone.rate_currency)
        return zone.rate * self.deliveries_per_billing_period

    def price_including_shipping(self, zone):
        return self.price + self.shipping_fee(zone)

    def humanised_interval(self):
        s = "/"
        if self.interval_count > 1:
            s += self.interval_count + " "
        s += self.interval
        if self.interval_count > 1:
            s += "s"
        return s

    @property
    def price_string(self) -> str:
        money = str(self.price)
        interval = self.humanised_interval()
        s = f"{money}{interval}"
        if self.should_advertise_postage_price:
            return f"{s} + p&p"
        return s

    @property
    def months_per_billing_cycle(self):
        if self.interval == "year":
            return 12 * self.interval_count
        if self.interval == "month":
            return self.interval_count
        if self.interval == "week":
            return self.interval_count / (52 / 7)
        if self.interval == "day":
            return self.interval_count / (365.25 / 12)

    @property
    def equivalent_monthly_price(self) -> str:
        return self.price / self.months_per_billing_cycle

    @property
    def equivalent_monthly_price_string(self) -> str:
        money = str(self.equivalent_monthly_price)
        s = f"{money}/month"
        if self.should_advertise_postage_price:
            return f"{s} + p&p"
        return s

    def __str__(self) -> str:
        return f"{self.price_string} on {self.plan}"

    @property
    def metadata(self):
        return {"wagtail_price": self.id}

    def to_price_data(self, product):
        return {
            "unit_amount_decimal": self.price.amount * 100,
            "currency": self.price_currency,
            "product": product.id,
            "recurring": {
                "interval": self.interval,
                "interval_count": self.interval_count,
            },
            "metadata": {**(self.metadata or {}), "primary": True},
        }

    def to_shipping_price_data(self, zone):
        shipping_product = get_shipping_product()
        shipping_fee = self.shipping_fee(zone)
        return {
            "unit_amount_decimal": shipping_fee.amount * 100,
            "currency": shipping_fee.currency,
            "product": shipping_product.id,
            "recurring": {
                "interval": self.interval,
                "interval_count": self.interval_count,
            },
            "metadata": {
                **create_shipping_zone_metadata(zone),
                "deliveries_per_period": self.deliveries_per_billing_period,
                **self.metadata,
            },
        }

    def to_checkout_line_items(self, zone=None, product=None):
        if product is None and self.products.count() == 1:
            product = self.products.first()
        if product is None:
            raise ValueError("Cannot create line items without a valid product")
        if zone is None:
            raise ValueError("Cannot create line items without a valid zone")

        line_items = [
            {
                "price_data": self.to_price_data(product),
                "quantity": 1,
            },
            # Keep the shipping fee in, even if it's 0
            # so that we can upgrade/downgrade shipping prices in the future
            {
                "price_data": self.to_shipping_price_data(zone),
                "quantity": 1,
            },
        ]
        return line_items

    def upsell(self, product_id: str):
        return Upsell.objects.filter(
            plan=self.plan, from_stripe_product__id=product_id
        ).first()

    def upsell_data(self, product_id: str, country_id):
        try:
            upsell = self.upsell(product_id)
            if upsell is not None and upsell.url() is not None:
                if country_id is not None:
                    return {
                        "description": upsell.description,
                        "url": upsell.url(country_id),
                    }
                return {"description": upsell.description, "url": upsell.url()}
        except:
            return None


@register_snippet
class Upsell(Orderable, ClusterableModel):
    class Meta:
        unique_together = ["plan", "from_stripe_product", "to_stripe_product"]

    plan = ParentalKey(
        "app.MembershipPlanPage",
        on_delete=models.CASCADE,
        related_name="upsells",
        verbose_name="membership plan",
    )

    description = models.CharField(max_length=150)

    from_stripe_product = models.ForeignKey(
        LBCProduct, on_delete=models.CASCADE, related_name="upsells"
    )

    to_stripe_product = models.ForeignKey(
        LBCProduct, on_delete=models.CASCADE, related_name="+"
    )

    panels = [
        FieldPanel("description"),
        AutocompletePanel("plan", target_model="app.MembershipPlanPage"),
        AutocompletePanel("from_stripe_product", target_model=LBCProduct),
        AutocompletePanel("to_stripe_product", target_model=LBCProduct),
    ]

    @property
    def to_price(self):
        return self.plan.prices.filter(products=self.to_stripe_product).first()

    def url(self, country_id=None):
        return reverse(
            "plan_shipping",
            kwargs=dict(
                price_id=self.to_price.id,
                product_id=self.to_stripe_product.id,
                country_id=country_id,
            ),
        )


class PlanTitleBlock(blocks.StructBlock):
    class Meta:
        template = "app/blocks/plan_title_block.html"

    # def get_context(self, value, parent_context=None):
    #     context = super().get_context(value, parent_context)
    #     context['page'] = parent_context['page']
    #     return context


class PlanPricingBlock(blocks.StructBlock):
    class Meta:
        template = "app/blocks/plan_pricing_block.html"

    # def get_context(self, value, parent_context=None):
    #     context = super().get_context(value, parent_context)
    #     context['page'] = parent_context['page']
    #     return context


class BookTypeChoice(blocks.ChoiceBlock):
    choices = [
        ("classic", "classic"),
        ("contemporary", "contemporary"),
        ("all-books", "all-books"),
    ]

    class Meta:
        default = "all-books"


class BackgroundColourChoiceBlock(blocks.ChoiceBlock):
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


class AlignmentChoiceBlock(blocks.ChoiceBlock):
    choices = [
        ("left", "left"),
        ("center", "center"),
        ("right", "right"),
    ]

    class Meta:
        icon = "fa-arrows-h"
        default = "center"


class BootstrapButtonSizeChoiceBlock(blocks.ChoiceBlock):
    choices = [
        ("sm", "small"),
        ("md", "medium"),
        ("lg", "large"),
    ]

    class Meta:
        icon = "fa-arrows-alt"
        default = "md"


class BootstrapButtonStyleChoiceBlock(blocks.ChoiceBlock):
    choices = [
        ("btn-outline-dark", "outlined"),
        ("btn-dark text-yellow", "filled"),
    ]

    class Meta:
        default = "btn-outline-dark"


class PlanBlock(blocks.StructBlock):
    plan = blocks.PageChooserBlock(
        page_type="app.membershipplanpage",
        target_model="app.membershipplanpage",
        can_choose_root=False,
    )
    background_color = BackgroundColourChoiceBlock(required=False)
    promotion_label = blocks.CharBlock(
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


class MembershipOptionsBlock(blocks.StructBlock):
    heading = blocks.CharBlock(
        required=False,
        form_classname="full title",
        default="Choose your plan",
    )
    description = blocks.RichTextBlock(
        required=False,
        default="<p>Your subscription will begin with the most recently published book in your chosen collection.</p>",
    )
    plans = blocks.ListBlock(PlanBlock)

    class Meta:
        template = "app/blocks/membership_options_grid.html"
        icon = "fa-users"


class CustomImage(AbstractImage):

    # Making blank / null explicit because you *really* need alt text
    alt_text = models.CharField(
        max_length=1024,
        blank=False,
        null=False,
        default="",
        help_text="Describe this image as literally as possible. If you can close your eyes, have someone read the alt text to you, and imagine a reasonably accurate version of the image, you're on the right track.",
    )

    admin_form_fields = (
        "file",
        "alt_text",
        "title",
    )


class ImageRendition(AbstractRendition):
    image = models.ForeignKey(
        CustomImage, on_delete=models.CASCADE, related_name="renditions"
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)


@method_decorator(cache_page, name="serve")
class BlogIndexPage(WagtailCacheMixin, IndexPageSeoMixin, Page):
    """
    Define blog index page.
    """

    show_in_menus_default = True

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro", classname="full")]

    seo_description_sources = IndexPageSeoMixin.seo_description_sources + ["intro"]


@method_decorator(cache_page, name="serve")
class BlogPage(WagtailCacheMixin, ArticleSeoMixin, Page):
    """
    Define blog detail page.
    """

    show_in_menus_default = True

    intro = RichTextField(max_length=250)

    feed_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = ArticleContentStream()

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
        StreamFieldPanel("body", classname="full"),
        ImageChooserPanel("feed_image"),
    ]

    seo_description_sources = ArticleSeoMixin.seo_description_sources + ["intro"]

    seo_image_sources = ArticleSeoMixin.seo_image_sources + ["feed_image"]


def shopify_product_id_key(page):
    return page.shopify_product_id


class BaseShopifyProductPage(ArticleSeoMixin, Page):
    class Meta:
        abstract = True

    # TODO: Autocomplete this in future?
    shopify_product_id = models.CharField(max_length=300, blank=False, null=False)
    description = RichTextField(null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    image_urls = ArrayField(
        models.URLField(max_length=500, blank=True), blank=True, null=True
    )
    cached_price = models.FloatField(blank=True, null=True)

    @property
    def primary_image_url(self):
        return (
            self.image_urls[0]
            if self.image_urls is not None and len(self.image_urls) > 0
            else self.image_url
        )

    # Don't allow editing here because it won't be synced back to Shopify
    content_panels = [
        FieldPanel("shopify_product_id"),
        HelpPanel(
            heading="You can edit this book's data on Shopify",
            content=f"""
          Visit <a href='https://{settings.SHOPIFY_DOMAIN}/admin/products/'>the shopify products list</a> to change this product's name, description and so on. Changes will be automatically reflected in the website, via webhook updates.
        """,
        ),
    ]

    @classmethod
    def get_lowest_price(cls, product):
        return min(variant.price for variant in product.variants)

    @classmethod
    def get_args_for_page(cls, product, metafields):
        images = product.attributes.get("images", [])
        return dict(
            shopify_product_id=product.id,
            slug=product.attributes.get("handle"),
            title=product.attributes.get("title"),
            description=product.attributes.get("body_html"),
            image_url=images[0].src if len(images) > 0 else "",
            image_urls=[image.src for image in images] if len(images) > 0 else [],
            cached_price=cls.get_lowest_price(product),
        )

    @classmethod
    def get_root_page(cls):
        """
        Default parent page for product pages
        """
        site = Site.objects.get(
            root_page__content_type=ContentType.objects.get_for_model(HomePage)
        )
        home = site.root_page
        return home

    @classmethod
    def create_instance_for_product(cls, product, metafields):
        instance = cls(**cls.get_args_for_page(product, metafields))
        cls.get_root_page().add_child(instance=instance)
        if product.attributes.get("status", "draft") == "draft":
            instance.save()
            instance.unpublish()
        else:
            instance.save_revision().publish()
        return instance

    @classmethod
    def update_instance_for_product(cls, product, metafields):
        cls.objects.filter(shopify_product_id=product.id).update(
            **{
                key: value
                for key, value in cls.get_args_for_page(product, metafields).items()
                # Keep the originally published page slug for SEO reasons
                if key != "slug"
            }
        )
        instance = cls.objects.filter(shopify_product_id=product.id).first()
        if instance is not None:
            if product.attributes.get("status", "draft") == "draft":
                instance.unpublish()
            else:
                instance.save_revision().publish()
        return instance

    @classmethod
    def sync_from_shopify_product_id(cls, shopify_product_id):
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            product = shopify.Product.find(shopify_product_id)
            metafields = product.metafields()
            metafields = metafields_to_dict(metafields)
            if cls.objects.filter(shopify_product_id=shopify_product_id).exists():
                return cls.update_instance_for_product(product, metafields)
            else:
                return cls.create_instance_for_product(product, metafields)

    @property
    @django_cached("shopify_product", get_key=shopify_product_id_key)
    def shopify_product(self):
        return self.nocache_shopify_product

    @property
    def nocache_shopify_product(self) -> shopify.ShopifyResource:
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            try:
                product = shopify.Product.find(self.shopify_product_id)
                return product
            except:
                return None

    @property
    @django_cached("shopify_product_metafields", get_key=shopify_product_id_key)
    def shopify_product_metafields(self):
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            try:
                metafields = self.shopify_product.metafields()
                return metafields_to_dict(metafields)
            except:
                return {}

    @classmethod
    def sync_shopify_products_to_pages(cls, collection_id=None):
        if collection_id is None:
            collection_id = cls.shopify_collection_id
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            cache.clear()
            product_ids = shopify.CollectionListing.find(collection_id).product_ids()
            for product_id in product_ids:
                cls.sync_from_shopify_product_id(product_id)
                # Very simple solution to Shopify 2 calls/second ratelimiting
                time.sleep(0.5)

    @property
    def seo_description(self) -> str:
        try:
            tags = strip_tags(self.description).replace("\n", "")
            return tags
        except:
            return ""

    @property
    def seo_image_url(self) -> str:
        """
        Middleware for seo_image_sources
        """
        try:
            image = self.image_url
            return image
        except:
            return ""

    @classmethod
    def get_specific_product_by_shopify_id(cls, shopify_product_id):
        return (
            Page.objects.filter(
                abstract_page_query_filter(
                    BaseShopifyProductPage, dict(shopify_product_id=shopify_product_id)
                )
            )
            .distinct()
            .live()
            .specific()
            .order_by("title")
            .first()
        )


class ButtonBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=100, required=False)
    page = blocks.PageChooserBlock(
        required=False, help_text="Pick a page or specify a URL"
    )
    href = blocks.URLBlock(
        required=False, help_text="Pick a page or specify a URL", label="URL"
    )
    size = BootstrapButtonSizeChoiceBlock(required=False, default="md")
    style = BootstrapButtonStyleChoiceBlock(required=False, default="btn-outline-dark")

    class Meta:
        template = "app/blocks/cta.html"


class HeroTextBlock(blocks.StructBlock):
    heading = blocks.CharBlock(max_length=250, form_classname="full title")
    background_color = BackgroundColourChoiceBlock(required=False)
    button = ButtonBlock(required=False)

    class Meta:
        template = "app/blocks/hero_block.html"
        icon = "fa fa-alphabet"


class ListItemBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=250, form_classname="full title")
    image = ImageChooserBlock(required=False)
    image_css = blocks.CharBlock(max_length=500, required=False)
    caption = blocks.RichTextBlock(max_length=500)
    background_color = BackgroundColourChoiceBlock(required=False)
    button = ButtonBlock(required=False)

    class Meta:
        template = "app/blocks/list_item_block.html"
        icon = "fa fa-alphabet"


class ColumnWidthChoiceBlock(blocks.ChoiceBlock):
    choices = [
        ("small", "small"),
        ("medium", "medium"),
        ("large", "large"),
    ]

    class Meta:
        icon = "fa-arrows-alt"
        default = "small"


class ListBlock(blocks.StructBlock):
    column_width = ColumnWidthChoiceBlock()
    items = blocks.ListBlock(ListItemBlock)

    class Meta:
        template = "app/blocks/list_block.html"
        icon = "fa fa-alphabet"


class FeaturedBookBlock(blocks.StructBlock):
    book = blocks.PageChooserBlock(
        page_type="app.bookpage",
        target_model="app.bookpage",
        can_choose_root=False,
    )
    background_color = BackgroundColourChoiceBlock(required=False)
    promotion_label = blocks.CharBlock(
        required=False, help_text="Label that highlights this product"
    )
    description = blocks.RichTextBlock(
        required=False,
        help_text="This will replace the book's default description. You can use this to provide a more contextualised description of the book",
    )

    class Meta:
        template = "app/blocks/featured_book_block.html"
        icon = "fa fa-book"


class FeaturedProductBlock(blocks.StructBlock):
    product = blocks.PageChooserBlock(
        page_type="app.merchandisepage",
        target_model="app.merchandisepage",
        can_choose_root=False,
    )
    background_color = BackgroundColourChoiceBlock(required=False)
    promotion_label = blocks.CharBlock(
        required=False, help_text="Label that highlights this product"
    )
    description = blocks.RichTextBlock(
        required=False,
        help_text="This will replace the product's default description. You can use this to provide a more contextualised description of the product",
    )

    class Meta:
        template = "app/blocks/featured_product_block.html"
        icon = "fa fa-shopping-cart"


class BookGridBlock(blocks.StructBlock):
    column_width = ColumnWidthChoiceBlock()

    class Meta:
        template = "app/blocks/book_grid_block.html"
        icon = "fa fa-book"


class ProductGridBlock(blocks.StructBlock):
    column_width = ColumnWidthChoiceBlock()

    class Meta:
        template = "app/blocks/product_grid_block.html"
        icon = "fa fa-shopping-cart"


class SelectedBooksBlock(BookGridBlock):
    books = blocks.ListBlock(
        blocks.PageChooserBlock(
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
    products = blocks.ListBlock(
        blocks.PageChooserBlock(
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
    max_books = blocks.IntegerBlock(
        default=4, help_text="How many books should show up?"
    )
    type = BookTypeChoice(default="all-books")

    def get_context(self, value, parent_context=None):
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
    max_products = blocks.IntegerBlock(
        default=10, help_text="How many products should show up?"
    )

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["products"] = list(
            MerchandisePage.objects.live().public().all()[: value["max_products"]]
        )
        return context


class YourBooks(BookGridBlock):
    class Meta:
        template = "app/blocks/your_books_grid_block.html"
        icon = "fa fa-book"


class SingleBookBlock(blocks.StructBlock):
    book = blocks.PageChooserBlock(
        page_type="app.bookpage",
        target_model="app.bookpage",
        can_choose_root=False,
    )

    class Meta:
        template = "app/blocks/single_book_block.html"
        icon = "fa fa-book"


class NewsletterSignupBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False, max_length=150)

    class Meta:
        template = "app/blocks/newsletter_signup_block.html"
        icon = "fa fa-email"


class ArticleText(blocks.StructBlock):
    text = blocks.RichTextBlock(form_classname="full", features=block_features)
    alignment = AlignmentChoiceBlock(
        help_text="Doesn't apply when used inside a column."
    )

    class Meta:
        template = "app/blocks/richtext.html"


class ColumnBlock(blocks.StructBlock):
    stream_blocks = [
        ("hero_text", HeroTextBlock()),
        ("title_image_caption", ListItemBlock()),
        ("image", ImageChooserBlock()),
        ("single_book", SingleBookBlock()),
        ("membership_plan", PlanBlock()),
        ("richtext", blocks.RichTextBlock(features=block_features)),
        ("button", ButtonBlock()),
        ("newsletter_signup", NewsletterSignupBlock()),
    ]
    background_color = BackgroundColourChoiceBlock(required=False)
    content = blocks.StreamBlock(stream_blocks, required=False)


class SingleColumnBlock(ColumnBlock):
    column_width = ColumnWidthChoiceBlock()
    alignment = AlignmentChoiceBlock(
        help_text="Doesn't apply when used inside a column."
    )

    class Meta:
        template = "app/blocks/single_column_block.html"
        icon = "fa fa-th-large"


class MultiColumnBlock(blocks.StructBlock):
    background_color = BackgroundColourChoiceBlock(required=False)
    columns = blocks.ListBlock(ColumnBlock, min_num=1, max_num=5)

    class Meta:
        template = "app/blocks/columns_block.html"
        icon = "fa fa-th-large"


class EventsListBlock(blocks.StructBlock):
    number_of_events = blocks.IntegerBlock(required=True, default=3)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context.update(MapPage.get_map_context())
        return context

    class Meta:
        template = "app/blocks/event_list_block.html"
        icon = "fa fa-calendar"


class EventsListAndMap(blocks.StructBlock):
    title = blocks.CharBlock(required=False)
    intro = blocks.RichTextBlock(required=False)
    number_of_events = blocks.IntegerBlock(required=True, default=3)

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context.update(MapPage.get_map_context())
        return context

    class Meta:
        template = "app/blocks/event_list_and_map_block.html"
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
        ("heading", blocks.CharBlock(form_classname="full title")),
        ("richtext", ArticleText()),
        ("list_of_heading_image_text", ListBlock()),
        ("single_column", SingleColumnBlock()),
        ("columns", MultiColumnBlock()),
        ("events_list_and_map", EventsListAndMap()),
        ("events_list_block", EventsListBlock()),
    ]

    if isinstance(additional_blocks, list):
        blcks += additional_blocks

    return StreamField(blcks, null=True, blank=True, use_json_field=True, **kwargs)


@method_decorator(cache_page, name="serve")
class MerchandiseIndexPage(WagtailCacheMixin, IndexPageSeoMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [StreamFieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class MerchandisePage(WagtailCacheMixin, BaseShopifyProductPage):
    shopify_collection_id = settings.SHOPIFY_MERCH_COLLECTION_ID

    @classmethod
    def get_root_page(cls):
        return MerchandiseIndexPage.objects.first()


@method_decorator(cache_page, name="serve")
class BookPage(WagtailCacheMixin, BaseShopifyProductPage):
    shopify_collection_id = settings.SHOPIFY_BOOKS_COLLECTION_ID

    parent_page_types = ["app.BookIndexPage"]
    subtitle = models.CharField(max_length=300, blank=True)
    authors = ArrayField(
        models.CharField(max_length=300, blank=True), blank=True, default=list
    )
    forward_by = ArrayField(
        models.CharField(max_length=300, blank=True), blank=True, default=list
    )
    original_publisher = models.CharField(max_length=300, blank=True)
    published_date = models.DateField(null=True, blank=True)
    isbn = models.CharField(max_length=50, blank=True)
    type = models.CharField(max_length=300, blank=True)
    layout = create_streamfield()

    content_panels = BaseShopifyProductPage.content_panels + [
        StreamFieldPanel("layout")
    ]

    @classmethod
    def get_root_page(cls):
        return BookIndexPage.objects.first()

    @classmethod
    def get_args_for_page(cls, product, metafields):
        args = super().get_args_for_page(product, metafields)
        args.update(
            dict(
                published_date=metafields.get("published_date", ""),
                authors=metafields.get("author", []),
                forward_by=metafields.get("forward_by", []),
                original_publisher=metafields.get("original_publisher", ""),
                isbn=metafields.get("isbn", ""),
                type=metafields.get("type", ""),
            )
        )
        return args

    class Meta:
        ordering = ["-published_date"]


@method_decorator(cache_page, name="serve")
class MembershipPlanPage(WagtailCacheMixin, ArticleSeoMixin, Page):
    parent_page_types = ["app.HomePage"]

    deliveries_per_year = models.IntegerField()
    description = RichTextField(null=True, blank=True)
    pick_product_title = models.CharField(
        default="Choose a book series",
        max_length=150,
        help_text="Displayed if there are multiple products to pick from",
        null=True,
        blank=True,
    )
    pick_product_text = RichTextField(
        help_text="Displayed if there are multiple products to pick from",
        null=True,
        blank=True,
    )

    layout = create_streamfield(
        [("plan_title", PlanTitleBlock()), ("plan_pricing", PlanPricingBlock())],
        default=(("plan_title", {}), ("plan_pricing", {})),
    )

    panels = content_panels = Page.content_panels + [
        FieldPanel("deliveries_per_year"),
        FieldPanel("description"),
        InlinePanel("prices", min_num=1, label="Subscription Pricing Options"),
        InlinePanel("upsells", heading="Upsell options", label="Upsell option"),
        FieldPanel("pick_product_title", classname="full title"),
        FieldPanel("pick_product_text"),
        StreamFieldPanel("layout"),
    ]

    @property
    def delivery_frequency(self):
        months_between = self.deliveries_per_year / 12
        s = "every "
        if months_between == 1:
            s += "month"
        # Could replace this with https://github.com/savoirfairelinux/num2words
        elif months_between == 1 / 2:
            s += "two months"
        elif months_between == 1 / 3:
            s += "three months"
        else:
            s += f"{months_between} months"
        return s

    @property
    def basic_price(self) -> MembershipPlanPrice:
        price = self.monthly_price
        if price is None:
            price = self.prices.order_by("price", "interval").first()
        return price

    @property
    def monthly_price(self) -> MembershipPlanPrice:
        return self.prices.filter(interval="month").order_by("interval_count").first()

    @property
    def annual_price(self) -> MembershipPlanPrice:
        return self.prices.filter(interval="year").order_by("interval_count").first()

    @property
    def annual_percent_off_per_month(self) -> str:
        return (
            self.annual_price.equivalent_monthly_price - self.basic_price.price
        ) / self.basic_price.price

    def get_price_for_request(self, request):
        if request.GET.get("annual", None) is not None:
            return self.annual_price
        return self.basic_price

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["request_price"] = self.get_price_for_request(request)
        return context


@method_decorator(cache_page, name="serve")
class HomePage(WagtailCacheMixin, IndexPageSeoMixin, RoutablePageMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [StreamFieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class InformationPage(WagtailCacheMixin, ArticleSeoMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [StreamFieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class BookIndexPage(WagtailCacheMixin, IndexPageSeoMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [StreamFieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class MapPage(WagtailCacheMixin, Page):
    intro = RichTextField()

    content_panels = Page.content_panels + [FieldPanel("intro")]

    @classmethod
    def get_map_context(cls):
        context = {}
        context["sources"] = {}
        context["layers"] = {}

        # Events
        context["events"] = list(
            CircleEvent.objects.filter(starts_at__gte=datetime.now())
            .order_by("starts_at")
            .all()
        )

        context["sources"]["events"] = {
            "type": "geojson",
            "data": {
                "type": "FeatureCollection",
                "features": [
                    event.as_geojson_feature
                    for event in context["events"]
                    if event.as_geojson_feature.get("geometry", None) is not None
                ],
            },
        }

        context["layers"].update(
            {
                "event-icon-border": {
                    "source": "events",
                    "id": "event-icon-border",
                    "type": "circle",
                    "paint": {"circle-color": "#000000", "circle-radius": 10},
                },
                "event-icons": {
                    "source": "events",
                    "id": "event-icons",
                    "type": "circle",
                    "paint": {"circle-color": "#F8F251", "circle-radius": 8},
                },
                "event-dates": {
                    "source": "events",
                    "id": "event-dates",
                    "type": "symbol",
                    "paint": {"text-color": "black", "text-opacity": 1},
                    "layout": {
                        "text-field": ["get", "human_readable_date"],
                        "text-offset": [0, 0.85],
                        "text-anchor": "top",
                        "text-allow-overlap": True,
                        "text-transform": "uppercase",
                        "text-size": 15,
                        "text-font": ["Inter Regular"],
                    },
                },
                "event-names": {
                    "source": "events",
                    "id": "event-names",
                    "type": "symbol",
                    "layout": {
                        "text-field": ["get", "name"],
                        "text-offset": [0, 2.5],
                        "text-anchor": "top",
                        "text-allow-overlap": False,
                        "text-size": 12,
                        "text-font": ["Inter Regular"],
                    },
                    "paint": {
                        "text-opacity": [
                            "interpolate",
                            # Set the exponential rate of change to 0.5
                            ["exponential", 0.5],
                            ["zoom"],
                            # When zoom is 8, buildings will be 100% transparent.
                            8,
                            0,
                            # When zoom is 11 or higher, buildings will be 100% opaque.
                            11,
                            1,
                        ]
                    },
                },
            }
        )

        return context

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(MapPage.get_map_context())
        return context
