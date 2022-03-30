import djstripe.models


class LBCProduct(djstripe.models.Product):
    @classmethod
    def get_active_plans(self):
        return self.objects.filter(metadata__pickable="1", active=True, type="service")

    @property
    def has_tiered_pricing(self):
        return self.prices.filter(nickname__isnull=False).exists()

    @property
    def regular_price(self):
        try:
            price = self.prices.get(nickname="regular")
            return price
        except:
            return self.prices.order_by("unit_amount").first()

    @property
    def solidarity_price(self):
        try:
            price = self.prices.get(nickname="solidarity")
            return price
        except:
            return self.prices.order_by("-unit_amount").first()

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return getattr(self, self.autocomplete_search_field)

    class Meta:
        proxy = True
