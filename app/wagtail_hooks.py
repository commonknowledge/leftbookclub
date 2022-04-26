import djstripe.models
import shopify
from admin_list_controls.actions import SubmitForm
from admin_list_controls.components import Button, Columns, Panel
from admin_list_controls.filters import BooleanFilter, ChoiceFilter, TextFilter
from admin_list_controls.views import ListControlsIndexView
from django.db.models import Count
from django.templatetags.static import static
from django.utils.html import format_html
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.core import hooks

from app.models.django import User
from app.models.stripe import LBCCustomer, LBCProduct, LBCSubscription, ShippingZone


@hooks.register("insert_global_admin_css")
def global_admin_css():
    return format_html('<link rel="stylesheet" href="{}">', static("wagtailadmin.css"))


class ShippingAdmin(ModelAdmin):
    model = ShippingZone
    menu_icon = "fa-truck"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    # list_display = ('title', 'author')
    # list_filter = ('author',)
    # search_fields = ('title', 'author')


modeladmin_register(ShippingAdmin)


class IndexView(ListControlsIndexView):
    def build_list_controls(self):
        products = list(
            LBCSubscription.objects.order_by()
            .values_list("plan__product__id", "plan__product__name")
            .annotate(frequency=Count("plan__product__id"))
            .order_by("-frequency")
        )
        statuses = list(
            LBCSubscription.objects.all().values_list("status").order_by().distinct()
        )
        config = [
            Panel()(
                Columns()(
                    ChoiceFilter(
                        name="status",
                        label="Subscription Status",
                        multiple=True,
                        choices=tuple((s[0], s[0]) for s in statuses),
                        default_value="active",
                        apply_to_queryset=lambda queryset, values: queryset.filter(
                            status__in=values
                        ),
                    ),
                    ChoiceFilter(
                        name="product",
                        label="Product",
                        multiple=True,
                        choices=tuple((p[0], p[1]) for p in products),
                        apply_to_queryset=lambda queryset, values: queryset.filter(
                            plan__product__in=values
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
    index_view_class = IndexView
    model = LBCSubscription
    menu_label = "Members"  # ditch this to use verbose_name_plural from model
    menu_icon = "fa-users"  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    add_to_settings_menu = False  # or True to add your model to the Settings sub-menu
    exclude_from_explorer = (
        False  # or True to exclude pages of this type from Wagtail's explorer view
    )
    list_display = (
        "id",
        "product",
        "status",
        "metadata",
        "recipient_name",
        "customer_id",
    )
    list_export = (
        "recipient_name",
        "shipping_line_1",
        "shipping_line_1",
        "shipping_line_2",
        "shipping_city",
        "shipping_country",
        "shipping_zip",
    )
    export_filename = "lbc_members"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(
            customer__shipping__address__isnull=False, metadata__gift_mode__isnull=True
        )


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(CustomerAdmin)


def create_shopify_order(
    self, user, variant_id, quantity=1, tags=["Membership Shipment"]
):
    o = shopify.Order()
    o.line_items = [{"variant_id": variant_id, "quantity": quantity}]
    o.financial_status = "paid"
    o.email = self.user.primary_email
    c = shopify.Customer.search(email=o.email)
    o.customer = {"id": c[0].id}
    o.send_receipt = False
    o.send_fulfillment_receipt = False
    # TODO: convert Shipping address from Stripe to Shopify format
    o.shipping_address = {
        "address1": "1 Byers Road",
        "address2": "Flat 4/2",
        "city": "Glasgow",
        "country": "United Kingdom",
        "zip": "G115RD",
        "name": "Jan Baykara",
        "country_code": "GB",
    }
    o.tags = tags
    return o
