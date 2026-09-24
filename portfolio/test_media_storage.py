from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.utils.functional import empty
from wagtail.images.models import Image

from .tests import VALID_PNG


class ProductionMediaStorageTests(SimpleTestCase):
    @override_settings(
        DEBUG=False,
        STORAGES={
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    "bucket_name": "portfolio-media",
                    "custom_domain": "media.example.test",
                    "querystring_auth": False,
                },
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        },
    )
    def test_wagtail_upload_uses_storage_url_without_debug_media_serving(self):
        default_storage._wrapped = empty
        self.addCleanup(setattr, default_storage, "_wrapped", empty)

        with patch("storages.backends.s3.S3Storage._save", return_value="images/smoke.png"):
            image = Image(title="Production smoke image", collection_id=1)
            image.file.save(
                "smoke.png",
                SimpleUploadedFile("smoke.png", VALID_PNG, content_type="image/png"),
                save=False,
            )

        self.assertEqual(image.file.storage.__class__.__name__, "S3Storage")
        self.assertEqual(image.file.url, "https://media.example.test/images/smoke.png")
