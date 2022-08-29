import os

import requests
from django.contrib.gis.geos import Point
from django.core.cache import cache

from app.utils.python import batch_and_aggregate, get, get_path


def normalise_postcode(postcode):
    return postcode.upper().strip().replace(" ", "")


def cache_key(postcode):
    normalised = normalise_postcode(postcode)
    return f"postcodes.io-{normalised}"


def point_from_postcode_result(postcode_result):
    return Point(postcode_result["longitude"], postcode_result["latitude"])


def postcode_geo(postcode: str):
    postcode = normalise_postcode(postcode)

    cached_data = cache.get(cache_key(postcode))
    if cached_data is not None:
        return cached_data

    response = requests.get(f"https://api.postcodes.io/postcodes/{postcode}")
    data = response.json()
    status = get(data, "status")
    result = get(data, "result")
    cache.set(cache_key(postcode), result, 60 * 60 if result is None else 9999999)

    if status != 200 or result is None:
        # raise Exception(f'Failed to geocode postcode: {postcode}.')
        return None

    return result


@batch_and_aggregate(100)
def bulk_postcode_geo(postcodes):
    postcodes = [normalise_postcode(postcode) for postcode in postcodes]
    cached_data = cache.get_many(cache_key(postcode) for postcode in postcodes)
    has_loaded = [
        {"query": postcode, "result": cached_data.get(postcode)}
        for postcode in postcodes
        if cached_data.get(postcode) is not None
    ]

    needs_loading = [
        postcode for postcode in postcodes if cached_data.get(postcode) is None
    ]
    # print('needs_loading')
    # print(needs_loading)

    if len(needs_loading) == 1:
        postcode = needs_loading[0]
        has_loaded += [{"query": postcode, "result": postcode_geo(postcode)}]

    elif len(needs_loading) > 0:
        response = requests.post(
            f"https://api.postcodes.io/postcodes", data={"postcodes": needs_loading}
        )

        data = response.json()
        new_data = get(data, "result")
        status = get(data, "status")

        if status != 200 or new_data is None:
            # raise Exception(f'Failed to bulk geocode postcodes: {postcodes}.')
            pass
        else:
            has_loaded += new_data
            cache.set_many(
                {cache_key(res.get("query")): res.get("result") for res in new_data}
            )

    return has_loaded


@batch_and_aggregate(25)
def bulk_coordinate_geo(coordinates):
    for i, coords in enumerate(coordinates):
        coordinates[i]["limit"] = 1

    payload = {"geolocations": coordinates}

    response = requests.post(f"https://api.postcodes.io/postcodes", data=payload)
    data = response.json()
    status = get(data, "status")
    result = get(data, "result")

    if status != 200 or result is None:
        raise Exception(f"Failed to bulk geocode coordinates: {payload}")

    return result


def coordinates_geo(latitude: float, longitude: float):
    response = requests.get(
        f"https://api.postcodes.io/postcodes?lon={longitude}&lat={latitude}"
    )
    data = response.json()
    status = get(data, "status")
    result = get(data, "result")

    if status != 200 or result is None or len(result) < 1:
        raise Exception(
            f"Failed to get postcode for coordinates: lon={longitude}&lat={latitude}."
        )

    return result[0]


def constituency_id_from_geo(geo):
    return get_path(geo, "codes", "parliamentary_constituency")


def constituency_id_by_postcode(postcode: str) -> str:
    geo = postcode_geo(postcode)
    return constituency_id_from_geo(geo)


class TransportModes:
    driving = "driving"
    walking = "walking"
    bicycling = "bicycling"
    transit = "transit"


def get_approximate_postcode_locations(postcodes):
    """
    Increase frequency of distance matrix cache hits by lowering precision of locations
    """

    def approximate_location(coordinate):
        # 0.01 degrees distance on both long and lat == about a 20 minute walk in the uk
        return {
            "latitude": round(get_path(coordinate, "result", "latitude"), 2),
            "longitude": round(get_path(coordinate, "result", "longitude"), 2),
        }

    return map(approximate_location, bulk_postcode_geo(postcodes))


def postcode_components(g):
    return [t for t in g.get("address_components") if "postal_code" in t.get("types")]


def geo_by_address(address: str):
    params = {
        "key": os.getenv("GOOGLE_MAPS_API_KEY"),
        "components": "country:" + os.getenv("CCTLD"),
        "address": address,
    }
    res = requests.get(
        f"https://maps.googleapis.com/maps/api/geocode/json?", params=params
    )
    data = res.json()
    postcoded_geos = [g for g in data.get("results") if len(postcode_components(g))]
    if len(postcoded_geos) == 0:
        return {}
    geo = postcoded_geos[0]
    return {
        "address": geo.get("formatted_address"),
        "postcode": postcode_components(geo)[0].get("short_name"),
        "latitude": float(geo.get("geometry").get("location").get("lat")),
        "longitude": float(geo.get("geometry").get("location").get("lng")),
    }


"""
output {
    "status" : "OK",
    "destination_addresses" : [ "New York, NY, USA" ],
    "origin_addresses" : [ "Washington, DC, USA" ],
    "rows" : [
        {
            "elements" : [
                {
                    "distance" : {
                        "text" : "225 mi",
                        "value" : 361715
                    },
                    "duration" : {
                        "text" : "3 hours 49 mins",
                        "value" : 13725
                    },
                    "status" : "OK"
                }
            ]
        }
    ]
}
"""
