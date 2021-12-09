import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views.generic import TemplateView

map = {
    "layer": {
        "id": "terrain-data",
        "type": "line",
        "source": "mapbox-terrain",
        "source-layer": "contour",
        "layout": {"line-join": "round", "line-cap": "round"},
        "paint": {"line-color": "#ff69b4", "line-width": 1},
    },
    "data": {
        "type": "vector",
        "url": "mapbox://mapbox.mapbox-terrain-v2",
    },
}


urlpatterns = [
    path("admin/", admin.site.urls),
    path("__debug__/", include(debug_toolbar.urls)),
    path("", TemplateView.as_view(template_name="pages/index.html", extra_context=map)),
]


if settings.DEBUG:
    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
