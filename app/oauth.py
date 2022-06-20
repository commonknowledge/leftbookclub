from django.db import models
from oauth2_provider.models import AbstractApplication
from oauth2_provider.oauth2_validators import OAuth2Validator

# class CustomOAuth2Application(AbstractApplication):
#     # logo = models.ImageField()
#     # agree = models.BooleanField()
#     pass


class CustomOAuth2Validator(OAuth2Validator):
    oidc_claim_scope = None
    # Set `oidc_claim_scope = None` to ignore scopes that limit which claims to return,
    # otherwise the OIDC standard scopes are used.

    def get_additional_claims(self, request):
        args = {
            "id": request.user.id,
            "_id": request.user.id,
            "given_name": request.user.first_name,
            "first_name": request.user.first_name,
            "family_name": request.user.last_name,
            "last_name": request.user.last_name,
            "name": request.user.display_name,
            "email": request.user.email,
            "is_member": request.user.is_member,
            "is_expired_member": request.user.is_expired_member,
            "stripe_customer_id": request.user.stripe_customer.id,
            "shipping_address": request.user.shipping_address,
        }
        if request.user.primary_product != None:
            args.update({
                "stripe_product_name": request.user.primary_product.name,
                "stripe_product_id": request.user.primary_product.id,
            })
        return args
