from django import template

register = template.Library()
from random import choice

backgrounds = [
    "tw-bg-coral",
    "tw-bg-lightgreen",
    "tw-bg-magenta",
    "tw-bg-pink",
    "tw-bg-darkgreen",
    "tw-bg-yellow",
    "tw-bg-purple",
    "tw-bg-lilacgrey",
    "tw-bg-teal",
]


@register.simple_tag
def random_brand_background():
    return choice(backgrounds)


@register.simple_tag
def brand_background_by_index(index):
    return backgrounds[index]


@register.simple_tag
def brand_backgrounds():
    return backgrounds


###


@register.inclusion_tag("groundwork/geo/components/map_config.html")
def adjusted_map_source(id, data):
    ref = "map_source_config" + "-" + id

    return {
        "controller": "map-source",
        "values": {"id": id, "data": "#" + ref},
        "json": {ref: data},
    }


@register.inclusion_tag("groundwork/geo/components/map_config.html")
def adjusted_map_layer(id, layer):
    ref = "map_layer_config" + "-" + id

    return {
        "controller": "map-layer",
        "values": {"layer": "#" + ref},
        "json": {ref: layer},
    }


@register.filter
def replace(value, arg):
    """
    Replacing filter
    Use `{{ "aaa"|replace:"a|b" }}`
    """
    if len(arg.split("|")) != 2:
        return value

    what, to = arg.split("|")
    return value.replace(what, to)
