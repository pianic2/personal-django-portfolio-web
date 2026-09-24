"""Import the backend-owned canonical bilingual portfolio subset into Wagtail."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale, Site

from portfolio.canonical_data import CANONICAL
from portfolio.models import (
    BlogIndexPage,
    Capability,
    CapabilityTranslation,
    ClaimEvidence,
    ProfilePage,
    ProfileSection,
    ProfileUsefulLink,
    ProjectCapability,
    ProjectClaim,
    ProjectEvidence,
    ProjectLink,
    ProjectPage,
    validate_portfolio_integrity,
)

LOCALES = ("it", "en")
SHARED = CANONICAL["shared"]
LOCALIZED = CANONICAL["locales"]
CAPABILITY_LABELS = {
    "it": {
        "embedded-firmware": "Sensori ESP32-C3",
        "privacy-aware-design": "Progettazione attenta alla privacy",
        "technical-governance": "Governance tecnica",
        "laravel-api": "API REST Laravel",
        "sanctum-authentication": "Autenticazione Sanctum",
        "containerized-delivery": "Docker e MySQL",
        "node-api": "Node.js ed Express",
        "sqlite-persistence": "Persistenza SQLite",
        "automated-testing": "Test automatici",
        "python-ai": "Python e AI",
        "multi-agent-systems": "Sistemi multi-agente",
        "financial-data-analysis": "Analisi di dati finanziari",
    },
    "en": {
        "embedded-firmware": "ESP32-C3 sensors",
        "privacy-aware-design": "Privacy-aware design",
        "technical-governance": "Technical governance",
        "laravel-api": "Laravel REST API",
        "sanctum-authentication": "Sanctum authentication",
        "containerized-delivery": "Docker and MySQL",
        "node-api": "Node.js and Express",
        "sqlite-persistence": "SQLite persistence",
        "automated-testing": "Automated tests",
        "python-ai": "Python and AI",
        "multi-agent-systems": "Multi-agent systems",
        "financial-data-analysis": "Financial data analysis",
    },
}


def _upsert_child(model, parent, stable_id, defaults, *, relation_field="page"):
    obj, _ = model.objects.get_or_create(
        **{relation_field: parent, "stable_id": stable_id}, defaults=defaults
    )
    for key, value in defaults.items():
        setattr(obj, key, value)
    obj.save()
    return obj


class Command(BaseCommand):
    help = "Import the canonical bilingual portfolio MVP snapshot into Wagtail."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json", action="store_true", dest="as_json", help="Emit a machine-readable report"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        site = Site.objects.get(is_default_site=True)
        locales = {code: Locale.objects.get_or_create(language_code=code)[0] for code in LOCALES}
        report = {
            "locales": list(LOCALES),
            "profile": 0,
            "projects": 0,
            "project_variants": 0,
            "capabilities": 0,
            "capability_translations": 0,
            "claims": 0,
            "evidence": 0,
            "links": 0,
        }

        localized_roots = _ensure_localized_site_roots(site, locales)
        root = localized_roots["it"]
        _sync_blog_index(localized_roots, locales)

        for capability in SHARED["capabilities"]:
            obj, _ = Capability.objects.update_or_create(
                stable_id=capability["id"], defaults={"category": capability["category"]}
            )
            report["capabilities"] += 1
            for code in LOCALES:
                CapabilityTranslation.objects.update_or_create(
                    capability=obj,
                    locale=locales[code],
                    defaults={
                        "label": CAPABILITY_LABELS[code][capability["id"]],
                        "description": "",
                    },
                )
                report["capability_translations"] += 1

        for code in LOCALES:
            data = LOCALIZED[code]["profilePage"]
            profile = ProfilePage.objects.filter(locale=locales[code], stable_id="profile").first()
            if profile is None:
                if code == "it":
                    profile = root.add_child(
                        instance=ProfilePage(
                            title=data["hero"]["title"],
                            slug="profilo",
                            stable_id="profile",
                            hero_eyebrow=data["hero"]["eyebrow"],
                            hero_description=data["hero"]["description"],
                            highlights_label=data["highlightsLabel"],
                            closing_title=data["closing"]["title"],
                            closing_description=data["closing"]["description"],
                        )
                    )
                else:
                    profile = ProfilePage.objects.get(
                        locale=locales["it"], stable_id="profile"
                    ).copy_for_translation(locale=locales["en"], copy_parents=True)
            ProfilePage.objects.filter(pk=profile.pk).update(
                title=data["hero"]["title"],
                slug="profilo" if code == "it" else "profile",
                stable_id="profile",
                hero_eyebrow=data["hero"]["eyebrow"],
                hero_description=data["hero"]["description"],
                highlights_label=data["highlightsLabel"],
                closing_title=data["closing"]["title"],
                closing_description=data["closing"]["description"],
            )
            profile.refresh_from_db()
            _sync_profile_children(profile, data)
            profile.save_revision().publish()
            report["profile"] += 1

        for core in SHARED["projects"]:
            for code in LOCALES:
                localized = next(
                    item
                    for item in LOCALIZED[code]["projects"]
                    if item["projectId"] == core["id"]
                )
                project = ProjectPage.objects.filter(
                    locale=locales[code], stable_id=core["id"]
                ).first()
                values = {
                    "title": localized["title"],
                    "slug": localized["slug"],
                    "stable_id": localized["projectId"],
                    "eyebrow": localized["eyebrow"],
                    "detail_eyebrow": localized["detailEyebrow"],
                    "cta_label": localized["ctaLabel"],
                    "question": localized["question"],
                    "supporting_text": localized["supportingText"],
                    "what_i_worked_on": localized["whatIWorkedOn"],
                    "future_improvement": localized["futureImprovement"],
                    "origin_description": localized.get("originDescription", ""),
                    "origin": core["origin"],
                    "visual_variant": core["visualVariant"],
                    "featured": core["featured"],
                    "display_order": core["order"],
                    "narrative": localized["narrative"],
                    "metadata": localized["metadata"],
                }
                if project is None:
                    if code == "it":
                        project = root.add_child(instance=ProjectPage(**values))
                    else:
                        project = ProjectPage.objects.get(
                            locale=locales["it"], stable_id=core["id"]
                        ).copy_for_translation(locale=locales["en"], copy_parents=True)
                ProjectPage.objects.filter(pk=project.pk).update(**values)
                project.refresh_from_db()
                _sync_project_children(project, core, localized)
                project.save_revision().publish()
                report["project_variants"] += 1
            report["projects"] += 1

        report["claims"] = ProjectClaim.objects.count()
        report["evidence"] = ProjectEvidence.objects.count()
        report["links"] = ProjectLink.objects.count()
        validate_portfolio_integrity()
        report["profile_identifiers"] = list(
            {
                "stable_id": item["stable_id"],
                "locale": item["locale__language_code"],
                "slug": item["slug"],
            }
            for item in ProfilePage.objects.order_by(
                "stable_id", "locale__language_code", "slug"
            ).values("stable_id", "locale__language_code", "slug")
        )
        report["project_identifiers"] = list(
            {
                "stable_id": item["stable_id"],
                "locale": item["locale__language_code"],
                "slug": item["slug"],
            }
            for item in ProjectPage.objects.order_by(
                "stable_id", "locale__language_code", "slug"
            ).values("stable_id", "locale__language_code", "slug")
        )
        output = json.dumps(report, ensure_ascii=False, sort_keys=True)
        self.stdout.write(output if options["as_json"] else "Imported " + output)


def _ensure_localized_site_roots(site, locales):
    """Ensure the canonical site root has both locale translations."""

    root = site.root_page
    italian_locale = locales["it"]
    if root.locale_id != italian_locale.id:
        root = (
            root.get_translation(italian_locale)
            if root.has_translation(italian_locale)
            else root.copy_for_translation(locale=italian_locale, copy_parents=True)
        )
        if site.root_page_id != root.pk:
            site.root_page = root
            site.save(update_fields=["root_page"])
            Site.clear_site_root_paths_cache()

    localized_roots = {}
    for code in LOCALES:
        locale = locales[code]
        if root.locale_id == locale.id:
            localized_roots[code] = root
        elif root.has_translation(locale):
            localized_roots[code] = root.get_translation(locale)
        else:
            localized_roots[code] = root.copy_for_translation(
                locale=locale, copy_parents=True
            )
    return localized_roots


def _sync_blog_index(localized_roots, locales):
    """Reconcile the canonical bilingual BlogIndex container."""

    variants = {}
    for code in LOCALES:
        parent = localized_roots[code]
        matches = list(
            BlogIndexPage.objects.filter(locale=locales[code], stable_id="blog").order_by("pk")
        )
        page = next(
            (candidate for candidate in matches if candidate.get_parent().pk == parent.pk),
            matches[0] if matches else None,
        )
        for duplicate in matches:
            if duplicate.pk != getattr(page, "pk", None):
                duplicate.delete()
        if page is None:
            if code == "it":
                page = parent.add_child(
                    instance=BlogIndexPage(
                        locale=locales[code], title="Blog", slug="blog", stable_id="blog"
                    )
                )
            else:
                page = BlogIndexPage.objects.get(
                    locale=locales["it"], stable_id="blog"
                ).copy_for_translation(locale=locales[code], copy_parents=True)
        BlogIndexPage.objects.filter(pk=page.pk).update(
            title="Blog",
            slug="blog-it" if code == "it" else "blog-en",
            stable_id="blog",
            locale=locales[code],
        )
        page.refresh_from_db()
        if page.get_parent().pk != parent.pk:
            page.move(parent, pos="last-child")
        variants[code] = page

    if variants["en"].translation_key != variants["it"].translation_key:
        BlogIndexPage.objects.filter(pk=variants["en"].pk).update(
            translation_key=variants["it"].translation_key
        )
        variants["en"].refresh_from_db()
    for page in variants.values():
        page.save_revision().publish()


def _sync_profile_children(profile, data):
    sections = data["sections"]
    wanted = set()
    for order, section in enumerate(sections):
        wanted.add(section["id"])
        _upsert_child(
            ProfileSection,
            profile,
            section["id"],
            {
                "number": section["number"],
                "eyebrow": section["eyebrow"],
                "title": section["title"],
                "paragraphs": section["paragraphs"],
                "highlights": section["highlights"],
                "sort_order": order,
            },
        )
    ProfileSection.objects.filter(page=profile).exclude(stable_id__in=wanted).delete()
    items = data["usefulLinks"]["items"]
    for order, item in enumerate(items):
        _upsert_child(
            ProfileUsefulLink,
            profile,
            item["id"],
            {
                "label": item["label"],
                "description": item["description"],
                "url": item["url"],
                "cta_label": item["ctaLabel"],
                "sort_order": order,
            },
        )
    ProfileUsefulLink.objects.filter(page=profile).exclude(
        stable_id__in=[item["id"] for item in items]
    ).delete()


def _sync_project_children(project, core, localized):
    evidence_by_id = {item["id"]: item for item in core["evidence"]}
    local_evidence = {item["evidenceId"]: item for item in localized["evidence"]}
    evidence_ids = list(evidence_by_id)
    for order, evidence_id in enumerate(evidence_ids):
        shared = evidence_by_id[evidence_id]
        local = local_evidence[evidence_id]
        _upsert_child(
            ProjectEvidence,
            project,
            evidence_id,
            {
                "evidence_type": shared["type"],
                "url": shared.get("url", ""),
                "label": local["label"],
                "description": local["description"],
                "link_label": local.get("linkLabel", ""),
                "sort_order": order,
            },
            relation_field="project",
        )
    ProjectEvidence.objects.filter(project=project).exclude(stable_id__in=evidence_ids).delete()

    capability_ids = core["capabilityIds"]
    for order, capability_id in enumerate(capability_ids):
        capability = Capability.objects.get(stable_id=capability_id)
        relation, _ = ProjectCapability.objects.get_or_create(
            project=project, capability=capability
        )
        relation.sort_order = order
        relation.save()
    ProjectCapability.objects.filter(project=project).exclude(
        capability__stable_id__in=capability_ids
    ).delete()

    links_by_id = {item["id"]: item for item in core["links"]}
    local_links = {item["linkId"]: item for item in localized["links"]}
    link_ids = list(links_by_id)
    for order, link_id in enumerate(link_ids):
        shared = links_by_id[link_id]
        local = local_links[link_id]
        _upsert_child(
            ProjectLink,
            project,
            link_id,
            {
                "kind": shared["kind"],
                "label": local["label"],
                "accessibility_label": local.get("accessibilityLabel", ""),
                "url": shared["url"],
                "sort_order": order,
            },
            relation_field="project",
        )
    ProjectLink.objects.filter(project=project).exclude(stable_id__in=link_ids).delete()

    claim_ids = [item["id"] for item in localized["claims"]]
    ClaimEvidence.objects.filter(claim__project=project).delete()
    for order, claim_data in enumerate(localized["claims"]):
        claim = _upsert_child(
            ProjectClaim,
            project,
            claim_data["id"],
            {
                "text": claim_data["text"],
                "status": claim_data["status"],
                "sort_order": order,
            },
            relation_field="project",
        )
        for evidence_id in claim_data["evidenceIds"]:
            ClaimEvidence.objects.create(
                claim=claim,
                evidence=ProjectEvidence.objects.get(
                    project=project, stable_id=evidence_id
                ),
            )
    ProjectClaim.objects.filter(project=project).exclude(stable_id__in=claim_ids).delete()
