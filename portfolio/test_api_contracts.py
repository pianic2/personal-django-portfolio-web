from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from wagtail.images import get_image_model
from wagtail.models import Locale, Site

from .models import BlogIndexPage, BlogPostPage, ProjectPage
from .test_support import ensure_localized_site_roots

VALID_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\x0dIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff"
    b"\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)


class PublicAPIContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_localized_site_roots()
        call_command("import_portfolio", verbosity=0)
        cls.root = Site.objects.get(is_default_site=True).root_page

    def test_profile_and_project_examples_have_consumer_contract_shapes(self):
        profile_list = self.client.get(
            "/api/v3/pages/", {"type": "portfolio.ProfilePage", "locale": "en"}
        )
        self.assertEqual(profile_list.status_code, 200)
        profile_item = profile_list.json()["items"][0]
        self.assertIsInstance(profile_item["id"], int)
        self.assertIsInstance(profile_item["title"], str)
        self.assertEqual(profile_item["meta"]["locale"], "en")
        self.assertIsInstance(profile_item["meta"]["slug"], str)

        profile = self.client.get(f"/api/v3/pages/{profile_item['id']}/").json()
        for field in (
            "stable_id",
            "hero_eyebrow",
            "hero_description",
            "highlights_label",
            "closing_title",
            "closing_description",
        ):
            self.assertIsInstance(profile[field], str)
        self.assertIsInstance(profile["sections"], list)
        self.assertIsInstance(profile["useful_links"], list)
        self.assertIsInstance(profile["sections"][0]["paragraphs"], list)
        self.assertIsInstance(profile["useful_links"][0]["url"], str)

        project_list = self.client.get(
            "/api/v3/pages/", {"type": "portfolio.ProjectPage", "locale": "en"}
        )
        self.assertEqual(project_list.status_code, 200)
        project_item = project_list.json()["items"][0]
        self.assertIsInstance(project_item["id"], int)
        self.assertEqual(project_item["meta"]["locale"], "en")

        project = self.client.get(f"/api/v3/pages/{project_item['id']}/").json()
        for field in (
            "stable_id",
            "eyebrow",
            "detail_eyebrow",
            "cta_label",
            "question",
            "supporting_text",
            "what_i_worked_on",
            "future_improvement",
            "origin",
            "visual_variant",
        ):
            self.assertIsInstance(project[field], str)
        self.assertIsInstance(project["featured"], bool)
        self.assertIsInstance(project["display_order"], int)
        for field in (
            "narrative",
            "metadata",
            "capabilities",
            "links",
            "assets",
            "evidence",
            "claims",
        ):
            self.assertIsInstance(project[field], (dict, list))

    def test_locale_and_slug_queries_are_locale_specific(self):
        for locale, slug in (("it", "api-libreria-its-laravel"), ("en", "its-library-api-laravel")):
            response = self.client.get(
                "/api/v3/pages/",
                {"type": "portfolio.ProjectPage", "locale": locale, "slug": slug},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["items"][0]["meta"]["locale"], locale)
            self.assertEqual(response.json()["items"][0]["meta"]["slug"], slug)

    def test_invalid_api_filters_return_failures(self):
        unsupported_type = self.client.get("/api/v3/pages/", {"type": "portfolio.UnknownPage"})
        self.assertEqual(unsupported_type.status_code, 422)
        self.assertEqual(unsupported_type.json()["status"], 422)

        unsupported_locale = self.client.get("/api/v3/pages/", {"locale": "de"})
        self.assertEqual(unsupported_locale.status_code, 404)
        self.assertEqual(unsupported_locale.json()["status"], 404)

    def test_cors_contract_allows_configured_origin_only(self):
        with override_settings(CORS_ALLOWED_ORIGINS=["https://pianic2.github.io"]):
            allowed = self.client.get("/api/v3/pages/", HTTP_ORIGIN="https://pianic2.github.io")
            self.assertEqual(allowed.headers["Access-Control-Allow-Origin"], "https://pianic2.github.io")

            rejected = self.client.get("/api/v3/pages/", HTTP_ORIGIN="https://evil.example")
            self.assertNotIn("Access-Control-Allow-Origin", rejected.headers)

    def test_anonymous_api_cannot_read_unpublished_draft_by_id_or_slug(self):
        draft = ProjectPage(
            title="Contract draft",
            slug="contract-draft",
            stable_id="contract-draft",
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

        by_id = self.client.get(f"/api/v3/pages/{draft.id}/")
        self.assertEqual(by_id.status_code, 404)

        by_slug = self.client.get(
            "/api/v3/pages/", {"type": "portfolio.ProjectPage", "slug": draft.slug}
        )
        self.assertEqual(by_slug.status_code, 200)
        self.assertEqual(by_slug.json()["count"], 0)

    def test_published_blog_contract_is_localized_ordered_and_media_safe(self):
        index = BlogIndexPage.objects.get(locale__language_code="it", stable_id="blog")
        image = get_image_model().objects.create(
            title="Featured", file=SimpleUploadedFile("featured.png", VALID_PNG)
        )
        first = BlogPostPage(
            title="First post",
            slug="first-post",
            stable_id="first-post",
            excerpt="First excerpt",
            body="First body",
            featured_image=image,
        )
        index.add_child(instance=first)
        first.save_revision().publish()
        second = BlogPostPage(
            title="Second post",
            slug="second-post",
            stable_id="second-post",
            excerpt="Second excerpt",
            body="Second body",
        )
        index.add_child(instance=second)
        second.save_revision().publish()
        translation = first.copy_for_translation(
            locale=Locale.objects.get(language_code="en"), copy_parents=True
        )
        translation.title = "First post EN"
        translation.slug = "first-post-en"
        translation.save_revision().publish()

        response = self.client.get(
            "/api/v3/pages/",
            {
                "type": "portfolio.BlogPostPage",
                "locale": "it",
                "fields": "stable_id,excerpt,publication_date,body,featured_image",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual([item["id"] for item in payload["items"]], [first.id, second.id])
        self.assertEqual(payload["items"][0]["meta"]["locale"], "it")
        self.assertEqual(payload["items"][0]["meta"]["slug"], "first-post")

        detail = self.client.get(f"/api/v3/pages/{first.id}/").json()
        self.assertTrue(
            {"title", "stable_id", "excerpt", "publication_date", "body", "featured_image"}
            <= set(detail)
        )
        self.assertEqual(detail["featured_image"]["id"], image.id)
        localized = self.client.get(
            "/api/v3/pages/",
            {"type": "portfolio.BlogPostPage", "locale": "en", "slug": "first-post-en"},
        )
        self.assertEqual(localized.status_code, 200)
        self.assertEqual(localized.json()["count"], 1)
        self.assertEqual(localized.json()["items"][0]["meta"]["locale"], "en")
        unknown_slug = self.client.get(
            "/api/v3/pages/",
            {"type": "portfolio.BlogPostPage", "locale": "en", "slug": "missing"},
        )
        self.assertEqual(unknown_slug.status_code, 200)
        self.assertEqual(unknown_slug.json()["count"], 0)
        missing_locale = self.client.get(
            "/api/v3/pages/", {"type": "portfolio.BlogPostPage", "locale": "de"}
        )
        self.assertEqual(missing_locale.status_code, 404)

    def test_anonymous_blog_api_excludes_drafts_by_id_and_slug(self):
        index = BlogIndexPage.objects.get(locale__language_code="it", stable_id="blog")
        draft = BlogPostPage(
            title="Draft post",
            slug="draft-post",
            stable_id="draft-post",
            excerpt="Draft excerpt",
            body="Draft body",
        )
        index.add_child(instance=draft)
        draft.save_revision()
        BlogPostPage.objects.filter(pk=draft.pk).update(live=False, has_unpublished_changes=True)
        draft.refresh_from_db()

        by_id = self.client.get(f"/api/v3/pages/{draft.id}/")
        self.assertEqual(by_id.status_code, 404)
        by_slug = self.client.get(
            "/api/v3/pages/",
            {"type": "portfolio.BlogPostPage", "locale": "it", "slug": "draft-post"},
        )
        self.assertEqual(by_slug.status_code, 200)
        self.assertEqual(by_slug.json()["count"], 0)
        by_list = self.client.get(
            "/api/v3/pages/", {"type": "portfolio.BlogPostPage", "locale": "it"}
        )
        self.assertEqual(by_list.status_code, 200)
        self.assertEqual(by_list.json()["count"], 0)
