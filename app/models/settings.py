from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.panels import StreamFieldPanel
from wagtail.contrib.settings.models import BaseSetting, register_setting
from wagtail.fields import RichTextField
from wagtailautocomplete.edit_handlers import AutocompletePanel

from app.models.wagtail import (
    BookPage,
    MembershipPlanPage,
    YourBooks,
    create_streamfield,
)


@register_setting(icon="users")
class MembershipJourney(BaseSetting):
    welcome_content = create_streamfield()
    panels = [StreamFieldPanel("welcome_content")]


@register_setting(icon="users")
class MemberProfilePage(BaseSetting):
    profile_page_content = create_streamfield(
        [
            ("your_book_list", YourBooks()),
        ]
    )
    panels = [StreamFieldPanel("profile_page_content")]


@register_setting(icon="money")
class UpsellPlanSettings(BaseSetting):
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
