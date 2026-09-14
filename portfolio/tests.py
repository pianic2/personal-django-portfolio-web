import os
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from wagtail.images import get_image_model

from portfolio.settings import database_config


class WagtailBootstrapTests(TestCase):
    def test_public_root_and_admin_login_are_available(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_only_explicit_origin_receives_cors_header(self):
        allowed = self.client.options("/", HTTP_ORIGIN="https://pianic2.github.io")
        denied = self.client.options("/", HTTP_ORIGIN="https://untrusted.example")

        self.assertEqual(allowed.headers["access-control-allow-origin"], "https://pianic2.github.io")
        self.assertNotIn("access-control-allow-origin", denied.headers)

    def test_postgresql_url_uses_postgresql_backend(self):
        with patch.dict(
            os.environ,
            {"DJANGO_DATABASE_URL": "postgresql://portfolio:password@db.example:5433/portfolio"},
        ):
            config = database_config()

        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["HOST"], "db.example")
        self.assertEqual(config["PORT"], 5433)

    def test_wagtail_image_uses_configured_media_storage(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                image = get_image_model().objects.create(
                    title="Smoke image",
                    file=SimpleUploadedFile(
                        "pixel.gif",
                        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
                        content_type="image/gif",
                    ),
                )
                self.assertTrue(image.file.storage.exists(image.file.name))
