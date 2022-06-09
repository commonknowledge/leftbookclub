def flatten_list(the_list):
    """
    Takes a 2D list and returns a 1D list
    """
    return [item for sublist in the_list for item in sublist]


def ensure_list(list_or_item):
    if isinstance(list_or_item, list):
        return list_or_item
    return [list_or_item]


from collections.abc import MutableMapping


def value_at_path(obj, path):
    *parts, last = path.split(".")

    for part in parts:
        if isinstance(obj, MutableMapping):
            obj = obj[part]
        else:
            obj = obj[int(part)]

    if isinstance(obj, MutableMapping):
        return obj[last]
    else:
        return obj[int(last)]


def include_keys(dictionary, keys):
    """Filters a dict by only including certain keys."""
    key_set = set(keys) & set(dictionary.keys())
    return {key: dictionary[key] for key in key_set}
