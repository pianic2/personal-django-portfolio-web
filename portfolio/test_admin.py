from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    BlogIndexPage,
    BlogPostPage,
    Capability,
    ProfilePage,
    ProjectPage,
)


class AdminBrandingAndOwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )

    def setUp(self):
        self.assertTrue(self.client.login(username="admin", password="test-password"))

    def test_django_admin_uses_portfolio_identity_and_favicon(self):
        response = self.client.get("/django-admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, settings.ADMIN_SITE_HEADER)
        self.assertContains(response, "portfolio/portfolio-mark.")
        self.assertContains(response, ".svg")

    def test_wagtail_admin_uses_portfolio_identity_and_favicon(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, settings.WAGTAIL_SITE_NAME)
        self.assertContains(response, "portfolio/portfolio-mark.")
        self.assertContains(response, ".svg")

    def test_django_admin_registers_only_standalone_capability_data(self):
        self.assertIn(Capability, admin.site._registry)
        for page_model in (ProfilePage, ProjectPage, BlogIndexPage, BlogPostPage):
            self.assertNotIn(page_model, admin.site._registry)
