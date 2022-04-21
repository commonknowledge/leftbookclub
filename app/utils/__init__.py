def flatten_list(the_list):
    """
    Takes a 2D list and returns a 1D list
    """
    return [item for sublist in the_list for item in sublist]


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
