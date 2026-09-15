"""Import the versioned MVP content snapshot into Wagtail."""

# The source snapshot contains long editorial strings; keep those values readable.
# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.models import Locale, Site

from portfolio.models import (
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
)

LOCALES = ("it", "en")


# This is deliberately plain Python rather than a fixture tied to database IDs. It is the
# reviewed snapshot of the frontend's canonical content contract at PDPW-13 implementation time.
CAPABILITIES = (
    ("embedded-firmware", "embedded", "Sensori ESP32-C3", "ESP32-C3 sensors"),
    (
        "privacy-aware-design",
        "security",
        "Progettazione attenta alla privacy",
        "Privacy-aware design",
    ),
    ("technical-governance", "architecture", "Governance tecnica", "Technical governance"),
    ("laravel-api", "backend", "API REST Laravel", "Laravel REST API"),
    ("sanctum-authentication", "security", "Autenticazione Sanctum", "Sanctum authentication"),
    ("containerized-delivery", "delivery", "Docker e MySQL", "Docker and MySQL"),
    ("node-api", "backend", "Node.js ed Express", "Node.js and Express"),
    ("sqlite-persistence", "backend", "Persistenza SQLite", "SQLite persistence"),
    ("automated-testing", "quality", "Test automatici", "Automated testing"),
)


@dataclass(frozen=True)
class ProjectSource:
    stable_id: str
    title: tuple[str, str]
    slugs: tuple[str, str]
    origin: str
    visual_variant: str
    featured: bool
    display_order: int
    capabilities: tuple[str, ...]
    repository_url: str
    eyebrow: tuple[str, str]
    detail_eyebrow: tuple[str, str]
    cta_label: tuple[str, str]
    question: tuple[str, str]
    supporting_text: tuple[str, str]
    what_i_worked_on: tuple[str, str]
    future_improvement: tuple[str, str]


