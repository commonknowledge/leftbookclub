def flatten_list(the_list):
    """
    Takes a 2D list and returns a 1D list
    """
    return [item for sublist in the_list for item in sublist]


def include_keys(dictionary, keys):
    """Filters a dict by only including certain keys."""
    key_set = set(keys) & set(dictionary.keys())
    return {key: dictionary[key] for key in key_set}
