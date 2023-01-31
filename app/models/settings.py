from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.panels import StreamFieldPanel
from wagtail.contrib.settings.models import BaseSetting, register_setting
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
