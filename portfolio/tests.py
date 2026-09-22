import base64
import json
import sys
from io import StringIO
from types import ModuleType

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import clear_url_caches, path, reverse
from django.utils import timezone
from wagtail.images.models import Image
from wagtail.models import Site

from .canonical_data import CANONICAL
from .models import (
    BlogIndexPage,
    BlogPostPage,
    ClaimEvidence,
    ProfilePage,
    ProjectClaim,
    ProjectEvidence,
    ProjectPage,
    validate_portfolio_integrity,
)

VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class WagtailBootstrapTests(TestCase):
    def test_admin_login_is_available(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_production_root_is_not_content_bearing(self):
        import portfolio.urls

        module_name = "portfolio._pdpw33_production_urls"
        production_urls = ModuleType(module_name)
        production_urls.urlpatterns = [
            *portfolio.urls.urlpatterns[:5],
            path("", portfolio.urls.production_root),
            portfolio.urls.urlpatterns[5],
        ]
        sys.modules[module_name] = production_urls
        self.addCleanup(sys.modules.pop, module_name)

        with override_settings(ROOT_URLCONF=module_name):
            response = self.client.get("/")
        clear_url_caches()

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("Welcome to your new Wagtail site!", response.content.decode())

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_production_explicit_routes_remain_available_without_debug_media(self):
        import portfolio.urls

        module_name = "portfolio._pdpw33_production_urls"
        production_urls = ModuleType(module_name)
        production_urls.urlpatterns = [
            *portfolio.urls.urlpatterns[:5],
            path("", portfolio.urls.production_root),
            portfolio.urls.urlpatterns[5],
        ]
        sys.modules[module_name] = production_urls
        self.addCleanup(sys.modules.pop, module_name)

        with override_settings(ROOT_URLCONF=module_name):
            self.assertEqual(self.client.get("/admin/").status_code, 302)
            self.assertEqual(self.client.get("/django-admin/").status_code, 302)
            self.assertEqual(self.client.get("/api/v3/openapi.json").status_code, 200)
            self.assertEqual(self.client.post("/api/contact/", {}).status_code, 400)
            self.assertEqual(self.client.get("/media/missing.txt").status_code, 404)
        clear_url_caches()

    def test_wagtail_api_v3_and_openapi_are_available(self):
        openapi_response = self.client.get("/api/v3/openapi.json")
        self.assertEqual(openapi_response.status_code, 200)
        schema = openapi_response.json()
        self.assertEqual(schema["openapi"], "3.1.0")
        self.assertIn("/api/v3/pages/", schema["paths"])
        self.assertIn("/api/v3/images/", schema["paths"])
        self.assertIn("post", schema["paths"]["/api/v3/images/"])
        self.assertIn("patch", schema["paths"]["/api/v3/images/{image_id}/"])
        self.assertEqual(self.client.get("/api/v3/openapi.json").json(), schema)
        self.assertEqual(self.client.get("/api/v3/docs/").status_code, 200)

        pages_response = self.client.get("/api/v3/pages/")
        self.assertEqual(pages_response.status_code, 200)
        self.assertIn("meta", pages_response.json()["items"][0])

    def test_authenticated_wagtail_admin_loads(self):
        self.create_superuser()
        self.assertTrue(self.client.login(username="admin", password="test-password"))

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)

    def test_wagtail_image_uses_configured_media_storage(self):
        self.create_superuser()
        self.assertTrue(self.client.login(username="admin", password="test-password"))

        response = self.client.post(
            reverse("wagtailimages:add"),
            {
                "title": "Smoke test image",
                "file": SimpleUploadedFile("smoke-test.png", VALID_PNG, content_type="image/png"),
            },
        )
        self.assertEqual(response.status_code, 302)

        image = Image.objects.get(title="Smoke test image")
        image.refresh_from_db()

        self.assertTrue(image.file.storage.exists(image.file.name))
        with image.file.storage.open(image.file.name, "rb") as stored_file:
            self.assertEqual(stored_file.read(), VALID_PNG)

        image.file.delete(save=False)
        image.delete()
        self.assertFalse(Image.objects.filter(pk=image.pk).exists())

    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173", "https://pianic2.github.io"])
    def test_cors_allows_configured_origins_and_rejects_unknown_origin(self):
        for origin in ("http://localhost:5173", "https://pianic2.github.io"):
            response = self.client.options(
                "/",
                HTTP_ORIGIN=origin,
                HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            )
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)

        response = self.client.get("/", HTTP_ORIGIN="https://evil.example")
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    @staticmethod
    def create_superuser():
        from django.contrib.auth import get_user_model

        return get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="test-password"
        )


