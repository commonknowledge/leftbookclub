import random
import string
import time
from datetime import date, datetime
from http import HTTPStatus
from multiprocessing.sharedctypes import Value

import djstripe.models
from django.test import TestCase
from django.urls import reverse
from djmoney.money import Money
from djstripe.enums import ProductType

from app.forms import UpgradeAction, UpgradeForm
from app.models import *
from app.utils.python import uid
from app.utils.stripe import (
    configure_gift_giver_subscription_and_code,
    create_gift_recipient_subscription,
    create_gift_subscription_and_promo_code,
    recreate_one_off_stripe_price,
)
from app.views import (
    CompletedGiftPurchaseView,
    GiftCodeRedeemView,
    GiftMembershipSetupView,
    SubscriptionCheckoutView,
    UpgradeView,
)


class PlansAndShippingTestCase(TestCase):
    def setUp(self):
        ShippingZone.objects.all().delete()

    # No zone, ROW should include all acceptable countries
    # and all codes are cool with stripe
    def test_countries_are_acceptable_to_stripe(self):
        self.assertEqual(
            set(ShippingZone.default_zone.country_codes)
            - set(ShippingZone.stripe_allowed_countries),
            set(),
        )

    # With one zone, that zone should country_codes = input
    def test_one_zone(self):
        input_codes = ["FR", "DE"]
        zone = ShippingZone.objects.create(
            nickname="Test", code="EU", countries=input_codes
        )
        self.assertSetEqual(set(zone.country_codes), set(input_codes))

    # Get zone for code ^ should work => same zone as above
    def test_zone_get_for_country(self):
        input_codes = ["FR", "DE"]
        zone = ShippingZone.objects.create(
            nickname="Test", code="EU", countries=input_codes
        )
        for code in input_codes:
            calculated_zone = ShippingZone.get_for_country(code)
            self.assertEqual(calculated_zone, zone)

    def test_use_most_specific_zone(self):
        """
        Expect the zone identified to be the one with the fewest other countries in it.
        """
        ShippingZone.objects.create(
            nickname="West Europe", code="WER", countries=["FR", "DE"]
        )
        expected_zone = ShippingZone.objects.create(
            nickname="Test 2", code="FR", countries=["FR"]
        )
        ShippingZone.objects.create(
            nickname="Eurasia",
            code="EUR",
            countries=["FR", "DE", "PT", "IT", "ES", "GR", "RU"],
        )
        calculated_zone = ShippingZone.get_for_country("FR")
        self.assertEqual(calculated_zone, expected_zone)

    # Get zone for code !!!not in^ should work => ROW
    def test_row_country_checker(self):
        input_codes = ["FR", "DE"]
        not_involved_country = "US"
        ShippingZone.objects.create(nickname="Test", code="EU", countries=input_codes)
        calculated_zone = ShippingZone.get_for_country(not_involved_country)
        self.assertEqual(calculated_zone.code, ShippingZone.default_zone.code)

    # When a zone is set, ROW should not include those countries
    def test_row_for_remaining_countries(self):
        input_codes = ["FR", "DE"]
        # These two countries should not show up in ROW
        ShippingZone.objects.create(nickname="Test", code="EU", countries=input_codes)
        for code in input_codes:
            self.assertNotIn(code, ShippingZone.default_zone.country_codes)

        self.assertEqual(
            len(ShippingZone.default_zone.country_codes),
            len(ShippingZone.all_country_codes) - len(input_codes),
        )

    def test_row_for_remaining_countries(self):
        # Expect default ROW rate to be 0 GBP
        self.assertEqual(Money(0, "GBP"), ShippingZone.default_zone.rate)

    # When ROW is set, it should be returned rather than the default
    def test_row_for_remaining_countries(self):
        row_rate = Money(100, "GBP")
        ShippingZone.objects.create(nickname="Test", code="EU", countries=["FR", "DE"])
        ShippingZone.objects.create(
            nickname="Test 2", code="ROW", rest_of_world=True, rate=row_rate
        )
        self.assertEqual(
            ShippingZone.get_for_country("IT").code, ShippingZone.default_zone.code
        )
        self.assertEqual(row_rate, ShippingZone.default_zone.rate)

    # When ROW is set, it should be returned rather than the default
    def test_shipping_calculation(self):
        self.assertEqual(ShippingZone.objects.count(), 0)
        zone = ShippingZone(
            nickname="Test", code="EU", countries=["FR"], rate=Money(3, "GBP")
        )
        solidarity_plan = MembershipPlanPage(
            title="Solidarity",
            deliveries_per_year=12,
            prices=[
                MembershipPlanPrice(
                    price=Money(10, "GBP"), interval="month", interval_count=1
                ),
                MembershipPlanPrice(
                    price=Money(100, "GBP"), interval="year", interval_count=1
                ),
            ],
        )
        # Deliveries per period
        self.assertEqual(solidarity_plan.annual_price.deliveries_per_billing_period, 12)
        self.assertEqual(solidarity_plan.monthly_price.deliveries_per_billing_period, 1)
        # Fees
        self.assertEqual(
            # 12 shipments per year * £3 = 18
            solidarity_plan.annual_price.shipping_fee(zone),
            Money(36, "GBP"),
        )
        self.assertEqual(
            # Plus £100
            solidarity_plan.annual_price.price_including_shipping(zone),
            Money(136, "GBP"),
        )
        self.assertEqual(
            # 6 shipments per year is 1 shipments per month, so should be £3
            solidarity_plan.monthly_price.shipping_fee(zone),
            Money(3, "GBP"),
        )
        self.assertEqual(
            # Plus £10 = £13
            solidarity_plan.monthly_price.price_including_shipping(zone),
            Money(13, "GBP"),
        )

        classic_plan = MembershipPlanPage(
            title="Classic Books Plan",
            deliveries_per_year=6,
            prices=[
                MembershipPlanPrice(
                    price=Money(10, "GBP"), interval="month", interval_count=1
                ),
                MembershipPlanPrice(
                    price=Money(20, "GBP"), interval="month", interval_count=2
                ),
                MembershipPlanPrice(
                    price=Money(100, "GBP"), interval="year", interval_count=1
                ),
            ],
        )
        irregular_price = classic_plan.prices.get(interval="month", interval_count=2)

        # Deliveries per period
        self.assertEqual(irregular_price.deliveries_per_billing_period, 1)
        self.assertEqual(classic_plan.annual_price.deliveries_per_billing_period, 6)
        self.assertEqual(classic_plan.monthly_price.deliveries_per_billing_period, 0.5)
        # Fees
        self.assertEqual(
            # 6 shipments per year, billed every two months, £3 each delivery
            irregular_price.shipping_fee(zone),
            Money(3, "GBP"),
        )
        self.assertEqual(
            # 6 shipments per year * £3 = 18
            classic_plan.annual_price.shipping_fee(zone),
            Money(18, "GBP"),
        )
        self.assertEqual(
            # Plus £100 = £118
            classic_plan.annual_price.price_including_shipping(zone),
            Money(118, "GBP"),
        )
        self.assertEqual(
            # 6 shipments per year is 0.5 shipments per month, so should be £1.5
            classic_plan.monthly_price.shipping_fee(zone),
            Money(1.50, "GBP"),
        )
        self.assertEqual(
            # Plus £10 = £11.5
            classic_plan.monthly_price.price_including_shipping(zone),
            Money(11.50, "GBP"),
        )

    # When ROW is set, it should be returned rather than the default
    def test_row_for_remaining_countries(self):
        row_rate = Money(100, "GBP")
        ShippingZone.objects.create(nickname="Test", code="EU", countries=["FR", "DE"])
        ShippingZone.objects.create(
            nickname="Test 2", code="ROW", rest_of_world=True, rate=row_rate
        )
        self.assertEqual(
            ShippingZone.get_for_country("IT").code, ShippingZone.default_zone.code
        )
        self.assertEqual(row_rate, ShippingZone.default_zone.rate)

    # When ROW is set, it should be returned rather than the default
    def test_shipping_excluded(self):
        self.assertEqual(ShippingZone.objects.count(), 0)
        zone = ShippingZone.objects.create(
            nickname="Test", code="UK", countries=["GB"], rate=Money(3, "GBP")
        )
        expensive_zone = ShippingZone.objects.create(
            nickname="Test", code="EU", countries=["FR"], rate=Money(10, "GBP")
        )
        product = LBCProduct.objects.create(
            id="prod_fake", name="Some Product", type=ProductType.service
        )
        solidarity_plan = MembershipPlanPage(
            slug="solidarity",
            title="Solidarity",
            deliveries_per_year=12,
            prices=[
                MembershipPlanPrice(
                    price=Money(10, "GBP"),
                    interval="month",
                    interval_count=1,
                    products=[product],
                ),
                MembershipPlanPrice(
                    price=Money(100, "GBP"),
                    interval="year",
                    interval_count=1,
                    free_shipping_zones=[zone],
                    products=[product],
                ),
            ],
        )

        # Sanity check: monthly price without free_shipping_zones defined will charge for shipping
        self.assertGreater(
            solidarity_plan.monthly_price.shipping_fee(expensive_zone),
            Money(0, expensive_zone.rate_currency),
        )

        # First, assert that shipping is calculated properly when `free_shipping_zones` is set
        self.assertGreater(
            solidarity_plan.annual_price.shipping_fee(expensive_zone),
            Money(0, expensive_zone.rate_currency),
        )
        line_items = solidarity_plan.annual_price.to_checkout_line_items(
            zone=expensive_zone
        )
        # self.assertEqual(len(line_items), 2)
        for item in line_items:
            if "shipping" in item["price_data"]["metadata"].keys():
                self.assertGreater(item["price_data"]["unit_amount_decimal"], 0)

        # Now check that `free_shipping_zones` has the desired effects:

        # 1. Shipping is calculated abstractly as being excluded for this annual price
        self.assertEqual(
            solidarity_plan.annual_price.shipping_fee(zone),
            Money(0, zone.rate_currency),
        )

        # 2. And this calculation means that a line item for shipping is presently 0
        # (meaning we can upgrade them to a different shipping fee later on)
        line_items = solidarity_plan.annual_price.to_checkout_line_items(zone=zone)
        for item in line_items:
            if "shipping" in item["price_data"]["metadata"].keys():
                self.assertEqual(item["price_data"]["unit_amount_decimal"], 0)


