from django.test import TestCase


class WagtailBootstrapTests(TestCase):
    def test_public_root_and_admin_login_are_available(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
