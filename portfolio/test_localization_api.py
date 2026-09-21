import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from wagtail.models import APIToken, Site

from .models import BlogIndexPage


class LocalizedPairAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
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
