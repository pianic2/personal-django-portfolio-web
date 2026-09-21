from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.api.v3.urls import api as wagtail_api
from wagtail.documents import urls as wagtaildocs_urls

from .contact import ContactView
from .localization_api import router as localized_pairs_router

wagtail_api.add_router("/localized-pairs/", localized_pairs_router)

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("api/v3/", wagtail_api.urls),
    path("api/contact/", ContactView.as_view(), name="contact"),
]

urlpatterns += [path("", include(wagtail_urls))]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
