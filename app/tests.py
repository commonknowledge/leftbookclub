from django.test import TestCase
from djmoney.money import Money
from djstripe.enums import ProductType

from app.models import *


class CacheTestCase(TestCase):
    def setUp(self):
        ShippingZone.objects.all().delete()

    # No zone, ROW should include all acceptable countries
    # and all codes are cool with stripe
    def countries_are_acceptable_to_stripe(self):
        self.assertSetEqual(
            set(ShippingZone.stripe_allowed_countries),
            set(ShippingZone.default_zone.country_codes),
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
        zone = ShippingZone(
            nickname="Test", code="UK", countries=["GB"], rate=Money(3, "GBP")
        )
        expensive_zone = ShippingZone(
            nickname="Test", code="EU", countries=["FR"], rate=Money(10, "GBP")
        )
        solidarity_plan = MembershipPlanPage(
            title="Solidarity",
            deliveries_per_year=12,
            products=[
                LBCProduct(
                    id="prod_fake", name="Some Product", type=ProductType.service
                )
            ],
            prices=[
                MembershipPlanPrice(
                    price=Money(10, "GBP"),
                    interval="month",
                    interval_count=1,
                ),
                MembershipPlanPrice(
                    price=Money(100, "GBP"),
                    interval="year",
                    interval_count=1,
                    free_shipping_zones=[zone],
                ),
            ],
        )

        # First, assert that shipping is calculated properly when `free_shipping_zones` is set
        self.assertGreater(
            solidarity_plan.annual_price.shipping_fee(expensive_zone),
            Money(0, expensive_zone.rate_currency),
        )
        line_items = solidarity_plan.annual_price.to_checkout_line_items(
            solidarity_plan.products.first(), expensive_zone
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
        line_items = solidarity_plan.annual_price.to_checkout_line_items(
            solidarity_plan.products.first(), zone
        )
        for item in line_items:
            if "shipping" in item["price_data"]["metadata"].keys():
                self.assertEqual(item["price_data"]["unit_amount_decimal"], 0)
