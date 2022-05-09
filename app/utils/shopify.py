import json

import pycountry
import shopify
from dateutil.parser import parse
from django.conf import settings


def create_session(
    domain=settings.SHOPIFY_DOMAIN,
    api_version="2021-10",
    access_token=settings.SHOPIFY_PRIVATE_APP_PASSWORD,
):
    return shopify.Session(domain, api_version, access_token)


def metafields_to_dict(metafields):
    return {f.key: parse_metafield(f) for f in metafields}


def parse_metafield(f):
    if f.type in [
        "date",
        "date_time",
    ]:
        return parse(f.value)
    elif (
        f.type
        in [
            "json_string",
            "json",
            "dimension",
            "rating",
            "rating",
            "volume",
            "weight",
        ]
        or f.value_type == "json_string"
    ):
        return json.loads(f.value)
    else:
        return f.value


def convert_stripe_address_to_shopify(user):
    shipping = user.stripe_customer.shipping
    address = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "address1": shipping.get("address").get("line1"),
        "address2": shipping.get("address").get("line2"),
        "city": shipping.get("address").get("city"),
        "country": pycountry.countries.search_fuzzy(
            shipping.get("address").get("country")
        )[0].name,
        "zip": shipping.get("address").get("postal_code"),
        "country_code": shipping.get("address").get("country"),
    }

    ret = {}
    for k in address:
        if address.get(k, None) is not None and address.get(k, "") != "":
            ret[k] = address[k]

    if len(ret.keys()) == 0:
        return None

    return ret


def to_shopify_address(user):
    if (
        user.stripe_customer
        and user.stripe_customer.shipping is not None
        and user.stripe_customer.shipping.get("address", {}).get("line1", False)
    ):
        return convert_stripe_address_to_shopify(user)
    return None


def create_shopify_order(user, line_items=list(), email=False, tags=list()):
    if not settings.SHOPIFY_DOMAIN or settings.SHOPIFY_PRIVATE_APP_PASSWORD:
        with shopify.Session.temp(
            settings.SHOPIFY_DOMAIN, "2021-10", settings.SHOPIFY_PRIVATE_APP_PASSWORD
        ):
            o = shopify.Order()
            o.line_items = line_items
            # [
            #     {
            #         # "variant_id": variant_id,
            #         "title": "New Signup",
            #         "price": 0,
            #         "requiresShipping": True,
            #         "quantity": quantity,
            #     }
            # ]
            o.financial_status = "paid"

            # Shopify customer link
            # if user.shopify_customer_id is None:
            #     cs = shopify.Customer.search(email=o.email)
            #     if len(cs) > 0:
            #         user.shopify_customer_id = cs[0].id
            #         user.save()
            #     else:
            #         c = shopify.Customer()
            #         c.first_name = "andres"
            #         c.last_name = "cepeda"
            #         if to_shopify_address(user) is not None:
            #             c.addresses = [to_shopify_address(user)]
            #             c.default_address = to_shopify_address(user)
            #         c.save()
            #         user.shopify_customer_id = c.id
            #         user.save()
            # if user.shopify_customer_id is None:
            #     raise ValueError("Couldn't create shipping order, because customer couldn't be identified")

            # o.customer = { "id": user.shopify_customer_id }
            if not email:
                o.send_receipt = False
                o.send_fulfillment_receipt = False
                o.note = f"Email: {user.primary_email}. Stripe customer: {user.stripe_customer.id}."
            else:
                o.email = user.primary_email

            o.shipping_address = to_shopify_address(user)
            o.tags = tags

            if not settings.STRIPE_LIVE_MODE:
                tags += ["TEST"]

            o.save()

            if not settings.STRIPE_LIVE_MODE:
                o.cancel()
