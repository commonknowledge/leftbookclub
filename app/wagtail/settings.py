from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.admin.menu import MenuItem
from wagtail.contrib.settings.models import BaseSetting, register_setting
from wagtail.core import hooks
from wagtailautocomplete.edit_handlers import AutocompletePanel

from app.models import LBCProduct


@register_setting(icon="pick")
class FeaturedContent(BaseSetting):
    class Meta:
        verbose_name = "Featured Content"

    current_book = models.ForeignKey(
        LBCProduct, blank=True, null=True, on_delete=models.DO_NOTHING
    )

    panels = [AutocompletePanel("current_book")]


@hooks.register("register_admin_menu_item")
def register_frank_menu_item():
    return MenuItem(
        "Featured Content",
        settings_path(FeaturedContent),
        icon_name="pick",
        order=10000,
    )


def settings_path(custom_settings_cls):
    return f"/admin/settings/{custom_settings_cls._meta.app_label}/{custom_settings_cls._meta.model_name}"
