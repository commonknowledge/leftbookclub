from django import template

register = template.Library()
from random import choice

backgrounds = [
    "tw-bg-yellow",
    "tw-bg-purple",
    "tw-bg-magenta",
    "tw-bg-pink",
    "tw-bg-lightgreen",
    "tw-bg-darkgreen",
    "tw-bg-lilacgrey",
    "tw-bg-teal",
    "tw-bg-coral",
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
