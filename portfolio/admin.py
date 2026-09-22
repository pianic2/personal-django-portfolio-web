"""Django admin owns standalone portfolio reference data only.

Portfolio pages and their inline children remain editable exclusively in Wagtail.
"""

from django.conf import settings
from django.contrib import admin

from .models import Capability, CapabilityTranslation

admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_INDEX_TITLE


class CapabilityTranslationInline(admin.TabularInline):
    model = CapabilityTranslation
    extra = 0


@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ("stable_id", "category")
    list_filter = ("category",)
    search_fields = ("stable_id", "translations__label", "translations__description")
    inlines = (CapabilityTranslationInline,)
