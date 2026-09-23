import tempfile

from django.conf import settings
from django.core.management import call_command
from django.test import Client, SimpleTestCase, override_settings


class ProductionStaticContractTests(SimpleTestCase):
    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_wagtail_admin_static_asset_is_served(self):
        self.assertEqual(
            settings.STORAGES["staticfiles"]["BACKEND"],
            "whitenoise.storage.CompressedManifestStaticFilesStorage",
        )
        self.assertIn("whitenoise.middleware.WhiteNoiseMiddleware", settings.MIDDLEWARE)

        with tempfile.TemporaryDirectory() as static_root:
            with override_settings(STATIC_ROOT=static_root):
                call_command("collectstatic", interactive=False, verbosity=0)
                response = Client(HTTP_HOST="testserver").get("/static/wagtailadmin/js/core.js")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content))