class ComplexPlansAndPrices(TestCase):
    @classmethod
    def setUpTestData(cls):
        contemporary_monthly = LBCProduct.objects.create(
            id="prod_contemporary_monthly",
            name="Some Product",
            type=ProductType.service,
        )
        classic_monthly = LBCProduct.objects.create(
            id="prod_classic_monthly", name="Some Product", type=ProductType.service
        )
        contemporary_annual = LBCProduct.objects.create(
            id="prod_contemporary_annual", name="Some Product", type=ProductType.service
        )
        classic_annual = LBCProduct.objects.create(
            id="prod_classic_annual", name="Some Product", type=ProductType.service
        )
        cls.plan = MembershipPlanPage(
            title="Classics",
            deliveries_per_year=12,
            prices=[
                MembershipPlanPrice(
                    interval="year",
                    interval_count=1,
                    products=[
                        classic_annual,
                        # contemporary_annual
                    ],
                ),
                MembershipPlanPrice(
                    interval="month",
                    interval_count=1,
                    products=[classic_monthly, contemporary_monthly],
                ),
            ],
        )

    def test_create_line_items_for_price_with_single_product(self):
        line_items = self.plan.annual_price.to_checkout_line_items(
            zone=ShippingZone.default_zone
        )
        self.assertEqual(
            line_items[0]["price_data"]["product"],
            self.plan.annual_price.products.first().id,
        )

    def test_create_line_items_for_price_with_multiple_products(self):
        with self.assertRaises(ValueError):
            self.plan.monthly_price.to_checkout_line_items(
                zone=ShippingZone.default_zone
            )
        product = self.plan.monthly_price.products.first()
        line_items = self.plan.monthly_price.to_checkout_line_items(
            product=product, zone=ShippingZone.default_zone
        )
        self.assertEqual(line_items[0]["price_data"]["product"], product.id)


