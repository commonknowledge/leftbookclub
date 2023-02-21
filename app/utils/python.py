from datetime import datetime


def is_sequence(arg):
    if isinstance(arg, str):
        return False
    return (
        not hasattr(arg, "strip")
        and hasattr(arg, "__getitem__")
        or hasattr(arg, "__iter__")
    )


def ensure_list(possible):
    if is_sequence(possible):
        return possible
    elif possible:
        return [possible]
    else:
        return []


def get(d, key, default=None):
    keys = ensure_list(key)
    val = None
    try:
        for key in keys:
            val = d.get(key)
            if val is not None:
                break
    except:
        pass
    try:
        if val is None:
            for key in keys:
                val = getattr(d, key)
                if val is not None:
                    break
    except:
        pass
    try:
        if val is None:
            for key in keys:
                val = getattr(ensureObj(d), key)
                if val is not None:
                    break
    except:
        pass

    return val if val is not None else default


def get_path(d, *keys):
    for k in keys:
        d = get(d, k)
    return d


def chunk_array(arr, max_size):
    for i in range(0, len(arr), max_size):
        yield arr[i : i + max_size]


def batch_and_aggregate(arr_limit):
    def decorator(original_fn):
        def resulting_fn(arr):
            batches = chunk_array(arr, arr_limit)
            results = []
            for batch in batches:
                results += original_fn(batch)
            return results

        return resulting_fn

    return decorator


import random
import string


def uid():
    return "".join(random.choice(string.ascii_lowercase) for i in range(10))


def diff_month(d1: datetime, d2: datetime):
    return (d1.year - d2.year) * 12 + d1.month - d2.month
