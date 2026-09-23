from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

CONTACT_URL = "/api/contact/"
VALID_PAYLOAD = {
    "name": "Niccolò Piazzi",
    "email": "niccolo@example.com",
    "message": "A message that is long enough.",
    "locale": "en",
}


@override_settings(
    CONTACT_RECIPIENT_EMAIL="owner@example.com",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CORS_ALLOWED_ORIGINS=["http://localhost:5173", "https://pianic2.github.io"],
)
class ContactEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @patch("portfolio.contact.send_mail", return_value=1)
    def test_valid_contact_is_delivered_without_forwarding_locale(self, send_mail):
        response = self.client.post(CONTACT_URL, VALID_PAYLOAD, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        send_mail.assert_called_once()
        self.assertEqual(send_mail.call_args.kwargs["recipient_list"], ["owner@example.com"])
        self.assertNotIn("locale", send_mail.call_args.kwargs["message"])

    @patch("portfolio.contact.send_mail")
    def test_validation_returns_stable_field_errors(self, send_mail):
        response = self.client.post(
            CONTACT_URL,
            {"name": " ", "email": "not-an-email", "message": "too short"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")
        self.assertEqual(set(response.json()["errors"]), {"name", "email", "message"})
        send_mail.assert_not_called()

    @patch("portfolio.contact.send_mail")
    def test_oversize_payload_is_rejected_before_delivery(self, send_mail):
        response = self.client.post(
            CONTACT_URL,
            {"name": "n" * 81, "email": "a" * 245 + "@example.com", "message": "m" * 2001},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "validation_error")
        self.assertEqual(set(response.json()["errors"]), {"name", "email", "message"})
        send_mail.assert_not_called()

    @patch("portfolio.contact.send_mail", return_value=1)
    def test_duplicate_message_is_throttled(self, send_mail):
        first_response = self.client.post(CONTACT_URL, VALID_PAYLOAD, format="json")
        self.assertEqual(first_response.status_code, 200)

        response = self.client.post(CONTACT_URL, VALID_PAYLOAD, format="json")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "throttled")
        self.assertEqual(send_mail.call_count, 1)

    @patch("portfolio.contact.send_mail", return_value=1)
    def test_ip_rate_limit_is_applied(self, send_mail):
        for index in range(3):
            payload = {**VALID_PAYLOAD, "message": f"A distinct message number {index:02d}."}
            self.assertEqual(self.client.post(CONTACT_URL, payload, format="json").status_code, 200)

        response = self.client.post(
            CONTACT_URL,
            {**VALID_PAYLOAD, "message": "A distinct message number 03."},
            format="json",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["code"], "throttled")
        self.assertEqual(send_mail.call_count, 3)

    @override_settings(NUM_PROXIES=1)
    @patch("portfolio.contact.send_mail", return_value=1)
    def test_proxy_clients_have_independent_rate_buckets(self, send_mail):
        for client_ip in ("203.0.113.10", "203.0.113.11"):
            for index in range(3):
                payload = {
                    **VALID_PAYLOAD,
                    "message": f"Proxy client {client_ip} message {index:02d}.",
                }
                response = self.client.post(
                    CONTACT_URL,
                    payload,
                    format="json",
                    REMOTE_ADDR="10.0.0.5",
                    HTTP_X_FORWARDED_FOR=f"10.0.0.5, {client_ip}",
                )
                self.assertEqual(response.status_code, 200)

        self.assertEqual(send_mail.call_count, 6)

    @patch("portfolio.contact.send_mail", return_value=1)
    def test_configured_cors_origin_is_allowed(self, send_mail):
        response = self.client.options(
            CONTACT_URL,
            HTTP_ORIGIN="https://pianic2.github.io",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "https://pianic2.github.io")

    @patch("portfolio.contact.send_mail", side_effect=RuntimeError("provider unavailable"))
    def test_delivery_failure_is_stable_and_does_not_expose_provider_error(self, send_mail):
        response = self.client.post(CONTACT_URL, VALID_PAYLOAD, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"code": "delivery_failed", "detail": "The message could not be delivered."},
        )
        self.assertNotIn("provider unavailable", response.content.decode())
