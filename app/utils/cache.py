from django.core.cache import cache
from django.db.models import QuerySet


def django_cached_key(ns, get_key, *args, **kwargs):
    key = ns
    if get_key != None:
        key += "." + str(get_key(*args, **kwargs))
    return key


def django_cached(ns, get_key=None, ttl=500):
    def decorator(fn):
        def cached_fn(*args, **kwargs):
            key = django_cached_key(ns, get_key, *args, **kwargs)

            hit = cache.get(key)
            if hit is None:
                hit = fn(*args, **kwargs)
                if isinstance(hit, QuerySet):
                    # Caching a QuerySet does _not_ do what you might think it does!
                    hit = tuple(hit)
                cache.set(key, hit, ttl)

            return hit

        return cached_fn

    return decorator


def django_cached_model(ns, ttl=500):
    return django_cached(ns, lambda self: self.id, ttl)


def cached_fn(key, timeout_seconds=60 * 5, cache_type="default"):
    def decorator(original_fn):
        def resulting_fn(*args, **kwargs):
            cache_key = key(*args, **kwargs) if callable(key) else key

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            try:
                result = original_fn(*args, **kwargs)
                cache.set(cache_key, result, timeout_seconds)
                return result
            except:
                pass

        return resulting_fn

    return
