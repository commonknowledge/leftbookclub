import djstripe.models
import shopify
from admin_list_controls.actions import SubmitForm
from admin_list_controls.components import Button, Columns, Panel
from admin_list_controls.filters import BooleanFilter, ChoiceFilter, TextFilter
from admin_list_controls.views import ListControlsIndexView
from django.db.models import Count, Q
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail import hooks
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from app.models.django import User
from app.models.stripe import LBCCustomer, LBCProduct, LBCSubscription, ShippingZone
from app.models.wagtail import MembershipPlanPage, MembershipPlanPrice


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("wagtailadmin.css"))


class MembershipOptionsAdmin(ModelAdmin):
    model = MembershipPlanPage
    menu_icon = "fa-money"  # change as required
    menu_label = "Plans"


modeladmin_register(MembershipOptionsAdmin)


class PriceOptionsAdmin(ModelAdmin):
    model = MembershipPlanPrice
    menu_label = "Prices"
    menu_icon = "fa-money"  # change as required


modeladmin_register(PriceOptionsAdmin)


class ShippingAdmin(ModelAdmin):
    model = ShippingZone
    menu_icon = "fa-truck"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )


modeladmin_register(ShippingAdmin)


class IndexView(ListControlsIndexView):
    def build_list_controls(self):
        products = list(
            djstripe.models.Plan.objects.filter(active=True)
            .order_by()
            .values_list("product__id", "product__name")
            .annotate(frequency=Count("product__id"))
            .order_by("-frequency")
        )
        statuses = list(
            LBCSubscription.objects.all().values_list("status").order_by().distinct()
        )
        config = [
            Panel()(
                Columns()(
                    ChoiceFilter(
                        name="product",
                        label="Product",
                        multiple=True,
                        choices=tuple((p[0], p[1]) for p in products),
                        apply_to_queryset=lambda queryset, values: queryset.filter(
                            # Single-plan subscriptions
                            # Q(plan__product__in=values) |
                            # Multi-plan subscriptions
                            Q(plan__subscription_items__plan__product__in=values)
                            | Q(items__plan__product__in=values)
                        ),
                    ),
                ),
                Button(action=SubmitForm())(
                    "Apply filters",
                ),
            ),
        ]
        return config


class CustomerAdmin(ModelAdmin):
    # index_view_class = IndexView
    model = LBCSubscription
    menu_label = "Members"  # ditch this to use verbose_name_plural from model
    menu_icon = "fa-users"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "recipient_name",
        "primary_product_name",
        "status",
        "is_gift_receiver",
    )
    list_export = (
        "recipient_name",
        "recipient_email",
        "primary_product_name",
        "primary_product_id",
        "is_gift_receiver",
        "is_active_member",
        "status",
        "created",
        "ended_at",
        "shipping_line_1",
        "shipping_line_2",
        "shipping_city",
        "shipping_state",
        "shipping_country",
        "shipping_postcode",
    )
    export_filename = "lbc_members"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.filter(
                metadata__gift_mode__isnull=True,
            )
            .distinct()
            .select_related("plan__product", "customer__subscriber")
        )


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(CustomerAdmin)
