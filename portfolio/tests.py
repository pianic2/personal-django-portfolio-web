import base64

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from wagtail.images.models import Image

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
