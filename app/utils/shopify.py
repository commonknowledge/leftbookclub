import json

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
