import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from wagtail.core import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls


urlpatterns = [
    path("django/", admin.site.urls),
    path('admin/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path("__debug__/", include(debug_toolbar.urls)),
    # For anything not caught by a more specific rule above, hand over to Wagtail's serving mechanism
    re_path(r'', include(wagtail_urls)),
]


if settings.DEBUG:
    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
