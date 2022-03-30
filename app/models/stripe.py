from djstripe.models import Product


class LBCProduct(Product):
    @classmethod
    def get_active_plans(self):
        return self.objects.filter(metadata__pickable="1")

    @property
    def has_tiered_pricing(self):
        return self.prices.filter(nickname__isnull=False).exists()

    @property
    def regular_price(self):
        price = self.prices.filter(nickname="regular").first()
        if price is not None:
            return price
        return self.prices.order_by("unit_amount").first()

    @property
    def solidarity_price(self):
        price = self.prices.filter(nickname="solidarity").first()
        if price is not None:
            return price
        return self.prices.order_by("-unit_amount").first()

    class Meta:
        proxy = True
