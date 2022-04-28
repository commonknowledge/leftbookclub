import urllib.parse
from importlib.metadata import metadata
from urllib.parse import urlencode

import djstripe.models
import shopify
import stripe
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.dispatch import receiver
from django.http.response import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django_countries import countries
from djmoney.models.fields import Money, MoneyField
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from wagtail.admin.edit_handlers import (
    FieldPanel,
    InlinePanel,
    MultiFieldPanel,
    PageChooserPanel,
    StreamFieldPanel,
)
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.core import blocks
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Orderable, Page
from wagtail.core.rich_text import get_text_for_indexing
from wagtail.images.blocks import ImageChooserBlock
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.search import index
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.snippets.models import register_snippet
from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtailseo.models import SeoMixin, SeoType, TwitterCard

from app.forms import CountrySelectorForm
from app.models.blocks import ArticleContentStream
from app.shopify_webhook.signals import products_create
from app.utils import include_keys
from app.utils.cache import django_cached
from app.utils.shopify import metafields_to_dict
from app.utils.stripe import create_shipping_zone_metadata, get_shipping_product
from app.views import CreateCheckoutSessionView, ShippingCostView

from .stripe import LBCProduct, ShippingZone


class SeoMetadataMixin(SeoMixin, Page):
    class Meta:
        abstract = True

    promote_panels = SeoMixin.seo_panels

    seo_image_sources = ["og_image"]  # Explicit sharing image

    seo_description_sources = [
        "search_description",  # Explicit sharing description
    ]

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
    seo_twitter_card = TwitterCard.SUMMARY
    promote_panels = SeoMixin.seo_panels


class ArticleSeoMixin(SeoMetadataMixin):
    class Meta:
        abstract = True

    seo_content_type = SeoType.ARTICLE
    seo_twitter_card = TwitterCard.LARGE
    promote_panels = SeoMixin.seo_panels


# class ProductBlock(StructBlock):
#     page = ParentalKey("app.MembershipPlanPage", related_name="products")
#     product = SnippetChooserBlock(djstripe.models.LBCProduct)


@register_snippet
class MembershipPlanPrice(Orderable):
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

    @property
    def deliveries_per_billing_period(self) -> float:
        if self.interval == "year":
            return self.plan.deliveries_per_year * self.interval_count
        if self.interval == "month":
            return (self.plan.deliveries_per_year / 12) * self.interval_count
        if self.interval == "week":
            return (self.plan.deliveries_per_year / 52) * self.interval_count
        if self.interval == "day":
            return (self.plan.deliveries_per_year / 365) * self.interval_count
        return self.plan.deliveries_per_year

    def shipping_fee(self, zone) -> Money:
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
        return f"{money}{interval}"

    @property
    def months_per_billing_cycle(self):
        if self.interval == "year":
            return 12 * self.interval_count
        if self.interval == "month":
            return self.interval_count
        if self.interval == "week":
            return self.interval_count / 4.2
        if self.interval == "day":
            return self.interval_count / 30

    @property
    def equivalent_monthly_price(self) -> str:
        return self.price / self.months_per_billing_cycle

    @property
    def equivalent_monthly_price_string(self) -> str:
        money = str(self.equivalent_monthly_price)
        return f"{money}/month"

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
            "metadata": self.metadata,
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


