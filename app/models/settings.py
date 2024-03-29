from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField
from wagtailautocomplete.edit_handlers import AutocompletePanel

from app.models.wagtail import (
    BookPage,
    MembershipPlanPage,
    YourBooks,
    create_streamfield,
)


@register_setting(icon="users")
class MembershipJourney(BaseSiteSetting):
    welcome_content = create_streamfield()
    panels = [FieldPanel("welcome_content")]


@register_setting(icon="users")
class MemberProfilePage(BaseSiteSetting):
    profile_page_content = create_streamfield(
        [
            ("your_book_list", YourBooks()),
        ]
    )
    panels = [FieldPanel("profile_page_content")]


@register_setting(icon="money")
class UpsellPlanSettings(BaseSiteSetting):
    class Meta:
        verbose_name = _("Review Fee Settings")

    intro_text = RichTextField(
        blank=False,
        features=["bold", "italic", "h1", "link", "ol", "ul"],
        default="""
    <h1>Review your fee</h1>
    <p>Since you signed up, our operating costs have increased dramatically due to the economic times we’re all living through.</p>
    <p>We’ve increased the price of new memberships and protected your fee, but we are beginning to struggle. Can you afford to increase your membership fee?</p>
    """,
    )

    donation_text = RichTextField(
        blank=False,
        features=["bold", "italic", "blockquote"],
        default="""
    <p>If you have remained on a legacy or a standard price, please consider adding a monthly donation to your membership fee. Any amount, however small, will make a huge difference. Thank you!</p>
    """,
    )

    upgrade_membership_text = RichTextField(
        blank=False,
        features=["bold", "italic", "blockquote"],
        default="""
    <p>You’re currently paying {{ old_price }}. Select this option if it’s all you can afford right now — that is totally OK.</p>
    <p>Other members paying solidarity rates will make it possible for us to continue offering this, so please consider if you can afford to increase your rate or if you genuinely need to stay here.</p>
    """,
    )

    upsell_plan = models.ForeignKey(
        MembershipPlanPage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Plan promoted to all existing members — the best offer for anyone to upgrade to",
    )


def settings_path(custom_settings_cls):
    return f"/admin/settings/{custom_settings_cls._meta.app_label}/{custom_settings_cls._meta.model_name}"


@register_setting(icon="money")
class V2SignupFlow(BaseSiteSetting):
    continue_button_label = models.CharField(
        max_length=255,
        default="Continue",
        help_text="Label for the continue button",
    )

    select_deliveries_title = models.CharField(
        max_length=255,
        default="How often do you want a new book?",
        help_text="Title for the deliveries step",
    )

    select_syllabus_title = models.CharField(
        max_length=255,
        default="What kind of books do you want?",
        help_text="Title for the syllabus step",
    )

    select_syllabus_intro = RichTextField(
        blank=False,
        features=["bold", "italic", "link", "ol", "ul", "blockquote"],
        default="""
        <p>Each syllabus has a new book published for it regularly.</p>
        """,
    )

    select_shipping_title = models.CharField(
        max_length=255,
        default="Where should we send your books?",
        help_text="Title for the shipping step",
    )

    select_billing_title = models.CharField(
        max_length=255,
        default="How much do you want to pay?",
        help_text="Title for the billing step",
    )

    select_donation_intro = RichTextField(
        blank=False,
        features=["bold", "italic", "link", "ol", "ul", "blockquote"],
        default="""
          <p>Our membership fees are based on solidarity. If you can afford to pay more, you'll help us to keep our fees low for everyone.</p>
          <p>To learn more about our not-for-profit political education project, <a href='/about' target='_blank' rel='noopener noreferrer'>click here</a>.
        """,
    )

    # RichTextField(
    #     blank=False,
    #     features=[],
    #     default="""
    # <p>You’re currently paying {{ old_price }}. Select this option if it’s all you can afford right now — that is totally OK.</p>
    # <p>Other members paying solidarity rates will make it possible for us to continue offering this, so please consider if you can afford to increase your rate or if you genuinely need to stay here.</p>
    # """,
    # )
