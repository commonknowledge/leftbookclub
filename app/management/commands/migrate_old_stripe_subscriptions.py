import djstripe.models
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand
from djstripe.enums import SubscriptionStatus

from app.models.django import User
from app.models.legacy import LegacyGifts

SOLIDARITY_ANNUAL = (
    "prod_LcizN8PVTWkMNa" if settings.DEBUG is False else "prod_LPVfI1zA2KEIiQ"
)
SOLIDARITY_MONTHLY = (
    "prod_LcPK6pYSDxDh9k" if settings.DEBUG is False else "prod_LPVfI1zA2KEIiQ"
)
#
ALLBOOKS_ANNUAL = (
    "prod_Lcj1YRpTYkC7fx" if settings.DEBUG is False else "prod_LQIDOBK7JwW2rt"
)
ALLBOOKS_MONTHLY = (
    "prod_LcPKLnohH0zOb9" if settings.DEBUG is False else "prod_LQIDOBK7JwW2rt"
)
#
CLASSICS_ANNUAL = (
    "prod_Lcj16IInOc32pb" if settings.DEBUG is False else "prod_LPl1Or1YFIGUDl"
)
CLASSICS_MONTHLY = (
    "prod_LcPKtBWnLRIGmn" if settings.DEBUG is False else "prod_LPl1Or1YFIGUDl"
)
#
CONTEMPORARY_ANNUAL = (
    "prod_Lcj0g11ZDHq7De" if settings.DEBUG is False else "prod_LPl0mqD6U0Nr27"
)
CONTEMPORARY_MONTHLY = (
    "prod_LcPK2ze6AGTAgl" if settings.DEBUG is False else "prod_LPl0mqD6U0Nr27"
)
#
SHIPPING_PRODUCT = (
    "prod_Lcasas0SaT0GYB" if settings.DEBUG is False else "prod_LcCgBFw4kdnhTp"
)

valid_products = [
    SOLIDARITY_ANNUAL,
    SOLIDARITY_MONTHLY,
    ALLBOOKS_ANNUAL,
    ALLBOOKS_MONTHLY,
    CLASSICS_ANNUAL,
    CLASSICS_MONTHLY,
    CONTEMPORARY_ANNUAL,
    CONTEMPORARY_MONTHLY,
]

invalid_statuses = [
    SubscriptionStatus.canceled.lower(),
    SubscriptionStatus.incomplete_expired.lower(),
]


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    def add_arguments(self, parser):
        parser.add_argument(
            "-b", "--batch", dest="batch_size", type=int, default=100000
        )

        parser.add_argument("-p", "--product", dest="product", type=str, default=None)

        parser.add_argument(
            "-s", "--subscription", dest="subscription", type=str, default=None
        )

        parser.add_argument(
            "-es", "--excluded_subs", dest="excluded_subs", nargs="+", default=[]
        )

    def handle(self, *args, **options):
        batch_size = options.get("batch_size")
        product = options.get("product")
        subscription = options.get("subscription")
        excluded_subs = options.get("excluded_subs")

        # Get all subscriptions that DON'T include valid products
        qs = djstripe.models.Subscription.objects.all()

        if product is not None:
            qs = qs.filter(items__plan__product=product)

        if subscription is not None:
            qs = qs.filter(id=subscription)

        qs = qs.exclude(
            items__plan__product__in=valid_products,
            status__in=invalid_statuses,
            id__in=excluded_subs,
        )

        legacy_subs = qs.select_related("plan__product")[:batch_size]

        print("Syncing legacy subs", len(legacy_subs), legacy_subs)
        for sub in legacy_subs:
            # refresh
            stripe_sub = stripe.Subscription.retrieve(sub.id)
            sub = djstripe.models.Subscription.sync_from_stripe_data(stripe_sub)

            if (
                sub.status.lower() not in invalid_statuses
                and sub.id not in excluded_subs
            ):
                # legacy subscriptions only had single products
                si = sub.items.exclude(plan__product__in=valid_products).first()

                if si is not None and si.plan.product.id not in valid_products:
                    print("Trying", sub.id, sub.status)

                    # create a replacement Price with [old price / interval] + 2022 products
                    new_plan = get_replacement_plan_for_old_plan(si.plan)

                    if new_plan is None:
                        print(
                            sub.id, "| old_si ->", si.id, "| new_plan -> NO CHANGE !!!"
                        )
                        continue

                    print(sub.id, "| old_si ->", si.id, "| new_plan ->", new_plan.id)

                    stripe.Subscription.modify(
                        sub.id,
                        metadata={
                            "legacy_stripe_product_id": si.plan.product.id,
                            "legacy_stripe_product_name": si.plan.product.name,
                            "legacy_stripe_plan_id": si.plan.id,
                            "legacy_stripe_plan_name": si.plan.nickname,
                        },
                    )

                    # add the new si to the subscription
                    stripe.SubscriptionItem.create(
                        subscription=sub.id,
                        price=new_plan.id,
                        quantity=1,
                    )

                    # delete the old si
                    stripe.SubscriptionItem.delete(si.id)

                    # update
                    subscription = stripe.Subscription.retrieve(sub.id)
                    djstripe.models.Subscription.sync_from_stripe_data(subscription)


# product_ids


def get_replacement_plan_for_old_plan(plan: djstripe.models.Plan) -> str:
    product_name = plan.product.name

    ####
    #### Identify product ID
    ####
    # Historical LBC products were defined on the price name, not product name
    if plan.product.id == "prod_DctmmNsQ5TOdQC":
        product_name = plan.nickname

    print("Migrating product:", product_name)

    is_legacy = "_" in product_name
    is_contemporary = "contemporary" in product_name
    is_classic = "classic" in product_name
    is_both = "both" in product_name
    #
    is_solidarity = "both_solidarity" in product_name
    #
    is_annual = plan.interval == "year"

    product_id = None

    if is_legacy:
        if is_solidarity:
            if is_annual:
                product_id = SOLIDARITY_ANNUAL
            else:
                product_id = SOLIDARITY_MONTHLY
        elif is_classic:
            if is_annual:
                product_id = CLASSICS_ANNUAL
            else:
                product_id = CLASSICS_MONTHLY
        elif is_contemporary:
            if is_annual:
                product_id = CONTEMPORARY_ANNUAL
            else:
                product_id = CONTEMPORARY_MONTHLY
        elif is_both:
            if is_annual:
                product_id = ALLBOOKS_ANNUAL
            else:
                product_id = ALLBOOKS_MONTHLY

    if product_id is None:
        return

    price = None

    # See if it already exists
    prices = stripe.Price.search(query=f'metadata["legacy_stripe_plan_id"]:"{plan.id}"')
    if len(prices.data) > 0:
        price = prices.data[0]

    # Else create it
    if price is None:
        price = stripe.Price.create(
            nickname=product_name.replace("_", " "),
            unit_amount=int(plan.amount_decimal),
            currency=plan.currency,
            recurring={
                "interval": plan.interval,
                "interval_count": plan.interval_count,
            },
            product=product_id,
            metadata={
                "legacy_subscription_name": product_name,
                "legacy_stripe_product_id": plan.product.id,
                "legacy_stripe_product_name": plan.product.name,
                "legacy_stripe_plan_id": plan.id,
                "legacy_stripe_plan_name": plan.nickname,
                "is_contemporary": is_contemporary,
                "is_classic": is_classic,
                "is_both": is_both,
                "is_solidarity": is_solidarity,
                "is_annual": is_annual,
            },
        )

    return price