class MembershipPlanPage(ArticleSeoMixin, Page):
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
    products = ParentalManyToManyField(LBCProduct, blank=True)

    panels = content_panels = Page.content_panels + [
        FieldPanel("deliveries_per_year"),
        FieldPanel("description"),
        InlinePanel("prices", min_num=1, label="Price"),
        FieldPanel("pick_product_title", classname="full title"),
        FieldPanel("pick_product_text"),
        AutocompletePanel("products", target_model=LBCProduct),
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


class BackgroundColourChoiceBlock(blocks.ChoiceBlock):
    choices = [
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


class PlanBlock(blocks.StructBlock):
    plan = blocks.PageChooserBlock(
        page_type=MembershipPlanPage,
        target_model=MembershipPlanPage,
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
        form_classname="full title", default="Choose your plan", null=True, blank=True
    )
    description = blocks.RichTextBlock(
        null=True,
        blank=True,
        default="<p>Your subscription will begin with the most recently published book in your chosen collection.</p>",
    )
    plans = blocks.ListBlock(PlanBlock)

    class Meta:
        template = "app/blocks/membership_options_grid.html"
        icon = "fa-users"


class HomePage(IndexPageSeoMixin, RoutablePageMixin, Page):
    show_in_menus_default = True
    layout = StreamField(
        [
            ("heading", blocks.CharBlock(form_classname="full title")),
            ("paragraph", blocks.RichTextBlock()),
            ("membership_options", MembershipOptionsBlock()),
            ("image", ImageChooserBlock()),
            # TODO: Featured book block
            # TODO: hero text block  (background=yellow)
            # TODO: section text block
            # TODO: two column block (text=left / right)
            # TODO: recent books block (max_count=8)
            # TODO: USP block
            # TODO: newsletter block
        ],
        null=True,
        blank=True,
    )

    content_panels = Page.content_panels + [StreamFieldPanel("layout")]

    seo_description_sources = IndexPageSeoMixin.seo_description_sources + ["body"]


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


class BlogIndexPage(IndexPageSeoMixin, Page):
    """
    Define blog index page.
    """

    show_in_menus_default = True

    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [FieldPanel("intro", classname="full")]

    seo_description_sources = IndexPageSeoMixin.seo_description_sources + ["intro"]


class BlogPage(ArticleSeoMixin, Page):
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

    seo_description_sources = ArticleSeoMixin.seo_description_sources + [
        "intro",
        "body",
    ]

    seo_image_sources = ArticleSeoMixin.seo_image_sources + ["feed_image"]


class InformationPage(ArticleSeoMixin, Page):
    show_in_menus_default = True

    cover_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    body = ArticleContentStream()

    content_panels = Page.content_panels + [
        ImageChooserPanel("cover_image"),
        StreamFieldPanel("body", classname="full"),
    ]

    seo_description_sources = ArticleSeoMixin.seo_description_sources + ["body"]

    seo_image_sources = ArticleSeoMixin.seo_image_sources + ["cover_image"]


class BookIndexPage(IndexPageSeoMixin, Page):
    body = ArticleContentStream()

    content_panels = Page.content_panels + [
        StreamFieldPanel("body", classname="full"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        products = [
            {
                "page": p,
                "product": p.shopify_product,
                "metafields": p.shopify_product_metafields,
            }
            for p in BookPage.objects.live()
            .descendant_of(self)
            .filter(published_date__isnull=False)
            .order_by("-published_date")
        ]
        context["products"] = products
        return context

    seo_description_sources = ArticleSeoMixin.seo_description_sources + ["body"]


def shopify_product_id_key(page):
    return page.shopify_product_id


class BaseShopifyProductPage(ArticleSeoMixin, Page):
    class Meta:
        abstract = True

    # TODO: Autocomplete this in future?
    shopify_product_id = models.CharField(max_length=300, blank=False, null=False)

    content_panels = Page.content_panels + [FieldPanel("shopify_product_id")]

    @classmethod
    def get_for_product(cls, id=None, product=None, handle=None):
        if product is not None:
            id = product.id

        if id is not None:
            # Check if it exists by ID
            page = cls.objects.filter(shopify_product_id=id).first()
            if page is not None:
                return page

            if product is None:
                # Query by ID
                with shopify.Session.temp(
                    settings.SHOPIFY_DOMAIN,
                    "2021-10",
                    settings.SHOPIFY_PRIVATE_APP_PASSWORD,
                ):
                    product = shopify.Product.find(id)

        if product is None and handle is not None:
            # Query by handle
            with shopify.Session.temp(
                settings.SHOPIFY_DOMAIN,
                "2021-10",
                settings.SHOPIFY_PRIVATE_APP_PASSWORD,
            ):
                product = shopify.Product.find(handle=handle)

        if product is None:
            return None

        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            metafields = product.metafields()
            metafields = metafields_to_dict(metafields)

            # Create new page
            page = cls.create_instance_for_product(product, metafields)
            BookIndexPage.objects.first().add_child(instance=page)

            return page

    @classmethod
    def create_instance_for_product(cls, product, metafields):
        return cls(
            slug=product.attributes.get("handle"),
            title=product.title,
            shopify_product_id=product.id,
        )

    @property
    @django_cached("shopify_product", get_key=shopify_product_id_key)
    def shopify_product(self):
        return self.latest_shopify_product

    @property
    def latest_shopify_product(self) -> shopify.ShopifyResource:
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

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["product"] = self.shopify_product
        context["metafields"] = self.shopify_product_metafields
        return context

    @classmethod
    def sync_shopify_products_to_pages(cls):
        print("sync_shopify_products_to_pages")
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            cache.clear()
            book_ids = shopify.CollectionListing.find(
                settings.SHOPIFY_COLLECTION_ID
            ).product_ids()
            for book in book_ids:
                BookPage.get_for_product(book)

            # TODO: also list merch
            # products = shopify.Product.find(collection=settings.SHOPIFY_COLLECTION_ID)
            # for product in products:
            #     ShopifyProductPage.get_for_product(id=product.id)

    @property
    def seo_description(self) -> str:
        try:
            tags = strip_tags(self.shopify_product.body_html).replace("\n", "")
            return tags
        except:
            return ""

    @property
    def seo_image_url(self) -> str:
        """
        Middleware for seo_image_sources
        """
        try:
            image = self.shopify_product.images[0].src
            return image
        except:
            return ""


class MerchandisePage(BaseShopifyProductPage):
    pass


class BookPage(BaseShopifyProductPage):
    published_date = models.DateField(null=True, blank=True)

    content_panels = BaseShopifyProductPage.content_panels + [
        FieldPanel("published_date")
    ]

    @property
    def common_ancestor(cls):
        book = BookIndexPage.objects.first()
        return book

    @classmethod
    def create_instance_for_product(cls, product, metafields):
        return cls(
            slug=product.attributes.get("handle"),
            title=product.title,
            shopify_product_id=product.id,
            published_date=metafields.get("published_date", None),
        )

    class Meta:
        ordering = ["published_date"]


@receiver(products_create)
def sync(*args, **kwargs):
    print(args, kwargs)
    BaseShopifyProductPage.sync_shopify_products_to_pages()