class BaseGiftTestCase(TestCase):
    users = []
    passwords = {}

    @classmethod
    def create_user(cls) -> User:
        id = uid()
        email = f"unit-test-{id}@leftbookclub.com"
        user = User.objects.create_user(id, email, "default_pw_12345_xyz_lbc")
        password = User.objects.make_random_password()
        user.plaintext_password = password
        cls.passwords[user] = password
        user.set_password(password)
        user.save(update_fields=["password"])
        cls.users += [user]
        return user

    @classmethod
    def setUpTestData(cls):
        # sync all products
        products = stripe.Product.list(limit=100)
        for product in products:
            djstripe.models.Product.sync_from_stripe_data(product)

        # sync all coupons
        coupons = stripe.Coupon.list(limit=100)
        for coupon in coupons:
            djstripe.models.Coupon.sync_from_stripe_data(coupon)

        # create user
        cls.gift_giver_user = cls.create_user()
        cls.gift_recipient_user = cls.create_user()

        # set up stripe customer details
        customer = stripe.Customer.create(
            email=cls.gift_giver_user.email, metadata={"text_mode": "true"}
        )
        cls.payment_card = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 5,
                "exp_year": date.today().year + 3,
                "cvc": "314",
            },
        )
        stripe.PaymentMethod.attach(
            cls.payment_card.id,
            customer=customer.id,
        )
        customer = djstripe.models.Customer.sync_from_stripe_data(customer)
        customer.subscriber = cls.gift_giver_user
        customer.save()

        ShippingZone.objects.create(
            rest_of_world=True, code="ROW", nickname="ROW", rate=Money(2, "GBP")
        )

        # configure a gift plan
        product = djstripe.models.Product.objects.filter(
            active=True, metadata__shipping__isnull=True
        ).first()
        gift_plan = MembershipPlanPage(
            title="The Gift of Solidarity",
            deliveries_per_year=12,
            prices=[
                MembershipPlanPrice(
                    price=Money(10, "GBP"), interval="month", interval_count=1
                )
            ],
        )
        Page.get_first_root_node().add_child(instance=gift_plan)
        gift_plan.save()
        gift_plan.monthly_price.products.set([product.djstripe_id])
        gift_plan.monthly_price.save()
        cls.gift_plan = gift_plan

        return super().setUpTestData()

    @classmethod
    def tearDownClass(cls) -> None:
        # for user in cls.users:
        #     if user.stripe_customer is not None:
        #         stripe.Customer.delete(user.stripe_customer.id)
        return super().tearDownClass()


