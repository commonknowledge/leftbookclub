from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtailmenus.models import AbstractMainMenuItem


class CustomMainMenuItem(AbstractMainMenuItem):
    """
    Same as wagtailmenus' MainMenuItem, but "Allow sub-menu" is off by default
    so new menu items don't unexpectedly get a dropdown of their child pages.
    Registered via WAGTAILMENUS_MAIN_MENU_ITEMS_RELATED_NAME.
    """

    menu = ParentalKey(
        "wagtailmenus.MainMenu",
        on_delete=models.CASCADE,
        related_name="custom_menu_items",
    )
    allow_subnav = models.BooleanField(
        verbose_name=_("allow sub-menu for this item"),
        default=False,
        help_text=_(
            "Show this page's child pages (those with 'Show in menus' ticked) "
            "as a dropdown under this item."
        ),
    )

    class Meta(AbstractMainMenuItem.Meta):
        abstract = False
