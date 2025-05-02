from typing import Optional

import time
import pytz
from datetime import datetime
from django.utils import timezone

import djstripe.models
import orjson
import shopify
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.forms import Select
from django.templatetags.static import static
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from djmoney.models.fields import Money, MoneyField
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import (
    FieldPanel,
    FieldRowPanel,
    HelpPanel,
    InlinePanel,
    MultiFieldPanel,
    TitleFieldPanel,
)
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.fields import RichTextField
from wagtail.images.models import AbstractImage, AbstractRendition
from wagtail.models import Orderable, Page, Site
from wagtail.rich_text import get_text_for_indexing
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtailcache.cache import WagtailCacheMixin, cache_page
from wagtailseo import utils
from wagtailseo.models import SeoMixin, SeoType, TwitterCard

from app.models.blocks import *
from app.models.circle import CircleEvent
from app.utils.abstract_model_querying import abstract_page_query_filter
from app.utils.books import get_current_book
from app.utils.cache import django_cached
from app.utils.shopify import metafields_to_dict
from app.utils.stripe import create_shipping_zone_metadata, get_shipping_product

from .stripe import LBCProduct, ShippingZone
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.db import models as gis_models
from app.utils.geo import postcode_geo, point_from_postcode_result 
from django.core.exceptions import ValidationError

class EventDate(models.Model):
    event = ParentalKey("ReadingGroup", on_delete=models.CASCADE, related_name="additional_dates")
    date = models.DateTimeField()

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.event.name} - {self.date.strftime('%Y-%m-%d %H:%M')}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone

        if self.date < timezone.now():
            raise ValidationError({"date": "Additional dates must be in the future."})
        
        
class ReadingGroup(ClusterableModel, models.Model):
    group_name = models.CharField(max_length=500)
    next_event = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(
        max_length=32,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default='Europe/London'
    )
    is_online = models.BooleanField(default=False, help_text="Is this event online?")
    in_person_location = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Enter an address if your event is in person.",
    )
    in_person_postcode = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Enter a UK postcode to show your event on our map.",
    )
    contact_link_or_email = models.CharField(max_length=128, blank=True, null=True, help_text="(Optional) A link or email address to contact the group.")
    contact_email_address = models.EmailField(max_length=128, blank=False, null=False, help_text="(Private) We will use this to contact you.")
    more_information = models.TextField(max_length=280, blank=True, null=True, help_text="(Optional) Any extra important information about the group.")
    coordinates = gis_models.PointField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    recurring_pattern = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Enter a description of the recurring pattern, e.g. 'Every first Monday of the month'.",
    )

    panels = [
        FieldPanel("group_name"),
        FieldPanel("next_event"),
        FieldPanel("timezone", widget=Select(choices=[(tz, tz) for tz in pytz.common_timezones])),
        InlinePanel("additional_dates", label="Additional Dates", max_num=5),
        FieldPanel("is_online"),
        FieldPanel("in_person_location"),
        FieldPanel("in_person_postcode"),
        FieldPanel("contact_link_or_email"),
        FieldPanel("more_information"),
        FieldPanel("contact_email_address"),
        FieldPanel("is_approved"),
        FieldPanel("is_recurring"),
        FieldPanel("recurring_pattern"),
    ]

    class Meta:
        ordering = ["next_event"]

    def __str__(self):
        if not self.next_event:
            return self.group_name
        return f"{self.group_name} ({self.next_event.strftime('%Y-%m-%d')})"

    def clean(self):
        super().clean()
        if self.next_event and self.next_event < timezone.now():
            raise ValidationError({"start_date": "Start date must be in the future."})

        future_dates = [self.next_event] + [
            d.date for d in self.additional_dates.all() if d.date >= timezone.now()
        ]
        if len(future_dates) > 6:
            raise ValidationError("You cannot have more than 6 future dates for this event.")

    def save(self, *args, **kwargs):
        if self.in_person_postcode and not self.coordinates:
            postcode_result = postcode_geo(self.in_person_postcode)
            point = point_from_postcode_result(postcode_result)
            if point:
                self.coordinates = point
        self.full_clean()  # Run validation before saving
        super().save(*args, **kwargs)

    @property
    def upcoming_dates(self):
        all_dates = [self.next_event] + [d.date for d in self.additional_dates.all()]
        return sorted(d for d in all_dates if d and d >= timezone.now())[:6]

    @property
    def as_geojson_feature(self):
        try:
            geometry = {
                "type": "Point",
                "coordinates": [self.coordinates.x, self.coordinates.y],
            } if self.coordinates else None
            
            upcoming = self.upcoming_dates
            next_date = upcoming[0] if upcoming else self.next_event

            feature = {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "name": self.group_name,
                "slug": self.group_name.lower().replace(" ", "-"),
                "starts_at": next_date.isoformat(),
                "human_readable_date": timezone.localtime(next_date).strftime("%d %b %Y"),
                "location_type": "virtual" if self.is_online else "in_person",
                "in_person_location": self.in_person_location,
                "contact_link_or_email": self.contact_link_or_email,
                "more_information": self.more_information,
                "postcode": self.in_person_postcode,
                "all_dates": [d.isoformat() for d in self.upcoming_dates],
            },
            }
        
            return feature
        except Exception as e:
            return {
                "type": "Feature",
                "properties": {
                    "name": self.group_name,
                    "error": str(e),
                },
            }
        
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


