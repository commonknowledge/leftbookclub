from datetime import date

import djstripe
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from djmoney.money import Money
from wagtail.models import Page

from app.models import MembershipPlanPage, MembershipPlanPrice, User
from app.utils.python import uid
from app.utils.stripe import create_gift_subscription_and_promo_code


class Command(BaseCommand):
    help = "Create BookPage for each Shopify product"

    def add_arguments(self, parser):
        parser.add_argument(
            "-e",
            "--email",
            dest="email",
            type=str,
            default=None,
        )
        parser.add_argument(
            "-p",
            "--plan",
            dest="plan",
            type=str,
            default=None,
        )
        parser.add_argument(
            "-c",
            "--card",
            dest="card",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--product",
            dest="product",
            type=str,
            default=None,
        )
        parser.add_argument("--price", dest="price", type=float, default=0)
        parser.add_argument(
            "--interval",
            dest="interval",
            type=str,
            choices=["month", "year"],
            default="month",
        )
        parser.add_argument(
            "--interval_count", dest="interval_count", type=int, default=1
        )
        parser.add_argument(
            "--plan_title",
            dest="plan_title",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--deliveries_per_year", dest="deliveries_per_year", type=int, default=12
        )

    def handle(self, *args, **options):
        # get user from email
        plan = None
        if options.get("plan", None) is not None:
            plan = MembershipPlanPage.objects.filter(pk=options.get("plan")).first()
        if plan is None:
            plan = self.create_test_plan(
                product=options.get("product", None),
                price=options.get("price"),
                plan_title=options.get("plan_title", None),
                deliveries_per_year=options.get("deliveries_per_year"),
                interval=options.get("interval"),
                interval_count=options.get("interval_count"),
            )

        gift_giver_user = None
        payment_card = None
        if options.get("email", None) is not None:
            gift_giver_user = User.objects.filter(email=options.get("email")).first()
        if gift_giver_user is None or gift_giver_user.stripe_customer is None:
            gift_giver_user, password = self.create_user()
            customer, payment_card = self.create_customer_and_payment_card_for_user(
                gift_giver_user
            )

        if payment_card is None and options.get("card", None) is not None:
            payment_card = stripe.PaymentMethod.retrieve(options.get("card"))

        promo_code, gift_giver_subscription = create_gift_subscription_and_promo_code(
            plan, gift_giver_user, payment_card
        )
        print(settings.BASE_URL + reverse("redeem", code=promo_code.code))

    def create_test_plan(
        self, product, plan_title, deliveries_per_year, price, interval, interval_count
    ):
        if product is not None:
            product = stripe.Product.retrieve(product)
            product = djstripe.models.Product.sync_from_stripe_data(product)
        else:
            # sync all products
            products = stripe.Product.list(limit=100)
            for product in products:
                djstripe.models.Product.sync_from_stripe_data(product)

            # pick a Stripe product to use as the basis of this plan
            product = djstripe.models.Product.objects.filter(
                active=True, metadata__shipping__isnull=True
            ).first()

        # create a CMS object to hold the product ID, and pricing data
        gift_plan = MembershipPlanPage(
            title=plan_title
            if plan_title is not None
            else "The Gift of Solidarity" + uid(),
            deliveries_per_year=deliveries_per_year,
            prices=[
                MembershipPlanPrice(
                    price=Money(price, "GBP"),
                    interval=interval,
                    interval_count=interval_count,
                )
            ],
        )
        Page.get_first_root_node().add_child(instance=gift_plan)
        gift_plan.save()
        gift_plan.monthly_price.products.set([product.djstripe_id])
        gift_plan.monthly_price.save()

        return gift_plan

    def create_customer_and_payment_card_for_user(self, user):
        customer = stripe.Customer.create(
            email=user.email, metadata={"text_mode": "true"}
        )
        payment_card = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 5,
                "exp_year": date.today().year + 3,
                "cvc": "314",
            },
        )
        stripe.PaymentMethod.attach(
            payment_card.id,
            customer=customer.id,
        )
        customer = djstripe.models.Customer.sync_from_stripe_data(customer)
        customer.subscriber = user
        customer.save()
        return customer, payment_card

    def create_user(self) -> User:
        id = uid()
        email = f"unit-test-{id}@leftbookclub.com"
        user = User.objects.create_user(id, email, "default_pw_12345_xyz_lbc")
        password = User.objects.make_random_password()
        user.plaintext_password = password
        user.set_password(password)
        user.save(update_fields=["password"])
        return user, password
