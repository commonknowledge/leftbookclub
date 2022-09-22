from django.core.management.base import BaseCommand
from django.db import transaction

from app.utils.geo import (
    bulk_postcode_geo,
    normalise_postcode,
    point_from_postcode_result,
)


class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        from app.models.django import User

        # Bulk get / set postcodes
        users_with_postcodes = (
            User.objects.filter(coordinates__isnull=True)
            .exclude(postcode="")
            .exclude(postcode=None)
        )
        # print("Getting postcode data for", users_with_postcodes.count(), users_with_postcodes)
        postcode_data = bulk_postcode_geo(
            [
                u.postcode
                for u in users_with_postcodes
                if u.postcode is not None and u.postcode != ""
            ]
        )
        # print("Coord data", postcode_data)
        for postcode_payload in postcode_data:
            # print("Searching", postcode_payload['query'])
            for user in users_with_postcodes:
                result = postcode_payload.get("result", None)
                # print("Against user", user.postcode)
                if (
                    normalise_postcode(user.postcode)
                    == normalise_postcode(postcode_payload["query"])
                    and result is not None
                ):
                    # print("--> MATCH", user, postcode_payload)
                    point = point_from_postcode_result(result)
                    user.coordinates = point
                    user.save()
