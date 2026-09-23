import json
import threading
from io import BytesIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.color import no_style
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from PIL import Image as PILImage
from wagtail.images import get_image_model
from wagtail.models import APIToken, Locale, Site

from .models import BlogIndexPage, BlogPostPage, ProjectPage
from .test_support import ensure_localized_site_roots


class LocalizedPairAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_localized_site_roots()
        call_command("import_portfolio", verbosity=0)

    def setUp(self):
        call_command("configure_agent_account", verbosity=0)
        user = get_user_model().objects.get(username="portfolio-agent")
        _token, token = APIToken.create_token(user=user, name="pair test")
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        self.root_id = Site.objects.get(is_default_site=True).root_page_id

    def payload(self, stable_id="pair-test"):
        return {
            "type": "portfolio.BlogIndexPage",
            "stable_id": stable_id,
            "it": {"parent_id": self.root_id, "title": "Indice IT", "slug": f"{stable_id}-it"},
            "en": {"parent_id": self.root_id, "title": "Index EN", "slug": f"{stable_id}-en"},
        }

    def blog_post_parents(self, stable_id="blog"):
        root = Site.objects.get(is_default_site=True).root_page
        parents = {}
        for code in ("it", "en"):
            locale = Locale.objects.get(language_code=code)
            parent = BlogIndexPage.objects.filter(locale=locale, stable_id=stable_id).first()
            if parent is None:
                parent = root.add_child(
                    instance=BlogIndexPage(
                        locale=locale,
                        stable_id=stable_id,
                        title=f"Blog {code.upper()}",
                        slug=f"{stable_id}-{code}",
                    )
                )
            parents[code] = parent
        return parents

    def blog_post_payload(self, stable_id="post-test", parent_stable_id="blog"):
        self.blog_post_parents(parent_stable_id)
        return {
            "type": "portfolio.BlogPostPage",
            "stable_id": stable_id,
            "parent_stable_id": parent_stable_id,
            "it": {
                "title": "Articolo IT",
                "slug": f"{stable_id}-it",
                "excerpt": "Estratto",
                "body": "Corpo",
            },
            "en": {
                "title": "Article EN",
                "slug": f"{stable_id}-en",
                "excerpt": "Excerpt",
                "body": "Body",
            },
        }

    def project_payload(self, stable_id="project-test", parent_ids=None):
        values = {
            "title": "Project",
            "slug": stable_id,
            "eyebrow": "Eyebrow",
            "detail_eyebrow": "Detail",
            "cta_label": "View",
            "question": "Question",
            "supporting_text": "Support",
            "what_i_worked_on": "Work",
            "future_improvement": "Future",
            "narrative": {"summary": "Summary"},
            "metadata": {"label": "Metadata"},
            "origin": ProjectPage.Origin.ITS_TRAINING,
            "visual_variant": ProjectPage.VisualVariant.STUDIO_PINK,
        }
        return {
            "type": "portfolio.ProjectPage",
            "stable_id": stable_id,
            "it": {
                **values,
                "slug": f"{stable_id}-it",
                "parent_id": (parent_ids or {}).get("it", self.root_id),
            },
            "en": {
                **values,
                "slug": f"{stable_id}-en",
                "parent_id": (parent_ids or {}).get("en", self.root_id),
            },
        }

    def featured_image(self):
        image_data = BytesIO()
        PILImage.new("RGB", (2, 2), color="white").save(image_data, format="PNG")
        image = get_image_model().objects.create(
            title="Localized pair image",
            file=SimpleUploadedFile(
                "localized-pair.png", image_data.getvalue(), content_type="image/png"
            ),
        )
        self.addCleanup(lambda: image.file.delete(save=False))
        return image

    def test_project_rejects_blog_index_parent_atomically(self):
        parents = self.blog_post_parents("project-parent")
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(self.project_payload("invalid-project", {
                code: parent.id for code, parent in parents.items()
            })),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("parent", response.json()["detail"])
        self.assertFalse(ProjectPage.objects.filter(stable_id="invalid-project").exists())

    def test_project_pair_under_site_roots_remains_valid(self):
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(self.project_payload()),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(ProjectPage.objects.filter(stable_id="project-test").count(), 2)

    def test_pair_creation_is_atomic_and_shares_translation_identity(self):
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(self.payload()),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 201, response.content)
        pages = BlogIndexPage.objects.filter(stable_id="pair-test").order_by(
            "locale__language_code"
        )
        self.assertEqual(pages.count(), 2)
        self.assertEqual({page.locale.language_code for page in pages}, {"it", "en"})
        self.assertEqual({page.translation_key for page in pages}, {pages[0].translation_key})
        self.assertTrue(all(not page.live for page in pages))

    def test_invalid_locale_shape_duplicate_and_second_locale_failure_are_rejected(self):
        missing_en = self.payload()
        del missing_en["en"]
        self.assertEqual(
            self.client.post(
                "/api/v3/localized-pairs/",
                data=json.dumps(missing_en),
                content_type="application/json",
                **self.auth,
            ).status_code,
            422,
        )
        failed = self.payload("rollback-test")
        failed["en"]["parent_id"] = 999999999
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(failed),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(BlogIndexPage.objects.filter(stable_id="rollback-test").exists())

        created = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(self.payload("duplicate-test")),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(created.status_code, 201, created.content)
        duplicate = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(self.payload("duplicate-test")),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.content)
        self.assertEqual(BlogIndexPage.objects.filter(stable_id="duplicate-test").count(), 2)

    def test_blog_post_resolves_localized_parent_by_stable_identity(self):
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(self.blog_post_payload()),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 201, response.content)
        pages = BlogPostPage.objects.filter(stable_id="post-test").select_related("locale")
        self.assertEqual(pages.count(), 2)
        for page in pages:
            self.assertEqual(page.get_parent().specific_class, BlogIndexPage)
            self.assertEqual(page.get_parent().specific.stable_id, "blog")
            self.assertEqual(page.get_parent().locale_id, page.locale_id)
        self.assertEqual(
            {page.translation_key for page in pages},
            {next(iter(pages)).translation_key},
        )

    def test_blog_post_missing_stable_parent_is_actionable_and_atomic(self):
        payload = self.blog_post_payload("missing-parent")
        payload["parent_stable_id"] = "missing-blog"
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("parent_stable_id", response.json()["detail"])
        self.assertFalse(BlogPostPage.objects.filter(stable_id="missing-parent").exists())

    def test_blog_post_rejects_numeric_parent_ids(self):
        payload = self.blog_post_payload("numeric-parent")
        payload["it"]["parent_id"] = self.root_id
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported fields", response.json()["detail"])

    def test_blog_post_resolves_featured_image_id(self):
        image = self.featured_image()
        payload = self.blog_post_payload("featured-image")
        payload["it"]["featured_image"] = image.id
        payload["en"]["featured_image"] = image.id
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            set(BlogPostPage.objects.filter(stable_id="featured-image").values_list(
                "featured_image_id", flat=True
            )),
            {image.id},
        )

    def test_featured_image_validation_is_atomic_and_rejects_unsupported_use(self):
        missing = self.blog_post_payload("missing-image")
        missing["it"]["featured_image"] = 999999999
        missing["en"]["featured_image"] = 999999999
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(missing),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("featured_image", response.json()["detail"])
        self.assertFalse(BlogPostPage.objects.filter(stable_id="missing-image").exists())

        malformed = self.blog_post_payload("malformed-image")
        malformed["it"]["featured_image"] = {"id": 1}
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(malformed),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(BlogPostPage.objects.filter(stable_id="malformed-image").exists())

        unsupported = self.payload("unsupported-image")
        unsupported["it"]["featured_image"] = 1
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(unsupported),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("only supported for BlogPostPage", response.json()["detail"])
        self.assertFalse(BlogIndexPage.objects.filter(stable_id="unsupported-image").exists())

        image = self.featured_image()
        rollback = self.blog_post_payload("rollback-image")
        rollback["it"]["featured_image"] = image.id
        rollback["en"]["featured_image"] = 999999999
        response = self.client.post(
            "/api/v3/localized-pairs/",
            data=json.dumps(rollback),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertFalse(BlogPostPage.objects.filter(stable_id="rollback-image").exists())


class LocalizedStableIDConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("stable-id concurrency regression requires PostgreSQL")
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), apps.get_models()):
                cursor.execute(sql)
        Locale.objects.get_or_create(id=1, defaults={"language_code": "en"})
        self.root = Site.objects.get(is_default_site=True).root_page
        self.locale = Locale.objects.get(pk=1)

    def test_concurrent_same_locale_stable_id_has_one_commit(self):
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        lock = threading.Lock()
        pages = [
            self.root.add_child(
                instance=BlogIndexPage(
                    locale=self.locale,
                    stable_id=f"concurrent-source-{suffix}",
                    title=f"Concurrent {suffix}",
                    slug=f"concurrent-source-{suffix}",
                )
            )
            for suffix in ("a", "b")
        ]

        def update_page(page_id: int) -> None:
            close_old_connections()
            try:
                with transaction.atomic():
                    barrier.wait(timeout=10)
                    page = BlogIndexPage.objects.get(pk=page_id)
                    page.stable_id = "concurrent-stable-id"
                    page.save(clean=False)
                result = "committed"
            except (IntegrityError, threading.BrokenBarrierError):
                result = "rejected"
            finally:
                close_old_connections()
            with lock:
                outcomes.append(result)

        threads = [threading.Thread(target=update_page, args=(page.id,)) for page in pages]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        self.assertEqual(sorted(outcomes), ["committed", "rejected"])
        self.assertEqual(
            BlogIndexPage.objects.filter(
                locale=self.locale, stable_id="concurrent-stable-id"
            ).count(),
            1,
        )