class GiftTestCase(BaseGiftTestCase):
    def test_buying_gift_card_and_redeeming_it_yourself(self):
        (
            promo_code,
            gift_giver_subscription,
        ) = create_gift_subscription_and_promo_code(
            self.gift_plan,
            self.gift_giver_user,
            self.payment_card,
            metadata={"automated_test_record": "true"},
        )

        self.assertEqual(
            self.gift_giver_user.active_subscription,
            None,
            "Gift subscriptions should not count as active membership subscriptions for the gift purchaser.",
        )

        # Test that promo code and updated_subcription have correct metadata
        self.assertEqual(
            gift_giver_subscription.metadata["automated_test_record"],
            "true",
            "configure_gift_giver_subscription_and_code() should pass through custom metadata -- to subscription",
        )
        self.assertIsNotNone(gift_giver_subscription.metadata["gift_mode"])
        self.assertEqual(gift_giver_subscription.metadata["promo_code"], promo_code.id)
        self.assertEqual(
            promo_code.metadata["gift_giver_subscription"], gift_giver_subscription.id
        )
        self.assertEqual(
            promo_code.metadata["automated_test_record"],
            "true",
            "configure_gift_giver_subscription_and_code() should pass through custom metadata -- to promo_code",
        )

        # Test redemption on self
        recipient_subscription = create_gift_recipient_subscription(
            gift_giver_subscription, self.gift_giver_user
        )

        # Assert that the recipient subscription is correctly set up in Stripe
        self.assertEqual(
            recipient_subscription.status, djstripe.enums.SubscriptionStatus.active
        )
        self.assertNotEqual(recipient_subscription.discount, None)
        self.assertEqual(
            get_primary_product_for_djstripe_subscription(gift_giver_subscription),
            get_primary_product_for_djstripe_subscription(recipient_subscription),
        )

        # Assert metadata on gift recipient sub is correct
        self.assertEqual(
            recipient_subscription.metadata["gift_giver_subscription"],
            gift_giver_subscription.id,
        )
        self.assertEqual(recipient_subscription.metadata["promo_code"], promo_code.id)

        # Assert that this has trickled through to the user model methods
        self.assertEqual(
            self.gift_giver_user.active_subscription, recipient_subscription
        )

        # Assert that the promo code can't be used anymore, because it's been redeemed
        promo_code = stripe.PromotionCode.retrieve(promo_code.id)
        self.assertFalse(promo_code.active)

    def test_buying_gift_card_and_redeeming_it_with_someone_else(self):
        (
            promo_code,
            gift_giver_subscription,
        ) = create_gift_subscription_and_promo_code(
            self.gift_plan,
            self.gift_giver_user,
            self.payment_card,
            metadata={"automated_test_record": "true"},
        )
        self.assertEqual(
            self.gift_giver_user.active_subscription,
            None,
            "Gift subscriptions should not count as active membership subscriptions for the gift purchaser.",
        )

        # Test that promo code and updated_subcription have correct metadata
        self.assertEqual(
            gift_giver_subscription.metadata["automated_test_record"],
            "true",
            "configure_gift_giver_subscription_and_code() should pass through custom metadata -- to subscription",
        )
        self.assertIsNotNone(gift_giver_subscription.metadata["gift_mode"])
        self.assertEqual(gift_giver_subscription.metadata["promo_code"], promo_code.id)
        self.assertEqual(
            promo_code.metadata["gift_giver_subscription"], gift_giver_subscription.id
        )
        self.assertEqual(
            promo_code.metadata["automated_test_record"],
            "true",
            "configure_gift_giver_subscription_and_code() should pass through custom metadata -- to promo_code",
        )

        # Test redemption on self
        recipient_subscription = create_gift_recipient_subscription(
            gift_giver_subscription, self.gift_recipient_user
        )

        # Assert that the recipient subscription is correctly set up in Stripe
        self.assertEqual(
            recipient_subscription.status, djstripe.enums.SubscriptionStatus.active
        )
        self.assertNotEqual(recipient_subscription.discount, None)
        self.assertEqual(
            get_primary_product_for_djstripe_subscription(gift_giver_subscription),
            get_primary_product_for_djstripe_subscription(recipient_subscription),
        )

        # Assert metadata on gift recipient sub is correct
        self.assertEqual(
            recipient_subscription.metadata["gift_giver_subscription"],
            gift_giver_subscription.id,
        )
        self.assertEqual(recipient_subscription.metadata["promo_code"], promo_code.id)

        # Assert that this has trickled through to the user model methods
        self.assertEqual(
            self.gift_recipient_user.active_subscription, recipient_subscription
        )

        # Assert that nothing has gone backwards
        import time

        self.driver.implicitly_wait(10)
        self.gift_recipient_user.refresh_stripe_data()
        self.assertEqual(
            self.gift_recipient_user.active_subscription, recipient_subscription
        )

        # Assert that the promo code can't be used anymore, because it's been redeemed
        promo_code = stripe.PromotionCode.retrieve(promo_code.id)
        self.assertFalse(promo_code.active)

    def test_gift_card_redemption_for_migrated_product(self):
        """
        In this scenario, a gift giver purchases a gift subscription, and then the gift subscription's product is migrated
        but the associated coupon is still applying only to the original product.

        1. The gift giver purchases a gift subscription
        2. The gift subscription's product is migrated
        3. TEST: The gift is redeemed successfully
        """

        ####
        #### 1. Create the gift giver subscription
        ####

        (
            promo_code,
            gift_giver_subscription,
        ) = create_gift_subscription_and_promo_code(
            self.gift_plan,
            self.gift_giver_user,
            self.payment_card,
            metadata={"automated_test_record": "true"},
        )

        ####
        #### 2. Migrate the product
        ####
        primary = get_primary_product_for_djstripe_subscription(gift_giver_subscription)
        si = gift_giver_subscription.items.get(plan__product=primary)

        # add new product price
        another_product = djstripe.models.Product.objects.filter(
            active=True, metadata__shipping__isnull=True
        )[2]
        # ensure we're actually shifting them to a new product
        self.assertNotEqual(primary.id, another_product.id)
        # new product price
        price_args = recreate_one_off_stripe_price(si.plan)
        price_args["product"] = another_product.id
        new_price = stripe.Price.create(**price_args)

        # add the new product price
        stripe.SubscriptionItem.create(
            subscription=gift_giver_subscription.id,
            price=new_price.id,
            quantity=1,
        )

        # delete the old product price
        stripe.SubscriptionItem.delete(si.id)

        # sync this down for further testing
        subscription = stripe.Subscription.retrieve(gift_giver_subscription.id)
        gift_giver_subscription = djstripe.models.Subscription.sync_from_stripe_data(
            subscription
        )

        ####
        #### Test redemption
        ####

        # Test redemption on self
        recipient_subscription = create_gift_recipient_subscription(
            gift_giver_subscription, self.gift_recipient_user
        )

        # Assert that the recipient subscription is correctly set up in Stripe
        self.assertEqual(
            recipient_subscription.status, djstripe.enums.SubscriptionStatus.active
        )
        self.assertNotEqual(recipient_subscription.discount, None)
        self.assertEqual(
            get_primary_product_for_djstripe_subscription(gift_giver_subscription),
            get_primary_product_for_djstripe_subscription(recipient_subscription),
        )

        # Assert that the promo code can't be used anymore, because it's been redeemed
        promo_code = stripe.PromotionCode.retrieve(promo_code.id)
        self.assertFalse(promo_code.active)

    # def test_redemption_flow_views(self):
    #     # 1. Create subscription programatically, as we can't go through the Stripe UI here

    # (
    #     promo_code,
    #     gift_giver_subscription,
    # ) = create_gift_subscription_and_promo_code(
    #   self.gift_plan,
    #   self.gift_giver_user,
    #   self.payment_card,
    #   metadata={"automated_test_record": "true"}
    # )

    #     # 2. Mock the UI flow for redemption

    #     ### First, test that promo code handling works at all
    #     form = GiftCodeRedeemView.form_class(data={"code": "--" + promo_code.code})
    #     self.assertEqual(form.errors["code"], ["This isn't a real code"])

    #     ### Then test that the view handles form errors OK.
    #     response = self.client.post(reverse("redeem"), {"code": "=="+promo_code.code})
    #     self.assertEqual(response.url, reverse('redeem'))

    #     ### Then test the view actually shows up in the URL
    #     response = self.client.get(reverse("redeem"))
    #     self.assertEqual(response.status_code, HTTPStatus.OK)
    #     self.assertContains(response, "Someone bought you a gift membership!")

    #     ### Then test that a successful code takes you to the shipping page
    #     response = self.client.post(reverse("redeem"), {"code": promo_code.code})
    #     self.assertRedirects(response, reverse('redeem_setup'), status_code=302, target_status_code=200)

    #     # Shipping page - enter shipping info
    #     response = self.client.get(reverse("redeem_setup"))
    #     self.assertContains(response, "Set up shipping")
    #     response = self.client.post(
    #         reverse("redeem_setup"),
    #         {
    #             "name": "Test",
    #             "line1": "Test",
    #             "line2": "Test",
    #             "postal_code": "Test",
    #             "city": "Test",
    #             "state": "Test",
    #             "country": "US",
    #         },
    #     )

    #     # Should see success page
    #     self.assertRedirects(response, reverse('completed_gift_redemption'), status_code=302, target_status_code=200)
    #     response = self.client.get(reverse("completed_gift_redemption"))

    #     #
    #     self.assertContains(
    #         response, "You've successfully redeemed a gift card for a membership."
    #     )


# from app.utils.tests import SeleniumTestCase
# from selenium.webdriver.common.by import By
# import time

# class DisableCSRFMiddleware(object):

#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         setattr(request, '_dont_enforce_csrf_checks', True)
#         response = self.get_response(request)
#         return response

# class IntegrationGiftTestCase(SeleniumTestCase, BaseGiftTestCase):
#     def test_gift_flow(self):
#         # 1. Create subscription programatically, as we can't go through the Stripe UI here

# (
#     promo_code,
#     gift_giver_subscription,
# ) = create_gift_subscription_and_promo_code(
#   self.gift_plan,
#   self.gift_giver_user,
#   self.payment_card,
#   metadata={"automated_test_record": "true"}
# )

#         # 2. Mock the UI flow for redemption
#         ENTER_KEY = u'\ue007'

#         def click_link(el):
#             # el.click()
#             login_url = el.get_attribute('href')
#             self.driver.get(login_url)

#         # Test error message
#         self.driver.get(f"{self.live_server_url}{reverse('redeem')}")
#         print("Expecting /redeem", self.driver.current_url)
#         self.driver.find_element(By.CSS_SELECTOR, "form#redeem-form input[name=code]").send_keys("ObviouslyFalsePromoCode")
#         self.driver.find_element(By.CSS_SELECTOR, "form#redeem-form input[name=code]").submit()
#         self.assertContains(
#           self.driver.find_element(By.CSS_SELECTOR, "form#redeem-form .list-unstyled.text-danger").text,
#           "This isn't a real code"
#         )
#         self.driver.implicitly_wait(4)

