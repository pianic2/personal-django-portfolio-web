from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.api.v3.urls import api as wagtail_api
from wagtail.documents import urls as wagtaildocs_urls

from .contact import ContactView


def production_root(request):
    return HttpResponseNotFound()

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("api/v3/", wagtail_api.urls),
    path("api/contact/", ContactView.as_view(), name="contact"),
    path("", include(wagtail_urls)),
]

if not settings.DEBUG:
    urlpatterns.insert(5, path("", production_root))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