PROJECTS = (
    ProjectSource(
        "homeedge-ai-platform",
        ("HomeEdge AI Platform", "HomeEdge AI Platform"),
        ("homeedge-ai-platform", "homeedge-ai-platform"),
        "personal-long-term",
        "signal-yellow",
        True,
        0,
        ("embedded-firmware", "privacy-aware-design", "technical-governance"),
        "https://github.com/pianic2/homeedge-ai-platform",
        ("SMART HOME · SISTEMI EMBEDDED", "SMART HOME · EMBEDDED SYSTEMS"),
        ("SMART HOME · EDGE COMPUTING · GOVERNANCE", "SMART HOME · EDGE COMPUTING · GOVERNANCE"),
        ("Scopri HomeEdge", "Discover HomeEdge"),
        (
            "Come raccogliere informazioni utili da una stanza senza rendere la casa un sistema poco trasparente?",
            "How can useful information be collected from a room without making the home an opaque system?",
        ),
        (
            "Il progetto è ancora nelle prime fasi, ma non è pensato come un esercizio isolato: voglio continuare a svilupparlo aggiungendo backend, applicazione mobile e nuove funzionalità solo dopo averne verificato i confini.",
            "The project is still in its early stages, but it is not intended as an isolated exercise: I plan to extend it with backend, mobile and new capabilities only after verifying their boundaries.",
        ),
        (
            "Ho definito la visione, i confini dell’MVP, la struttura del repository, la governance tecnica e il percorso di validazione dei componenti hardware.",
            "I defined the vision, MVP boundaries, repository structure, technical governance and hardware validation path.",
        ),
        (
            "Il prossimo obiettivo è trasformare le decisioni e i test hardware in un nodo funzionante e collegarlo progressivamente a un backend e a un’applicazione mobile.",
            "The next objective is to turn the decisions and hardware tests into a working node and progressively connect it to a backend and mobile application.",
        ),
    ),
    ProjectSource(
        "its-library-api-laravel",
        ("ITS Library API", "ITS Library API"),
        ("api-libreria-its-laravel", "its-library-api-laravel"),
        "its-training",
        "studio-pink",
        False,
        1,
        ("laravel-api", "sanctum-authentication", "containerized-delivery"),
        "https://github.com/pianic2/its-php-libreria",
        ("LARAVEL · API REST", "LARAVEL · REST API"),
        ("LARAVEL · API REST · LIBRERIA DIGITALE", "LARAVEL · REST API · DIGITAL LIBRARY"),
        ("Scopri la Library API", "Discover the Library API"),
        (
            "Come organizzare libri, autori e categorie in un backend che sia semplice da provare e da mantenere?",
            "How can books, authors and categories be organised in a backend that is easy to run and maintain?",
        ),
        (
            "È il progetto in cui ho lavorato maggiormente sull’integrazione tra API, database, relazioni tra entità e protezione delle operazioni di modifica.",
            "This project helped me work on the relationship between API design, database entities and protected write operations.",
        ),
        (
            "Ho lavorato sulla struttura delle API, sulle relazioni tra libri, autori e categorie, sull’autenticazione e sulla riproducibilità dell’ambiente Docker.",
            "I worked on the API structure, relationships between books, authors and categories, authentication and Docker reproducibility.",
        ),
        (
            "Una possibile evoluzione è aggiungere un’interfaccia frontend e ampliare la gestione dei file e dei permessi.",
            "A possible next step would be adding a frontend interface and expanding file and permission management.",
        ),
    ),
    ProjectSource(
        "node-list-manager",
        ("Progetto ITS Node.js", "ITS Node.js Project"),
        ("gestore-liste-node", "node-list-manager"),
        "its-training",
        "electric-cyan",
        False,
        2,
        ("node-api", "sqlite-persistence", "automated-testing"),
        "https://github.com/pianic2/todo-list-manager-node",
        ("NODE.JS · EXPRESS · SQLITE", "NODE.JS · EXPRESS · SQLITE"),
        ("NODE.JS · EXPRESS · SQLITE", "NODE.JS · EXPRESS · SQLITE"),
        ("Scopri il progetto Node.js", "Discover the Node.js project"),
        (
            "Quanto deve essere complesso un backend per gestire liste e attività?",
            "How complex does a backend need to be to manage lists and tasks?",
        ),
        (
            "Qui l’obiettivo non era costruire una grande architettura, ma mantenere il codice leggibile e il progetto facile da verificare.",
            "The goal was not to create a large architecture, but to keep the code understandable and easy to verify.",
        ),
        (
            "Ho organizzato le route, la persistenza SQLite e i test, cercando di mantenere il progetto piccolo e leggibile.",
            "I organised the routes, SQLite persistence and tests, keeping the project small and readable.",
        ),
        (
            "Potrei estendere la validazione degli input e aggiungere un’interfaccia semplice per utilizzare il backend dal browser.",
            "I could extend input validation and add a simple browser interface for using the backend.",
        ),
    ),
)

EVIDENCE_IDS = {
    "homeedge-ai-platform": (
        "homeedge-mvp-scope",
        "homeedge-architecture-governance",
        "homeedge-product-vision",
        "homeedge-stakeholder-review",
    ),
    "its-library-api-laravel": (
        "library-rest-endpoints",
        "library-docker-setup",
        "library-validation-tests",
    ),
    "node-list-manager": ("node-server-source", "node-package-manifest", "node-automated-tests"),
}
CLAIM_IDS = {
    "homeedge-ai-platform": (
        "sprint-zero-boundary",
        "target-services-unvalidated",
        "product-vision-boundaries",
        "project-progress-stakeholder-review",
    ),
    "its-library-api-laravel": ("rest-resources", "local-containers"),
    "node-list-manager": ("express-route-modules", "sqlite-test-stack"),
}


