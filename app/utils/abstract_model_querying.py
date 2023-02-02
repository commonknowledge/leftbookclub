from django.apps import apps
from django.db.models import Q, Subquery

#####
# The below is taken from:
# https://www.oak-tree.tech/blog/snippet-abstract-model-query
# Read that article for a full explainer of the slightly ambiguous code below.
#####


def model_subclasses(mclass):
    """Retrieve all model subclasses for the provided class"""
    return [m for m in apps.get_models() if issubclass(m, mclass)]


def abstract_page_query_filter(mclass, filter_params, pk_attr="page_ptr"):
    """
    Create a filter query that will be applied to all children of the provided
    abstract model class. Returns None if a query filter cannot be created.
    @returns Query or None
    """
    if not mclass._meta.abstract:
        raise ValueError("Provided model class must be abstract")

    # First, you use the Django apps registry to locate and retrieve all concrete model classes which are children of the abstract class. This is implemented in model_subclasses.
    pclasses = model_subclasses(mclass)

    # Filter for pages which are marked as features
    if len(pclasses):
        # After the model class reference has been retrieved, create a subquery that retrieves the primary keys of pages that match the condition. Because this is constructed as a subquery and uses the values method, the entire statement will execute in a single database query.
        qf = Q(
            pk__in=Subquery(pclasses[0].objects.filter(**filter_params).values(pk_attr))
        )
        # Execute the query filter created in abstract_page_query_filter as part of a larger query using the parent model, Page.
        for c in pclasses[1:]:
            qf |= Q(pk__in=Subquery(c.objects.filter(**filter_params).values(pk_attr)))

        return qf

    return None