class Interval(models.TextChoices):
    year = "year"
    month = "month"
    week = "week"
    day = "day"


@register_snippet
class MembershipPlanPrice(Orderable, ClusterableModel):
    # name = models.CharField(max_length=150, blank=True)
    plan = ParentalKey("app.MembershipPlanPage", related_name="prices")

    price = MoneyField(
        default=0,
        max_digits=14,
        decimal_places=2,
        default_currency="GBP",
        null=False,
        blank=False,
    )

    interval = models.CharField(
        max_length=10,
        choices=Interval.choices,
        default=Interval.month,
        null=False,
        blank=True,
    )

    interval_count = models.IntegerField(default=1, null=False, blank=True)

    ### v2 flow
    title = models.CharField(max_length=150, blank=True, null=True)
    skip_donation_ask = models.BooleanField(default=False, blank=True, null=True)
    suggested_donation_amounts = ArrayField(
        models.IntegerField(), blank=True, null=True
    )
    default_donation_amount = MoneyField(
        max_digits=14,
        decimal_places=2,
        default_currency="GBP",
        null=True,
        blank=True,
    )
    ### /v2

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
        help_text="The stripe product that the user will be subscribed to.",
        verbose_name="Stripe product",
    )

    panels = [
        TitleFieldPanel("title", targets=[]),
        FieldPanel("price", classname="collapsible collapsed"),
        MultiFieldPanel(
            [
                FieldPanel("skip_donation_ask"),
                FieldPanel("suggested_donation_amounts"),
                FieldPanel("default_donation_amount"),
            ],
            heading="[V2] Donation upsell",
        ),
        FieldRowPanel(
            [
                FieldPanel("interval_count"),
                FieldPanel("interval"),
            ],
            heading="Billing schedule",
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
        MultiFieldPanel(
            [
                AutocompletePanel("products", target_model=LBCProduct),
            ],
            heading="V1 signup flow",
            classname="collapsible collapsed",
        ),
    ]

    @property
    def deliveries_per_billing_period(self) -> Optional[float]:
        if self.plan.deliveries_per_year <= 0:
            return 0
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

    def equivalent_monthly_shipping_fee(self, zone) -> Money:
        if self.free_shipping_zones.filter(code=zone.code).exists():
            return Money(0, zone.rate_currency)
        return (
            zone.rate
            * self.deliveries_per_billing_period
            / self.months_per_billing_cycle
        )

    def price_including_shipping(self, zone):
        return self.price + self.shipping_fee(zone)

    def humanised_interval(self):
        s = "/"
        if self.interval_count > 1:
            s += str(self.interval_count) + " "
        s += self.interval
        if self.interval_count > 1:
            s += "s"
        return s

    def raw_price_string(self) -> str:
        money = str(self.price)
        interval = self.humanised_interval()
        s = f"{money}{interval}"
        return s

    def shipping_price_string(self, zone) -> str:
        money = str(self.shipping_fee(zone))
        interval = self.humanised_interval()
        s = f"{money}{interval}"
        return s

    @property
    def price_string(self) -> str:
        money = str(self.price)
        interval = self.humanised_interval()
        s = f"{money}{interval}"
        if self.should_advertise_postage_price:
            return f"{s} + p&p"
        return s

    def price_string_including_shipping(self, zone) -> str:
        money = str(self.price_including_shipping(zone))
        interval = self.humanised_interval()
        s = f"{money}{interval}"
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
    def monthly_price_string(self) -> str:
        money = str(self.equivalent_monthly_price)
        s = f"{money}/month"
        return s

    def equivalent_monthly_price_string_including_shipping(self, zone) -> str:
        money = str(
            self.equivalent_monthly_price
            + self.shipping_fee(zone) / self.months_per_billing_cycle
        )
        s = f"{money}/month"
        return s

    @property
    def equivalent_monthly_price_string(self) -> str:
        money = str(self.equivalent_monthly_price)
        s = f"{money}/month"
        if self.should_advertise_postage_price:
            return f"{s} + p&p"
        return s

    @property
    def shipping_price_string_uk(self) -> str:
        return self.shipping_fee(ShippingZone.get_for_country(iso_a2="GB"))

    @property
    def price_string_including_uk_shipping(self) -> str:
        return self.price_string_including_shipping(
            ShippingZone.get_for_country(iso_a2="GB")
        )

    def __str__(self) -> str:
        return f"{self.price_string} on {self.plan}"

    @property
    def metadata(self):
        return {"wagtail_price": self.id}

    def to_price_data(self, product=None, amount=None):
        if product is None and self.products.count() == 1:
            product = self.products.first()
        if product is None:
            raise ValueError("Cannot create line items without a valid product")

        return {
            "unit_amount_decimal": (amount if amount is not None else self.price.amount)
            * 100,
            "currency": self.price_currency,
            "product": product.id,
            "recurring": {
                "interval": self.interval,
                "interval_count": self.interval_count,
            },
            "metadata": {**(self.metadata or {}), "primary": True},
        }

    def to_shipping_price_data(self, zone, amount=None):
        shipping_product = get_shipping_product()
        shipping_fee = self.shipping_fee(zone)
        return {
            "unit_amount_decimal": (
                amount if amount is not None else shipping_fee.amount
            )
            * 100,
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

    def default_product(self):
        return self.products.first()

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

    @classmethod
    def from_si(cls, si: djstripe.models.SubscriptionItem):
        current_plan_price = MembershipPlanPrice.objects.filter(
            Q(id=si.metadata.get("wagtail_price"))
            | Q(id=si.plan.metadata.get("wagtail_price"))
        ).first()
        if current_plan_price is None:
            current_plan_price = MembershipPlanPrice.objects.filter(
                interval=si.plan.interval,
                interval_count=si.plan.interval_count,
                products=si.plan.product.djstripe_id,
            ).first()
        return current_plan_price

    @property
    def discount_percent(self):
        if self.interval != "year":
            return None
        monthly_price = self.plans.first().monthly_price.price
        discount_percent = (
            monthly_price - self.equivalent_monthly_price
        ) / monthly_price
        return discount_percent


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


def create_default_layout_syllabus():
    return (("syllabus_title", {}),)


@register_snippet
class ReadingOption(Orderable, ClusterableModel):
    """
    A simple way to group together multiple plans, e.g. "every month" and "every two months"
    """

    title = models.CharField(max_length=150, help_text="Visible to potential customers")
    banner_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    description = RichTextField(
        features=["ul"],
        help_text="Bullet points will appear as ticks.",
        null=True,
        blank=True,
    )
    interval = models.CharField(
        max_length=10,
        choices=Interval.choices,
        default=Interval.month,
        null=False,
        blank=True,
    )
    interval_count = models.IntegerField(default=1, null=False, blank=True)

    plans = ParentalManyToManyField(
        "app.MembershipPlanPage",
        related_name="plans",
        help_text="The plans available under this option",
    )

    def __str__(self) -> str:
        return self.title

    panels = [
        TitleFieldPanel("title", targets=[]),
        FieldPanel("description"),
        FieldRowPanel(
            [
                FieldPanel("interval_count"),
                FieldPanel("interval"),
            ],
            heading="Delivery schedule",
        ),
        FieldPanel("banner_image"),
        AutocompletePanel("plans", target_model="app.MembershipPlanPage"),
    ]


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
        FieldPanel("body", classname="full"),
        FieldPanel("feed_image"),
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
        images = metafields_array_to_list(product.attributes.get("images", []))
        image_urls = [image.src for image in images] if len(images) > 0 else []
        return dict(
            shopify_product_id=product.id,
            slug=product.attributes.get("handle"),
            title=product.attributes.get("title"),
            description=product.attributes.get("body_html"),
            image_url=image_urls[0] if len(images) > 0 else "",
            image_urls=image_urls,
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
        update_args = {
            key: value
            for key, value in cls.get_args_for_page(product, metafields).items()
            # Keep the originally published page slug for SEO reasons
            if key != "slug"
        }
        cls.objects.filter(shopify_product_id=product.id).update(**update_args)
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
            collection_listing = shopify.CollectionListing.find(collection_id)
            product_ids = collection_listing.product_ids(limit=250)
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


@method_decorator(cache_page, name="serve")
class MerchandiseIndexPage(WagtailCacheMixin, IndexPageSeoMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [FieldPanel("layout")]


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
        models.CharField(max_length=300, blank=True), blank=True, null=True
    )
    forward_by = ArrayField(
        models.CharField(max_length=300, blank=True), blank=True, null=True
    )
    original_publisher = models.CharField(max_length=300, blank=True)
    published_date = models.DateField(null=True, blank=True)
    isbn = models.CharField(max_length=50, blank=True)
    type = models.CharField(max_length=300, blank=True)
    layout = create_streamfield()

    content_panels = BaseShopifyProductPage.content_panels + [FieldPanel("layout")]

    @classmethod
    def get_root_page(cls):
        return BookIndexPage.objects.first()

    @classmethod
    def get_args_for_page(cls, product, metafields):
        args = super().get_args_for_page(product, metafields)
        args.update(
            dict(
                published_date=metafields.get("published_date", None),
                authors=metafields_array_to_list(metafields.get("author", [])),
                forward_by=metafields_array_to_list(metafields.get("forward_by", [])),
                original_publisher=metafields.get("original_publisher", ""),
                isbn=metafields.get("isbn", ""),
                type=metafields.get("type", ""),
            )
        )
        return args

    class Meta:
        ordering = ["-published_date"]


def metafields_array_to_list(arg):
    value = []
    if isinstance(arg, str):
        value = orjson.loads(arg)
    else:
        value = arg
    if isinstance(value, list):
        return value
    else:
        return []


def create_default_layout_plan():
    return (
        ("plan_title", {}),
        ("plan_pricing", {}),
    )


@method_decorator(cache_page, name="serve")
class MembershipPlanPage(WagtailCacheMixin, ArticleSeoMixin, Page):
    parent_page_types = ["app.HomePage"]

    ### v2 signup flow fields
    product_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="600 x 300 optimal resolution.",
    )
    background_image = models.ForeignKey(
        CustomImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="1400 x 1024 optimal resolution.",
    )
    display_in_quiz_flow = models.BooleanField(
        default=False, verbose_name="Display in v2 signup flow"
    )
    book_types = models.CharField(
        choices=book_types,
        max_length=150,
        blank=True,
        null=True,
        help_text="Which types of books are included in this plan? Used for displaying things.",
    )
    ### /v2

    deliveries_per_year = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0)]
    )
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
        default=create_default_layout_plan,
    )

    panels = content_panels = Page.content_panels + [
        FieldPanel("deliveries_per_year", heading="[v1+v2] Deliveries per year"),
        InlinePanel(
            "prices", min_num=1, label="Prices", classname="collapsible collapsed"
        ),
        MultiFieldPanel(
            [
                # FieldPanel("display_in_quiz_flow"),
                FieldPanel("book_types"),
                FieldPanel("product_image"),
                FieldPanel("background_image"),
                FieldPanel("description"),
            ],
            heading="V2 signup flow",
            classname="collapsible",
        ),
        MultiFieldPanel(
            [
                InlinePanel("upsells", label="Upsell prices"),
                FieldPanel("pick_product_title", classname="full title"),
                FieldPanel("pick_product_text"),
            ],
            heading="V1 signup flow",
            classname="collapsible collapsed",
        ),
        FieldPanel("layout"),
    ]

    @property
    def delivery_frequency(self):
        if self.deliveries_per_year <= 0:
            return None
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
    def annual_percent_off_per_month(self):
        if self.basic_price is None or self.annual_price is None:
            return None
        return (
            self.annual_price.equivalent_monthly_price - self.basic_price.price
        ) / self.basic_price.price

    def get_price_for_request(self, request):
        if request.GET.get("annual", None) is not None:
            return self.annual_price
        return self.basic_price

    @cached_property
    def current_book(self):
        return get_current_book(self.book_types)

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["request_price"] = self.get_price_for_request(request)
        return context


