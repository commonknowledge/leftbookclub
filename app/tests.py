from django.test import TestCase

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