PROFILE = {
    "it": {
        "title": "Profilo",
        "slug": "profilo",
        "hero_eyebrow": "PROFILO",
        "hero_description": "Il mio percorso nello sviluppo software unisce curiosità, pratica e attenzione ai problemi reali.",
        "highlights_label": "Punti chiave",
        "closing_title": "Continuo a costruire competenze attraverso progetti concreti.",
        "closing_description": "Sono disponibile a confrontarmi su stage, collaborazioni e opportunità junior.",
        "sections": [
            (
                "profile-vocation",
                "01",
                "VOCAZIONE",
                "Prima del codice c’era il bisogno di capire.",
                [
                    "Mi attirano i problemi che richiedono ragionamento e la capacità di collegare elementi diversi."
                ],
                ["Curiosità per i sistemi", "Logica applicata"],
            ),
            (
                "profile-its",
                "02",
                "ITS PRODIGI",
                "Una preparazione professionale costruita con metodo.",
                [
                    "Il percorso Full Stack Developer mi permette di lavorare su frontend, backend, database, testing e delivery."
                ],
                ["Formazione Full Stack", "Progetti strutturati"],
            ),
        ],
    },
    "en": {
        "title": "Profile",
        "slug": "profile",
        "hero_eyebrow": "PROFILE",
        "hero_description": "My path in software development combines curiosity, practice and attention to real problems.",
        "highlights_label": "Key points",
        "closing_title": "I keep building skills through concrete projects.",
        "closing_description": "I am open to internships, collaborations and junior opportunities.",
        "sections": [
            (
                "profile-vocation",
                "01",
                "VOCATION",
                "Before the code, there was a need to understand.",
                [
                    "I am drawn to problems that require reasoning and the ability to connect different elements."
                ],
                ["Curiosity about systems", "Applied logic"],
            ),
            (
                "profile-its",
                "02",
                "ITS PRODIGI",
                "Professional preparation built with method.",
                [
                    "The Full Stack Developer programme lets me work across frontend, backend, databases, testing and delivery."
                ],
                ["Full Stack training", "Structured projects"],
            ),
        ],
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
        root = Site.objects.get(is_default_site=True).root_page
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

        for stable_id, category, it_label, en_label in CAPABILITIES:
            capability, _ = Capability.objects.update_or_create(
                stable_id=stable_id, defaults={"category": category}
            )
            report["capabilities"] += 1
            for code, label in (("it", it_label), ("en", en_label)):
                CapabilityTranslation.objects.update_or_create(
                    capability=capability, locale=locales[code], defaults={"label": label}
                )
                report["capability_translations"] += 1

        for code in LOCALES:
            data = PROFILE[code]
            profile = ProfilePage.objects.filter(locale=locales[code], stable_id="profile").first()
            if profile is None:
                if code == "it":
                    profile = ProfilePage(
                        title=data["title"],
                        slug=data["slug"],
                        stable_id="profile",
                        hero_eyebrow=data["hero_eyebrow"],
                        hero_description=data["hero_description"],
                        highlights_label=data["highlights_label"],
                        closing_title=data["closing_title"],
                        closing_description=data["closing_description"],
                    )
                    profile = root.add_child(instance=profile)
                else:
                    profile = ProfilePage.objects.get(
                        locale=locales["it"], stable_id="profile"
                    ).copy_for_translation(locale=locales["en"], copy_parents=True)
            ProfilePage.objects.filter(pk=profile.pk).update(
                **{
                    field: data[field]
                    for field in (
                        "title",
                        "slug",
                        "hero_eyebrow",
                        "hero_description",
                        "highlights_label",
                        "closing_title",
                        "closing_description",
                    )
                }
            )
            profile.refresh_from_db()
            _sync_profile_children(profile, data["sections"])
            profile.save_revision().publish()
            report["profile"] += 1

        for source in PROJECTS:
            for index, code in enumerate(LOCALES):
                project = ProjectPage.objects.filter(
                    locale=locales[code], stable_id=source.stable_id
                ).first()
                values = {
                    "title": source.title[index],
                    "slug": source.slugs[index],
                    "stable_id": source.stable_id,
                    "eyebrow": source.eyebrow[index],
                    "detail_eyebrow": source.detail_eyebrow[index],
                    "cta_label": source.cta_label[index],
                    "question": source.question[index],
                    "supporting_text": source.supporting_text[index],
                    "what_i_worked_on": source.what_i_worked_on[index],
                    "future_improvement": source.future_improvement[index],
                    "origin": source.origin,
                    "visual_variant": source.visual_variant,
                    "featured": source.featured,
                    "display_order": source.display_order,
                    "narrative": {
                        "source": "its-react-portfolio-web",
                        "stable_id": source.stable_id,
                    },
                    "metadata": {
                        "title": source.title[index],
                        "description": source.supporting_text[index],
                        "noIndex": False,
                    },
                }
                if project is None:
                    if code == "it":
                        project = root.add_child(instance=ProjectPage(**values))
                    else:
                        project = ProjectPage.objects.get(
                            locale=locales["it"], stable_id=source.stable_id
                        ).copy_for_translation(locale=locales["en"], copy_parents=True)
                ProjectPage.objects.filter(pk=project.pk).update(**values)
                project.refresh_from_db()
                _sync_project_children(project, source, code)
                project.save_revision().publish()
                report["project_variants"] += 1
            report["projects"] += 1

        report["claims"] = ProjectClaim.objects.count()
        report["evidence"] = ProjectEvidence.objects.count()
        report["links"] = ProjectLink.objects.count()
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
        if options["as_json"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write("Imported " + json.dumps(report, ensure_ascii=False, sort_keys=True))


def _sync_profile_children(profile, sections):
    wanted = set()
    for order, (stable_id, number, eyebrow, title, paragraphs, highlights) in enumerate(sections):
        wanted.add(stable_id)
        _upsert_child(
            ProfileSection,
            profile,
            stable_id,
            {
                "number": number,
                "eyebrow": eyebrow,
                "title": title,
                "paragraphs": paragraphs,
                "highlights": highlights,
                "sort_order": order,
            },
        )
    ProfileSection.objects.filter(page=profile).exclude(stable_id__in=wanted).delete()
    _upsert_child(
        ProfileUsefulLink,
        profile,
        "leetcode",
        {
            "label": "LeetCode",
            "description": "Profile for algorithm and problem-solving practice.",
            "url": "https://leetcode.com/u/pianic2",
            "cta_label": "Open my LeetCode profile",
        },
    )
    ProfileUsefulLink.objects.filter(page=profile).exclude(stable_id="leetcode").delete()


def _sync_project_children(project, source, code):
    evidence_ids = EVIDENCE_IDS[source.stable_id]
    for order, evidence_id in enumerate(evidence_ids):
        _upsert_child(
            ProjectEvidence,
            project,
            evidence_id,
            {
                "evidence_type": "documentation",
                "url": source.repository_url,
                "label": f"{source.title[0]} evidence {evidence_id}",
                "description": "Canonical repository evidence.",
                "link_label": "Open repository" if code == "en" else "Apri il repository",
                "sort_order": order,
            },
            relation_field="project",
        )
    ProjectEvidence.objects.filter(project=project).exclude(stable_id__in=evidence_ids).delete()
    for order, capability_id in enumerate(source.capabilities):
        capability = Capability.objects.get(stable_id=capability_id)
        relation, _ = ProjectCapability.objects.get_or_create(
            project=project, capability=capability
        )
        relation.sort_order = order
        relation.save()
    ProjectCapability.objects.filter(project=project).exclude(
        capability__stable_id__in=source.capabilities
    ).delete()
    _upsert_child(
        ProjectLink,
        project,
        f"{source.stable_id}-repository",
        {
            "kind": "repository",
            "label": "GitHub repository" if code == "en" else "Repository GitHub",
            "url": source.repository_url,
            "sort_order": 0,
        },
        relation_field="project",
    )
    ProjectLink.objects.filter(project=project).exclude(
        stable_id=f"{source.stable_id}-repository"
    ).delete()
    claim_ids = CLAIM_IDS[source.stable_id]
    for order, claim_id in enumerate(claim_ids):
        claim = _upsert_child(
            ProjectClaim,
            project,
            claim_id,
            {
                "text": "The canonical repository documents this project capability.",
                "status": "demonstrated",
                "sort_order": order,
            },
            relation_field="project",
        )
        evidence = ProjectEvidence.objects.get(
            project=project, stable_id=evidence_ids[order % len(evidence_ids)]
        )
        ClaimEvidence.objects.update_or_create(claim=claim, evidence=evidence)
    ProjectClaim.objects.filter(project=project).exclude(stable_id__in=claim_ids).delete()
