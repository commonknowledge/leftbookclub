from django.urls import re_path

from ..views import WebhookView

urlpatterns = [
    re_path(r"webhook/", WebhookView.as_view(), name="webhook"),
]