#         # Test success path message
#         print("Expecting /redeem", self.driver.current_url)
#         self.driver.get(f"{self.live_server_url}{reverse('redeem')}")
#         print(self.driver.current_url)
#         self.driver.find_element(By.CSS_SELECTOR, "form#redeem-form input[name=code]").send_keys(promo_code.code)
#         self.driver.find_element(By.CSS_SELECTOR, "form#redeem-form input[name=code]").submit()

#         # Should navigate to signup
#         self.driver.implicitly_wait(4)
#         self.assertContains(self.driver.current_url, "accounts/signup")
#         print("Expecting /accounts/signup", self.driver.current_url)

#         # Sign in
#         click_link(self.driver.find_element(By.ID, "sign-in-link"))
#         print(self.driver.current_url)
#         self.driver.implicitly_wait(2)
#         self.driver.find_element(By.CSS_SELECTOR, "input[name=login]").send_keys(self.gift_recipient_user.email)
#         self.driver.find_element(By.CSS_SELECTOR, "input[name=password]").send_keys(self.gift_recipient_user.plaintext_password)
#         self.driver.find_element(By.CSS_SELECTOR, "form").submit()

#         # Should navigate back to shipping
#         self.driver.implicitly_wait(2)
#         self.assertContains(self.driver.current_url, reverse('redeem_setup'))

#         # Shipping
#         print("Expectign redeem setup", self.driver.current_url)
#         self.assertContains(self.driver.current_url, reverse('redeem_setup'))
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=name]").send_keys("Test")
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=line1]").send_keys("Test")
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=line2]").send_keys("Test")
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=postal_code]").send_keys("Test")
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=city]").send_keys("Test")
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=state]").send_keys("Test")
#         self.driver.find_element(By.CSS_SELECTOR, "form input[name=country]").send_keys("US")
#         self.driver.find_element(By.CSS_SELECTOR, "form").submit()

#         # Success page
#         self.driver.implicitly_wait(4)
#         print("Expecting success", self.driver.current_url)
#         self.assertContains(self.driver.current_url, reverse('completed_gift_redemption'))


import datetime

from dateutil.relativedelta import relativedelta


def epoch_time(**kwargs):
    time = datetime.datetime.now()
    if len(kwargs.items()) > 0:
        time = time + relativedelta(**kwargs)
    return int(time.timestamp())


def advance_clock(clock_id, **kwargs):
    stripe.test_helpers.TestClock.advance(clock_id, frozen_time=epoch_time(**kwargs))
    clock_has_advanced = False
    while clock_has_advanced is False:
        time.sleep(0.5)
        clock = stripe.test_helpers.TestClock.retrieve(clock_id)
        if clock.status == "ready":
            clock_has_advanced = True
            return True, clock
        elif clock.status == "internal_failure":
            raise Exception("Failed to advance clock")


