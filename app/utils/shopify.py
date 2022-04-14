import json

from dateutil.parser import parse


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
