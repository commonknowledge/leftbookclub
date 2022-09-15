from django import template

register = template.Library()
from random import choice

light_backgrounds = [
    "tw-bg-lightgreen",
    "tw-bg-pink",
    "tw-bg-lilacgrey",
    "tw-bg-coral",
    "tw-bg-magenta",
    "tw-bg-purple",
]


dark_backgrounds = [
    "tw-bg-darkgreen",
    "tw-bg-yellow",
    "tw-bg-teal",
]

backgrounds = light_backgrounds + dark_backgrounds


def get_color_set(variant=None):
    if variant == "light":
        return light_backgrounds
    if variant == "dark":
        return dark_backgrounds
    return backgrounds


@register.simple_tag
def random_brand_background(variant=None):
    return choice(get_color_set(variant))


@register.simple_tag
def brand_background_by_index(index, variant=None):
    color_set = get_color_set(variant)
    return color_set[(index % len(color_set)) - 1]


@register.simple_tag
def brand_backgrounds(variant=None):
    return get_color_set(variant)


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