class UpgradeTestCase(TestCase):
    users = []
    passwords = {}

    def create_user(self) -> User:
        # Generate current time in seconds since epoch
        self.clock = stripe.test_helpers.TestClock.create(
            frozen_time=epoch_time(), name="Monthly billing"
        )
        id = uid()
        email = f"unit-test-{id}@leftbookclub.com"
        user = User.objects.create_user(id, email, "default_pw_12345_xyz_lbc")
        password = User.objects.make_random_password()
        user.plaintext_password = password
        user.set_password(password)
        user.save(update_fields=["password"])

        customer = stripe.Customer.create(
            email=user.email,
            test_clock=self.clock.id,
            metadata={"text_mode": "true"},
            shipping={
                "address": {
                    "city": "San Francisco",
                    "country": "US",
                    "line1": "1234 Main Street",
                    "line2": "Apt 1",
                    "postal_code": "94111",
                    "state": "CA",
                },
                "name": "Some guy",
            },
        )
        payment_card = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": "4242424242424242",
                "exp_month": 5,
                "exp_year": date.today().year + 3,
                "cvc": "424",
            },
        )
        stripe.PaymentMethod.attach(
            payment_card.id,
            customer=customer.id,
        )
        customer = stripe.Customer.modify(
            customer.id, invoice_settings=dict(default_payment_method=payment_card.id)
        )
        customer = djstripe.models.Customer.sync_from_stripe_data(customer)
        customer.subscriber = user
        customer.save()

        self.passwords[user] = password
        self.users += [user]
        return user

    @classmethod
    def setUpTestData(cls):
        # sync all products
        products = stripe.Product.list(limit=100)
        for product in products:
            djstripe.models.Product.sync_from_stripe_data(product)

        cls.home = HomePage(
            title="Left Book Club",
            slug="leftbookclub",
        )
        Page.get_first_root_node().add_child(instance=cls.home)
        cls.home.save_revision().publish()
        # Add a dummy page to avoid Treebeard add/delete issues
        another_page = InformationPage(title="Some dummy page", slug="some_dummy_page")
        cls.home.add_child(instance=another_page)
        another_page.save_revision().publish()
        cls.site, is_new = Site.objects.get_or_create(
            hostname="localhost",
            port=8000,
            is_default_site=True,
            site_name="Left Book Club",
            root_page=cls.home,
        )
        return super().setUpTestData()

    @classmethod
    def tearDownClass(cls) -> None:
        for user in cls.users:
            if user.stripe_customer is not None:
                stripe.Customer.delete(user.stripe_customer.id)
        return super().tearDownClass()

    def setUp(self) -> None:
        self.user = self.create_user()

        # Add zone
        self.zone = ShippingZone.objects.create(
            rest_of_world=True, code="ROW", nickname="ROW", rate=Money(2, "GBP")
        )

        # configure a boring plan
        self.product = (
            djstripe.models.Product.objects.filter(
                active=True, metadata__shipping__isnull=True
            )
            .order_by("?")
            .first()
        )
        #
        self.legacy_plan = MembershipPlanPage(
            title="Legacy Plan",
            deliveries_per_year=12,
            prices=[
                MembershipPlanPrice(
                    price=Money(4, "GBP"), interval="month", interval_count=1
                ),
                MembershipPlanPrice(
                    price=Money(30, "GBP"), interval="year", interval_count=1
                ),
            ],
        )
        self.home.add_child(instance=self.legacy_plan)
        self.legacy_plan.save_revision().publish()
        self.legacy_plan.monthly_price.products.set([self.product.djstripe_id])
        self.legacy_plan.monthly_price.save()
        self.legacy_plan.annual_price.products.set([self.product.djstripe_id])
        self.legacy_plan.annual_price.save()
        #
        self.plan = MembershipPlanPage(
            title="Contemporary Plan",
            deliveries_per_year=12,
            prices=[
                MembershipPlanPrice(
                    price=Money(10, "GBP"), interval="month", interval_count=1
                ),
                MembershipPlanPrice(
                    price=Money(100, "GBP"), interval="year", interval_count=1
                ),
            ],
        )
        self.home.add_child(instance=self.plan)
        self.plan.save_revision().publish()
        self.plan.monthly_price.products.set([self.product.djstripe_id])
        self.plan.monthly_price.save()
        self.plan.annual_price.products.set([self.product.djstripe_id])
        self.plan.annual_price.save()
        #

        return super().setUp()

    def tearDown(self) -> None:
        stripe.test_helpers.TestClock.delete(self.clock.id)
        ShippingZone.objects.all().delete()
        self.legacy_plan.delete()
        self.plan.delete()
        return super().tearDown()

    def test_customer_chooses_status_quo(self):
        # Set up
        stripe_context = SubscriptionCheckoutView.create_checkout_context(
            product=self.plan.monthly_price.products.first(),
            price=self.plan.monthly_price,
            zone=ShippingZone.default_zone,
        )
        args = dict(
            customer=self.user.stripe_customer.id,
            items=stripe_context["checkout_args"]["line_items"],
            metadata={"created_by_script": "true"},
        )
        subscription = stripe.Subscription.create(**args)
        djstripe.models.Subscription.sync_from_stripe_data(subscription)
        subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )

        # The user picks STATUS_QUO
        form = UpgradeForm(
            data={
                "user_id": self.user.pk,
                "fee_option": UpgradeAction.STATUS_QUO,
            }
        )
        self.assertTrue(form.is_valid())
        subscription = form.update_subscription()
        self.user.refresh_stripe_data()

        # Bust the active_subscription cache
        if "active_subscription" in self.user.__dict__:
            delattr(self.user, "active_subscription")

        # Their stripe subscription should be the same as it was before — check by invoice estimate
        updated_subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        self.assertEqual(
            len(updated_subscription_items.data), len(subscription_items.data)
        )

    def test_legacy_customer_should_upgrade(self):
        # A price was never created for this user in the past.
        # They're on some random price for a product that also has a newer, higher price.

        # Set up
        args = dict(
            customer=self.user.stripe_customer.id,
            items=[
                {
                    "price_data": {
                        # half the price
                        "unit_amount_decimal": (
                            self.legacy_plan.monthly_price.price.amount * 100
                        )
                        / 2,
                        "currency": self.legacy_plan.monthly_price.price.currency,
                        # same product
                        "product": self.legacy_plan.monthly_price.products.first().id,
                        "recurring": {
                            "interval": self.legacy_plan.monthly_price.interval,
                            "interval_count": self.legacy_plan.monthly_price.interval_count,
                        },
                        "metadata": {
                            "primary": True,
                            "wagtail_price": self.legacy_plan.monthly_price.pk,
                        },
                    },
                    "quantity": 1,
                },
                # no shipping item
            ],
            metadata={"created_by_script": "true"},
        )
        subscription = stripe.Subscription.create(**args)
        djstripe.models.Subscription.sync_from_stripe_data(subscription)

        # They're alerted to the fact they should upgrade
        self.assertTrue(self.user.active_subscription.should_upgrade)

    def test_legacy_customer_refreshes_to_new_price(self):
        # A price was never created for this user in the past
        # The user should end up with two line items, including the new price

        # Set up
        args = dict(
            customer=self.user.stripe_customer.id,
            items=[
                {
                    "price_data": {
                        # half the price
                        "unit_amount_decimal": (
                            self.plan.monthly_price.price.amount * 50
                        ),
                        "currency": self.plan.monthly_price.price.currency,
                        # same product
                        "product": self.plan.monthly_price.products.first().id,
                        "recurring": {
                            "interval": self.plan.monthly_price.interval,
                            "interval_count": self.plan.monthly_price.interval_count,
                        },
                        "metadata": {
                            "primary": True,
                            "wagtail_price": self.plan.monthly_price.pk,
                        },
                    },
                    "quantity": 1,
                },
                # no shipping item
            ],
            metadata={"created_by_script": "true"},
        )
        subscription = stripe.Subscription.create(**args)
        djstripe.models.Subscription.sync_from_stripe_data(subscription)
        subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )

        form = UpgradeForm(
            data={
                "user_id": self.user.pk,
                "fee_option": UpgradeAction.UPDATE_PRICE,
            }
        )
        self.assertTrue(form.is_valid())
        subscription = form.update_subscription()
        self.user.refresh_stripe_data()

        # Bust the active_subscription cache
        if "active_subscription" in self.user.__dict__:
            delattr(self.user, "active_subscription")

        # SI count should be 2
        updated_subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        self.assertEqual(len(updated_subscription_items.data), 2)
        self.assertGreater(
            len(updated_subscription_items.data), len(subscription_items.data)
        )
        # Including shipping
        self.assertIsNotNone(self.user.active_subscription.shipping_si)
        # And the NEW fee
        self.assertEqual(
            self.user.active_subscription.membership_si.plan.amount,
            self.plan.monthly_price.price.amount,
        )

        # No prorations
        # price is as expected
        advance_clock(self.clock.id, days=15)

        expected_line_items = (
            self.user.active_subscription.membership_plan_price.to_checkout_line_items(
                product=self.user.active_subscription.membership_si.plan.product,
                zone=self.user.active_subscription.shipping_zone,
            )
        )
        quote = stripe.Quote.create(
            customer=self.user.stripe_customer.id,
            line_items=expected_line_items,
        )
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=self.user.stripe_customer.id
        )
        self.assertEqual(quote.amount_total, upcoming_invoice.subtotal)

        # No prorations
        # price is as expected
        advance_clock(self.clock.id, days=15)
        expected_line_items = (
            self.user.active_subscription.membership_plan_price.to_checkout_line_items(
                product=self.user.active_subscription.membership_si.plan.product,
                zone=self.user.active_subscription.shipping_zone,
            )
        )
        quote = stripe.Quote.create(
            customer=self.user.stripe_customer.id,
            line_items=expected_line_items,
        )
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=self.user.stripe_customer.id
        )
        self.assertEqual(
            quote.amount_total,
            upcoming_invoice.subtotal,
            "Next invoice should be equal to the quote",
        )

    def test_customer_on_edited_price_updates_to_new_price(self):
        # A price was created
        # The user signed up with it
        # Since then, the price changed
        # The user should end up on the new price

        # Set up
        stripe_context = SubscriptionCheckoutView.create_checkout_context(
            product=self.plan.monthly_price.products.first(),
            price=self.plan.monthly_price,
            zone=ShippingZone.default_zone,
        )
        args = dict(
            customer=self.user.stripe_customer.id,
            items=stripe_context["checkout_args"]["line_items"],
            metadata={"created_by_script": "true"},
        )
        subscription = stripe.Subscription.create(**args)
        djstripe.models.Subscription.sync_from_stripe_data(subscription)
        subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        old_sis = self.user.active_subscription.named_subscription_items
        old_shipping_price = old_sis.shipping_si.plan.amount_decimal
        old_membership_price = old_sis.membership_si.plan.amount_decimal

        # Later, the prices double
        self.zone.rate = self.zone.rate * 2
        self.zone.save()
        price = self.plan.monthly_price
        price.price = self.plan.monthly_price.price * 2
        price.save()

        # Check form options
        options = UpgradeForm.get_options_for_user(self.user)
        self.assertEqual(
            len(options),
            2,
            "Should have a status quo and an update price option since the price increased",
        )
        self.assertIn(UpgradeAction.UPDATE_PRICE, options)
        self.assertIn(UpgradeAction.STATUS_QUO, options)

        # The user updates their subscription
        form = UpgradeForm(
            data={
                "user_id": self.user.pk,
                "fee_option": UpgradeAction.UPDATE_PRICE,
            }
        )
        self.assertTrue(form.is_valid())
        subscription = form.update_subscription()
        self.user.refresh_stripe_data()

        # Bust the active_subscription cache
        if "active_subscription" in self.user.__dict__:
            delattr(self.user, "active_subscription")

        ## Check actual

        updated_subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        self.assertEqual(len(updated_subscription_items.data), 2)
        self.assertEqual(
            len(updated_subscription_items.data), len(subscription_items.data)
        )

        self.assertGreater(
            self.user.active_subscription.membership_si.plan.amount_decimal,
            old_membership_price,
            "Membership price should have increased",
        )

        self.assertGreater(
            self.user.active_subscription.shipping_si.plan.amount_decimal,
            old_shipping_price,
            "Shipping price should have increased",
        )

        # No prorations
        # price is as expected
        advance_clock(self.clock.id, days=15)
        expected_line_items = (
            self.user.active_subscription.membership_plan_price.to_checkout_line_items(
                product=self.user.active_subscription.membership_si.plan.product,
                zone=self.user.active_subscription.shipping_zone,
            )
        )
        quote = stripe.Quote.create(
            customer=self.user.stripe_customer.id,
            line_items=expected_line_items,
        )
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=self.user.stripe_customer.id
        )
        self.assertEqual(
            quote.amount_total,
            upcoming_invoice.subtotal,
            "Next invoice should be equal to the quote",
        )

    # def test_customer_on_deleted_price_updates_to_new_price(self):
    #     # A price was created
    #     # The user signed up with it
    #     # Since then, the price was deleted
    #     # The user should end up on the new price

    #     # Set up
    #     stripe_context = SubscriptionCheckoutView.create_checkout_context(
    #         product=self.plan.monthly_price.products.first(),
    #         price=self.plan.monthly_price,
    #         zone=ShippingZone.default_zone,
    #     )
    #     args = dict(
    #         customer=self.user.stripe_customer.id,
    #         items=stripe_context["checkout_args"]["line_items"],
    #         metadata={"created_by_script": "true"},
    #     )
    #     subscription = stripe.Subscription.create(**args)
    #     djstripe.models.Subscription.sync_from_stripe_data(subscription)
    #     subscription_items = stripe.SubscriptionItem.list(
    #         subscription=subscription.id,
    #     )

    #     # Later, the price was deleted and a new, similar one was created
    #     old_billing_deets = self.user.get_membership_details()
    #     plan_price = self.plan.monthly_price.price
    #     self.plan.delete()
    #     new_plan = MembershipPlanPage(
    #         title="New Plan",
    #         deliveries_per_year=12,
    #         prices=[
    #             MembershipPlanPrice(
    #                 price=plan_price * 2, interval="month", interval_count=1
    #             )
    #         ],
    #     )
    #     self.home.add_child(instance=new_plan)
    #     new_plan.save()
    #     new_plan.monthly_price.products.set([self.product.djstripe_id])
    #     new_plan.monthly_price.save()

    #     # The user picks STATUS_QUO
    #     form = UpgradeForm(
    #         data={
    #             "user_id": self.user.pk,
    #             "fee_option": UpgradeAction.UPDATE_PRICE,
    #         }
    #     )
    #     form.update_subscription()

    #     # The user should end up with two line items
    #     updated_subscription_items = stripe.SubscriptionItem.list(
    #         subscription=subscription.id,
    #     )
    #     updated_sub = stripe.Subscription.retrieve(subscription.id)
    #     djstripe.models.Subscription.sync_from_stripe_data(updated_sub)
    #     self.assertEqual(len(updated_subscription_items.data), 2)
    #     self.assertEqual(
    #         len(updated_subscription_items.data), len(subscription_items.data)
    #     )

    #     # Membership price should have increased
    #     billing_deets = self.user.get_membership_details()
    #     print(billing_deets, billing_deets.subscription.id)
    #     self.assertGreater(
    #         billing_deets.membership_si.plan.amount,
    #         old_billing_deets.membership_si.plan.amount,
    #     )

    #     # New plan should be recognised as belonging to this user
    #     self.assertEqual(billing_deets.membership_plan_price, new_plan.monthly_price)

    #     # No prorations
    #     # price is as expected
    #     advance_clock(self.clock.id, days=15)
    #     expected_line_items = (
    #         billing_deets.membership_plan_price.to_checkout_line_items(
    #             product=billing_deets.membership_si.plan.product,
    #             zone=billing_deets.shipping_zone,
    #         )
    #     )
    #     quote = stripe.Quote.create(
    #         customer=self.user.stripe_customer.id,
    #         line_items=expected_line_items,
    #     )
    #     upcoming_invoice = stripe.Invoice.upcoming(
    #         customer=self.user.stripe_customer.id
    #     )
    #     self.assertEqual(quote.amount_total, upcoming_invoice.subtotal, "Next invoice should be equal to the quote")

    def test_customer_upgrades_to_solidarity_plan(self):
        # A price was created
        # The user signed up with it
        # Since then, the price was deleted
        # The user should end up on the new price

        # Set an upsell plan
        UpsellPlanSettings.objects.create(site=self.site, upsell_plan=self.plan)

        # Set up a legacy price
        stripe_context = SubscriptionCheckoutView.create_checkout_context(
            product=self.legacy_plan.monthly_price.products.first(),
            price=self.legacy_plan.monthly_price,
            zone=ShippingZone.default_zone,
        )
        args = dict(
            customer=self.user.stripe_customer.id,
            items=stripe_context["checkout_args"]["line_items"],
            metadata={"created_by_script": "true"},
        )
        subscription = stripe.Subscription.create(**args)
        djstripe.models.Subscription.sync_from_stripe_data(subscription)

        old_sis = self.user.active_subscription.named_subscription_items

        # They pick upgrade
        form = UpgradeForm(
            data={
                "user_id": self.user.pk,
                "fee_option": UpgradeAction.UPGRADE_TO_SOLIDARITY,
            }
        )
        self.assertTrue(form.is_valid())
        subscription = form.update_subscription()
        self.user.refresh_stripe_data()

        # Bust the active_subscription cache
        if "active_subscription" in self.user.__dict__:
            delattr(self.user, "active_subscription")

        self.assertEqual(
            self.user.active_subscription.membership_si.plan.amount_decimal,
            old_sis.membership_si.plan.amount_decimal,
            "Membership price should equal the new plan's price",
        )

        # No prorations
        # price is as expected
        advance_clock(self.clock.id, days=15)
        expected_line_items = (
            self.user.active_subscription.membership_plan_price.to_checkout_line_items(
                product=self.user.active_subscription.membership_si.plan.product,
                zone=self.user.active_subscription.shipping_zone,
            )
        )
        quote = stripe.Quote.create(
            customer=self.user.stripe_customer.id,
            line_items=expected_line_items,
        )
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=self.user.stripe_customer.id
        )
        self.assertEqual(
            quote.amount_total,
            upcoming_invoice.subtotal,
            "Next invoice should be equal to the quote",
        )

    def test_yearly_customer_updating_their_sub(self):
        # A price was created
        # The user signed up with it
        # Since then, the price changed
        # The user should end up on the new price

        # Set up
        stripe_context = SubscriptionCheckoutView.create_checkout_context(
            product=self.plan.annual_price.products.first(),
            price=self.plan.annual_price,
            zone=ShippingZone.default_zone,
        )
        args = dict(
            customer=self.user.stripe_customer.id,
            items=stripe_context["checkout_args"]["line_items"],
            metadata={"created_by_script": "true"},
        )
        subscription = stripe.Subscription.create(**args)
        djstripe.models.Subscription.sync_from_stripe_data(subscription)
        subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        old_sis = self.user.active_subscription.named_subscription_items
        old_shipping_price = old_sis.shipping_si.plan.amount_decimal
        old_membership_price = old_sis.membership_si.plan.amount_decimal

        # Later, the prices double
        self.zone.rate = self.zone.rate * 2
        self.zone.save()
        price = self.plan.annual_price
        price.price = self.plan.annual_price.price * 2
        price.save()

        # The user updates their subscription
        form = UpgradeForm(
            data={
                "user_id": self.user.pk,
                "fee_option": UpgradeAction.UPDATE_PRICE,
            }
        )
        self.assertTrue(form.is_valid())
        subscription = form.update_subscription()
        self.user.refresh_stripe_data()

        # Bust the active_subscription cache
        if "active_subscription" in self.user.__dict__:
            delattr(self.user, "active_subscription")

        # Check that the subscription is still annual
        self.assertEqual(
            self.user.active_subscription.membership_si.plan.interval,
            "year",
            "Membership plan should be annual",
        )

        # No prorations
        # price is as expected
        advance_clock(self.clock.id, days=300)
        expected_line_items = (
            self.user.active_subscription.membership_plan_price.to_checkout_line_items(
                product=self.user.active_subscription.membership_si.plan.product,
                zone=self.user.active_subscription.shipping_zone,
            )
        )
        quote = stripe.Quote.create(
            customer=self.user.stripe_customer.id,
            line_items=expected_line_items,
        )
        upcoming_invoice = stripe.Invoice.upcoming(
            customer=self.user.stripe_customer.id
        )
        self.assertEqual(
            quote.amount_total,
            upcoming_invoice.subtotal,
            "Next invoice should be equal to the quote",
        )

    def test_add_donation(self):
        # A price was created
        # The user signed up with it
        # Since then, the price was deleted
        # The user should end up on the new price

        # Set up a legacy price
        stripe_context = SubscriptionCheckoutView.create_checkout_context(
            product=self.legacy_plan.monthly_price.products.first(),
            price=self.legacy_plan.monthly_price,
            zone=ShippingZone.default_zone,
        )
        args = dict(
            customer=self.user.stripe_customer.id,
            items=stripe_context["checkout_args"]["line_items"],
            metadata={"created_by_script": "true"},
        )
        sub = stripe.Subscription.create(**args)
        subscription: LBCSubscription = (
            djstripe.models.Subscription.sync_from_stripe_data(sub).lbc()
        )

        # Add a donation
        donation_pounds = 450
        subscription.upsert_regular_donation(donation_pounds)
        self.user.refresh_stripe_data()

        # Bust the active_subscription cache
        if "active_subscription" in self.user.__dict__:
            delattr(self.user, "active_subscription")

        self.assertIsNotNone(
            self.user.active_subscription.donation_si, "Sub should have a donation"
        )
        self.assertEqual(
            self.user.active_subscription.items.count(),
            3,
            "Sub should have deduped membership, shipping and donation product lines",
        )
        next_fee_big = self.user.active_subscription.next_fee
        self.assertGreaterEqual(
            next_fee_big,
            donation_pounds,
            "Sub should have a biiiig donation value",
        )

        # Test tweaking the donation
        subscription.upsert_regular_donation(1)
        self.user.refresh_stripe_data()
        delattr(self.user.active_subscription, "next_fee")
        delattr(self.user, "active_subscription")

        updated_subscription_items = stripe.SubscriptionItem.list(
            subscription=subscription.id,
        )
        self.assertEqual(
            len(updated_subscription_items.data),
            3,
            "Sub should have deduped membership, shipping and donation product lines",
        )
        next_fee_small = self.user.active_subscription.next_fee
        self.assertLessEqual(
            next_fee_small,
            next_fee_big,
            "Upserting a donation should replace the donation SI",
        )
