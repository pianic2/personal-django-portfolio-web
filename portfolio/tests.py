import base64

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.images.models import Image
from wagtail.models import Site

from .models import (
    ClaimEvidence,
    ProfilePage,
    ProjectClaim,
    ProjectEvidence,
    ProjectPage,
)

VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class WagtailBootstrapTests(TestCase):
    def test_public_root_and_admin_login_are_available(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_wagtail_api_v3_and_openapi_are_available(self):
        openapi_response = self.client.get("/api/v3/openapi.json")
        self.assertEqual(openapi_response.status_code, 200)
        self.assertEqual(openapi_response.json()["openapi"], "3.1.0")

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
