from django.db.models import Q
from django.http import HttpRequest
from wagtail.api.v3 import querysets as wagtail_querysets
from wagtail.models import Page, Site


def get_pages_queryset(request: HttpRequest, model=Page):
    """Keep public API pages hidden when any ancestor is still a draft."""
    queryset = wagtail_querysets.get_pages_queryset(request, model)
    if request.user.is_authenticated:
        return queryset

    site_root_paths = set()
    for site in Site.objects.select_related("root_page"):
        site_root_paths.add(site.root_page.path)
        site_root_paths.update(site.root_page.get_translations().values_list("path", flat=True))
    draft_paths = Page.objects.filter(live=False).exclude(
        path__in=site_root_paths
    ).values_list("path", flat=True)
    for path in draft_paths:
        queryset = queryset.exclude(Q(path__startswith=path))
    return queryset
