from typing import List, Union

from app.utils import ensure_list


def get_current_book(book_types: Union[None, str, List[str]]):
    from app.models.wagtail import BookPage

    if book_types is not None:
        book_types = ensure_list(book_types)

        if len(book_types) > 0 and "all-books" not in book_types:
            return (
                BookPage.objects.filter(type__in=book_types)
                .order_by("-published_date")
                .first()
            )
    return BookPage.objects.order_by("-published_date").first()