class PortfolioDomainModelTests(TestCase):
    def setUp(self):
        self.root = Site.objects.get(is_default_site=True).root_page
        from wagtail.models import Locale

        self.italian_locale = Locale.objects.get(language_code="it")
        self.english_locale = Locale.objects.create(language_code="en")

    def make_project(self, stable_id):
        project = ProjectPage(
            title=stable_id.title(),
            slug=stable_id,
            stable_id=stable_id,
            eyebrow="PROJECT",
            detail_eyebrow="DETAIL",
            cta_label="Open",
            question="What was built?",
            supporting_text="Supporting context.",
            what_i_worked_on="The work.",
            future_improvement="The next step.",
            narrative={"cardSummary": "Summary"},
            metadata={"title": stable_id, "description": "Description"},
            origin=ProjectPage.Origin.ITS_TRAINING,
            visual_variant=ProjectPage.VisualVariant.STUDIO_PINK,
        )
        self.root.add_child(instance=project)
        project.save_revision().publish()
        return project

    def make_blog_index(self):
        index = BlogIndexPage(title="Blog", slug="blog", stable_id="blog")
        self.root.add_child(instance=index)
        index.save_revision().publish()
        return index

    def test_blog_pages_support_native_constraints_and_lifecycle(self):
        index = self.make_blog_index()
        image = Image.objects.create(
            title="Blog feature",
            file=SimpleUploadedFile("blog-feature.png", VALID_PNG, content_type="image/png"),
        )
        post = BlogPostPage(
            title="A post",
            slug="a-post",
            stable_id="a-post",
            excerpt="A short summary.",
            body="A plain text body.",
            featured_image=image,
        )
        index.add_child(instance=post)
        draft = post.save_revision()

        self.assertEqual(post.locale, self.italian_locale)
        preview = draft.as_object()
        self.assertIsNotNone(preview)
        self.assertEqual(preview.featured_image_id, image.pk)
        self.assertEqual(post.get_parent().specific_class, BlogIndexPage)
        self.assertEqual(post.content_panels[-1].field_name, "featured_image")
        self.assertEqual(post.get_children().count(), 0)

        draft.publish()
        post.refresh_from_db()
        self.assertTrue(post.live)
        self.assertEqual(post.publication_date, timezone.localdate())

        translation = post.copy_for_translation(locale=self.english_locale, copy_parents=True)
        translation.title = "A post in English"
        translation.slug = "a-post-en"
        translation.save()

        self.assertEqual(translation.translation_key, post.translation_key)
        self.assertEqual(translation.stable_id, post.stable_id)

    def test_blog_post_can_remain_single_locale_without_inventing_translation(self):
        index = self.make_blog_index()
        post = BlogPostPage(
            title="Italian only",
            slug="italian-only",
            stable_id="italian-only",
            excerpt="Summary.",
            body="Body.",
        )
        index.add_child(instance=post)
        post.save_revision().publish()

        self.assertEqual(BlogPostPage.objects.filter(stable_id="italian-only").count(), 1)
        self.assertEqual(post.get_translations().count(), 0)

    def test_blog_post_is_editable_in_native_wagtail_admin(self):
        index = self.make_blog_index()
        post = BlogPostPage(
            title="Admin post",
            slug="admin-post",
            stable_id="admin-post",
            excerpt="Summary.",
            body="Body.",
        )
        index.add_child(instance=post)
        post.save_revision().publish()

        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser(
            username="blog-editor", email="blog@example.com", password="editor-password"
        )
        self.assertTrue(self.client.login(username="blog-editor", password="editor-password"))

        response = self.client.get(f"/admin/pages/{post.id}/edit/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publication date")
        self.assertContains(response, "Featured image")

    def test_profile_and_project_pages_support_locale_identity_and_revisions(self):
        profile = ProfilePage(
            title="Profile",
            slug="profile",
            stable_id="profile",
            hero_eyebrow="PROFILE",
            hero_description="A profile.",
            highlights_label="Highlights",
            closing_title="Closing",
            closing_description="A closing.",
        )
        self.root.add_child(instance=profile)
        project = self.make_project("sample-project")

        self.assertEqual(profile.locale.language_code, "it")
        self.assertEqual(project.locale.language_code, "it")
        self.assertIsNotNone(project.save_revision().as_object())

        translation = project.copy_for_translation(locale=self.english_locale, copy_parents=True)
        translation.title = "Sample project"
        translation.slug = "sample-project-en"
        translation.save()

        self.assertEqual(translation.translation_key, project.translation_key)
        self.assertEqual(translation.stable_id, project.stable_id)
        self.assertNotEqual(translation.slug, project.slug)

        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser(
            username="editor", email="editor@example.com", password="editor-password"
        )
        self.assertTrue(self.client.login(username="editor", password="editor-password"))
        admin_response = self.client.get(f"/admin/pages/{project.id}/edit/")
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Stable editorial identifier")

    def test_claim_evidence_cannot_cross_project_boundaries(self):
        first = self.make_project("first-project")
        second = self.make_project("second-project")
        first_evidence = ProjectEvidence(
            project=first,
            stable_id="first-evidence",
            evidence_type=ProjectEvidence.EvidenceType.DOCUMENTATION,
            url="https://example.com/first",
            label="First evidence",
            description="First evidence.",
        )
        first_evidence.save()
        claim = ProjectClaim(
            project=second,
            stable_id="second-claim",
            text="A claim",
            status=ProjectClaim.Status.VERIFIED,
        )
        claim.save()

        relation = ClaimEvidence(claim=claim, evidence=first_evidence)
        with self.assertRaisesMessage(ValidationError, "same project"):
            relation.full_clean()

        valid_evidence = ProjectEvidence(
            project=second,
            stable_id="second-evidence",
            evidence_type=ProjectEvidence.EvidenceType.TEST,
            url="https://example.com/second",
            label="Second evidence",
            description="Second evidence.",
        )
        valid_evidence.save()
        relation = ClaimEvidence(claim=claim, evidence=valid_evidence)
        relation.full_clean()
        relation.save()
        claim.refresh_from_db()
        claim.full_clean()

        planned = ProjectClaim(
            project=second,
            stable_id="planned-claim",
            text="A planned claim",
            status=ProjectClaim.Status.PLANNED,
        )
        planned.save()
        planned_relation = ClaimEvidence(claim=planned, evidence=valid_evidence)
        planned_relation.save()
        with self.assertRaisesMessage(ValidationError, "cannot reference evidence"):
            planned.full_clean()

    def test_verified_claim_without_evidence_is_rejected(self):
        project = self.make_project("claim-project")
        claim = ProjectClaim.objects.create(
            project=project,
            stable_id="unsupported-claim",
            text="An unsupported claim",
            status=ProjectClaim.Status.VERIFIED,
        )

        with self.assertRaisesMessage(ValidationError, "require evidence"):
            claim.full_clean()

        with self.assertRaisesMessage(ValidationError, "requires at least one Evidence"):
            validate_portfolio_integrity()

    def test_duplicate_project_stable_id_is_rejected_on_save(self):
        self.make_project("duplicate-project")
        duplicate = ProjectPage(
            title="Duplicate",
            slug="duplicate-project-2",
            stable_id="duplicate-project",
            eyebrow="PROJECT",
            detail_eyebrow="DETAIL",
            cta_label="Open",
            question="What was built?",
            supporting_text="Supporting context.",
            what_i_worked_on="The work.",
            future_improvement="The next step.",
            narrative={"cardSummary": "Summary"},
            metadata={"title": "duplicate", "description": "Description"},
            origin=ProjectPage.Origin.ITS_TRAINING,
            visual_variant=ProjectPage.VisualVariant.STUDIO_PINK,
        )

        with self.assertRaisesMessage(ValidationError, "already used in this locale"):
            self.root.add_child(instance=duplicate)

    def test_native_wagtail_api_exposes_portfolio_page_fields(self):
        project = self.make_project("api-project")
        response = self.client.get(
            f"/api/v3/pages/{project.id}/",
            {"fields": "stable_id,origin,featured"},
        )

        self.assertEqual(response.status_code, 200)
        item = response.json()
        self.assertEqual(item["stable_id"], "api-project")
        self.assertEqual(item["origin"], ProjectPage.Origin.ITS_TRAINING)
        self.assertFalse(item["featured"])

    def test_public_api_supports_localized_profile_and_project_use_cases(self):
        call_command("import_portfolio", stdout=None)

        profile_response = self.client.get(
            "/api/v3/pages/",
            {
                "type": "portfolio.ProfilePage",
                "locale": "it",
            },
        )
        self.assertEqual(profile_response.status_code, 200)
        profile_items = profile_response.json()["items"]
        self.assertEqual(len(profile_items), 1)
        self.assertEqual(profile_items[0]["meta"]["locale"], "it")
        profile_detail = self.client.get(f"/api/v3/pages/{profile_items[0]['id']}/")
        self.assertEqual(profile_detail.status_code, 200)
        self.assertEqual(len(profile_detail.json()["sections"]), 3)
        self.assertEqual(len(profile_detail.json()["useful_links"]), 1)

        project_list_response = self.client.get(
            "/api/v3/pages/",
            {
                "type": "portfolio.ProjectPage",
                "locale": "en",
                "featured": "true",
                "order": "display_order",
            },
        )
        self.assertEqual(project_list_response.status_code, 200)
        project_items = project_list_response.json()["items"]
        self.assertTrue(project_items)
        expected_ids = list(
            ProjectPage.objects.filter(
                locale__language_code="en", featured=True
            ).order_by("display_order").values_list("id", flat=True)
        )
        self.assertEqual(
            [item["id"] for item in project_items],
            expected_ids,
        )

        slug = "its-library-api-laravel"
        slug_response = self.client.get(
            "/api/v3/pages/",
            {"type": "portfolio.ProjectPage", "locale": "en", "slug": slug},
        )
        self.assertEqual(slug_response.status_code, 200)
        self.assertEqual(len(slug_response.json()["items"]), 1)
        project_id = slug_response.json()["items"][0]["id"]

        detail_response = self.client.get(
            f"/api/v3/pages/{project_id}/", {"fields": "links,claims"}
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["meta"]["slug"], slug)
        self.assertTrue(detail_response.json()["links"])
        self.assertTrue(detail_response.json()["claims"])

    def test_public_api_excludes_unpublished_pages(self):
        draft = ProjectPage(
            title="Draft project",
            slug="draft-project",
            stable_id="draft-project",
            eyebrow="DRAFT",
            detail_eyebrow="DRAFT",
            cta_label="Open",
            question="Question",
            supporting_text="Supporting text",
            what_i_worked_on="Work",
            future_improvement="Future",
            narrative={"cardSummary": "Draft"},
            metadata={"title": "Draft", "description": "Draft"},
            origin=ProjectPage.Origin.ITS_TRAINING,
            visual_variant=ProjectPage.VisualVariant.STUDIO_PINK,
        )
        self.root.add_child(instance=draft)
        ProjectPage.objects.filter(pk=draft.pk).update(live=False, has_unpublished_changes=True)
        draft.save_revision()

        response = self.client.get(
            "/api/v3/pages/",
            {"type": "portfolio.ProjectPage", "slug": "draft-project"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)


class PortfolioImportTests(TestCase):
    def test_import_matches_backend_owned_canonical_subset_exactly(self):
        call_command("import_portfolio", stdout=None)

        for code in ("it", "en"):
            locale = code
            profile_source = CANONICAL["locales"][locale]["profilePage"]
            profile = ProfilePage.objects.get(
                stable_id="profile", locale__language_code=locale
            )
            self.assertEqual(profile.title, profile_source["hero"]["title"])
            self.assertEqual(profile.hero_eyebrow, profile_source["hero"]["eyebrow"])
            self.assertEqual(profile.hero_description, profile_source["hero"]["description"])
            self.assertEqual(profile.closing_title, profile_source["closing"]["title"])
            self.assertEqual(profile.closing_description, profile_source["closing"]["description"])
            self.assertEqual(profile.slug, "profilo" if locale == "it" else "profile")
            self.assertEqual(
                list(
                    profile.sections.order_by("sort_order").values(
                        "stable_id", "number", "eyebrow", "title", "paragraphs", "highlights"
                    )
                ),
                [
                    {
                        "stable_id": section["id"],
                        "number": section["number"],
                        "eyebrow": section["eyebrow"],
                        "title": section["title"],
                        "paragraphs": section["paragraphs"],
                        "highlights": section["highlights"],
                    }
                    for section in profile_source["sections"]
                ],
            )

            for source in CANONICAL["locales"][locale]["projects"]:
                project = ProjectPage.objects.get(
                    stable_id=source["projectId"], locale__language_code=locale
                )
                core = next(
                    item
                    for item in CANONICAL["shared"]["projects"]
                    if item["id"] == source["projectId"]
                )
                self.assertEqual(project.slug, source["slug"])
                self.assertEqual(project.narrative, source["narrative"])
                self.assertEqual(project.metadata, source["metadata"])
                self.assertEqual(project.featured, core["featured"])
                self.assertEqual(project.display_order, core["order"])
                self.assertEqual(project.origin, core["origin"])
                self.assertEqual(project.visual_variant, core["visualVariant"])
                self.assertEqual(
                    list(project.claims.order_by("sort_order").values_list(
                        "stable_id", "text", "status"
                    )),
                    [(claim["id"], claim["text"], claim["status"]) for claim in source["claims"]],
                )
                self.assertEqual(
                    {
                        claim.stable_id: list(
                            claim.evidence.order_by("sort_order").values_list(
                                "stable_id", flat=True
                            )
                        )
                        for claim in project.claims.all()
                    },
                    {claim["id"]: claim["evidenceIds"] for claim in source["claims"]},
                )

    def test_import_is_bilingual_and_repeatable(self):
        output = StringIO()
        call_command("import_portfolio", "--json", stdout=output)
        from wagtail.models import Locale

        italian_locale = Locale.objects.get(language_code="it")
        english_locale = Locale.objects.get(language_code="en")
        report = json.loads(output.getvalue())
        self.assertEqual(report["locales"], ["it", "en"])
        self.assertEqual(
            report["profile_identifiers"],
            [
                {"locale": "en", "slug": "profile", "stable_id": "profile"},
                {"locale": "it", "slug": "profilo", "stable_id": "profile"},
            ],
        )
        self.assertEqual(
            len(report["project_identifiers"]),
            6,
        )
        self.assertEqual(
            {(item["stable_id"], item["locale"]) for item in report["project_identifiers"]},
            {
                (project_id, locale)
                for project_id in (
                    "homeedge-ai-platform",
                    "its-library-api-laravel",
                    "node-list-manager",
                )
                for locale in ("it", "en")
            },
        )
        first_counts = {
            "profiles": ProfilePage.objects.count(),
            "projects": ProjectPage.objects.count(),
            "claims": ProjectClaim.objects.count(),
            "evidence": ProjectEvidence.objects.count(),
        }
        self.assertEqual(first_counts["profiles"], 2)
        self.assertEqual(first_counts["projects"], 6)
        self.assertEqual(first_counts["claims"], 16)
        self.assertEqual(first_counts["evidence"], 20)
        self.assertEqual(
            set(ProjectPage.objects.values_list("stable_id", "locale__language_code")),
            {
                (project_id, locale)
                for project_id in (
                    "homeedge-ai-platform",
                    "its-library-api-laravel",
                    "node-list-manager",
                )
                for locale in ("it", "en")
            },
        )
        self.assertEqual(
            set(ProjectPage.objects.values_list("stable_id", "slug")),
            {
                ("homeedge-ai-platform", "homeedge-ai-platform"),
                ("its-library-api-laravel", "api-libreria-its-laravel"),
                ("its-library-api-laravel", "its-library-api-laravel"),
                ("node-list-manager", "gestore-liste-node"),
                ("node-list-manager", "node-list-manager"),
            },
        )
        for stable_id in ("homeedge-ai-platform", "its-library-api-laravel", "node-list-manager"):
            variants = ProjectPage.objects.filter(stable_id=stable_id).order_by("locale_id")
            self.assertEqual({variant.locale.language_code for variant in variants}, {"it", "en"})
            self.assertEqual(
                {variant.translation_key for variant in variants},
                {variants[0].translation_key},
            )
            self.assertEqual(
                {
                    variant.locale.language_code: variant.get_translation(
                        english_locale
                        if variant.locale.language_code == "it"
                        else italian_locale
                    ).locale.language_code
                    for variant in variants
                },
                {"it": "en", "en": "it"},
            )
        validate_portfolio_integrity()
        call_command("import_portfolio", stdout=None)
        self.assertEqual(
            {
                model: manager.count()
                for model, manager in (
                    ("profiles", ProfilePage.objects),
                    ("projects", ProjectPage.objects),
                    ("claims", ProjectClaim.objects),
                    ("evidence", ProjectEvidence.objects),
                )
            },
            first_counts,
        )

    def test_import_publishes_editable_revisions(self):
        call_command("import_portfolio", stdout=None)
        self.assertTrue(ProfilePage.objects.filter(locale__language_code="en", live=True).exists())
        project = ProjectPage.objects.get(
            stable_id="homeedge-ai-platform", locale__language_code="en"
        )
        self.assertTrue(project.live)
        self.assertGreater(project.revisions.count(), 0)
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="test-password"
        )
        self.assertTrue(self.client.login(username="admin", password="test-password"))
        response = self.client.get(f"/admin/pages/{project.id}/edit/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stable editorial identifier")

        form = response.context["form"]
        data = {
            name: field.initial
            for name, field in form.fields.items()
            if field.initial is not None
        }
        data.update(
            {
                "title": project.title,
                "slug": project.slug,
                "stable_id": project.stable_id,
                "eyebrow": project.eyebrow,
                "detail_eyebrow": project.detail_eyebrow,
                "cta_label": project.cta_label,
                "question": project.question,
                "supporting_text": "Edited through native Wagtail admin.",
                "what_i_worked_on": project.what_i_worked_on,
                "future_improvement": project.future_improvement,
                "origin_description": project.origin_description,
                "narrative": json.dumps(project.narrative),
                "metadata": json.dumps(project.metadata),
                "origin": project.origin,
                "visual_variant": project.visual_variant,
                "featured": "on" if project.featured else "",
                "display_order": project.display_order,
            }
        )
        for formset in form.formsets.values():
            data[f"{formset.prefix}-TOTAL_FORMS"] = formset.total_form_count()
            data[f"{formset.prefix}-INITIAL_FORMS"] = formset.initial_form_count()
            data[f"{formset.prefix}-MIN_NUM_FORMS"] = 0
            data[f"{formset.prefix}-MAX_NUM_FORMS"] = 1000
            for inline_form in formset.initial_forms:
                for name, field in inline_form.fields.items():
                    value = inline_form.initial.get(name)
                    if name == "id":
                        value = inline_form.instance.pk
                    if value is not None:
                        data[f"{inline_form.prefix}-{name}"] = value

        revision_count = project.revisions.count()
        save_response = self.client.post(f"/admin/pages/{project.id}/edit/", data)
        self.assertEqual(save_response.status_code, 302)
        project.refresh_from_db()
        self.assertGreater(project.revisions.count(), revision_count)
        self.assertEqual(
            project.revisions.order_by("-created_at").first().as_object().supporting_text,
            "Edited through native Wagtail admin.",
        )

    def test_integrity_rejects_missing_project_locale(self):
        call_command("import_portfolio", stdout=None)
        ProjectPage.objects.get(
            stable_id="homeedge-ai-platform", locale__language_code="en"
        ).delete()

        with self.assertRaisesMessage(ValidationError, "exactly one it and one en"):
            validate_portfolio_integrity()
