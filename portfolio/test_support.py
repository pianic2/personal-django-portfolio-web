from wagtail.models import Locale, Site


def ensure_localized_site_roots() -> None:
    site = Site.objects.get(is_default_site=True)
    italian_locale = Locale.objects.get_or_create(language_code="it")[0]
    english_locale = Locale.objects.get_or_create(language_code="en")[0]
    root = site.root_page
    if root.locale_id != italian_locale.id:
        italian_root = (
            root.get_translation(italian_locale)
            if root.has_translation(italian_locale)
            else root.copy_for_translation(locale=italian_locale, copy_parents=True)
        )
        site.root_page = italian_root
        site.save(update_fields=["root_page"])
        root = italian_root
    if not root.has_translation(english_locale):
        root.copy_for_translation(locale=english_locale, copy_parents=True)