@method_decorator(cache_page, name="serve")
class HomePage(WagtailCacheMixin, IndexPageSeoMixin, RoutablePageMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [FieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class InformationPage(WagtailCacheMixin, ArticleSeoMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [FieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class BookIndexPage(WagtailCacheMixin, IndexPageSeoMixin, Page):
    show_in_menus_default = True
    layout = create_streamfield()
    content_panels = Page.content_panels + [FieldPanel("layout")]


@method_decorator(cache_page, name="serve")
class ReadingGroupsPage(WagtailCacheMixin, Page):
    intro = RichTextField()

    content_panels = Page.content_panels + [FieldPanel("intro")]

    @classmethod
    def get_map_context(cls):
        context = {}
        context["sources"] = {}
        context["layers"] = {}

        # Reading Groups
        reading_groups = list(
            ReadingGroup.objects.filter(is_approved=True)
            .order_by("next_event")
            .all()
        )
        context["reading_groups"] = reading_groups

        context["sources"]["reading_groups"] = {
            "type": "geojson",
            "data": {
                "type": "FeatureCollection",
                "features": [
                    group.as_geojson_feature
                    for group in context["reading_groups"]
                    if group.as_geojson_feature.get("geometry", None) is not None
                ],
            },
        }

        context["layers"].update(
            {
                "reading-group-icon-border": {
                    "source": "reading_groups",
                    "id": "reading-group-icon-border",
                    "type": "circle",
                    "paint": {"circle-color": "#000000", "circle-radius": 10},
                },
                "reading-group-icons": {
                    "source": "reading_groups",
                    "id": "reading-group-icons",
                    "type": "circle",
                    "paint": {"circle-color": "#F8F251", "circle-radius": 8},
                },
                "reading-group-dates": {
                    "source": "reading_groups",
                    "id": "reading-group-dates",
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
                "reading-group-names": {
                    "source": "reading_groups",
                    "id": "reading-group-names",
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
                            ["exponential", 0.5],
                            ["zoom"],
                            8, 0,
                            11, 1,
                        ]
                    },
                },
            }
        )

        return context

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context.update(ReadingGroupsPage.get_map_context())
        return context


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
