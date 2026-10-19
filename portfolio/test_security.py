import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.models import APIToken


class APITokenAdminBoundaryTests(TestCase):
    """Wagtail API tokens authenticate the API only, never the admin surfaces."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_superuser(
            username="token-owner",
            email="token-owner@example.com",
            password="test-password",
        )

    def setUp(self):
        _token, token = APIToken.create_token(user=self.owner, name="admin-capable token")
        self.authorization = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_bearer_token_does_not_open_django_admin(self):
        response = self.client.get("/django-admin/", **self.authorization)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/django-admin/login/"))

    def test_bearer_token_does_not_open_wagtail_admin(self):
        response = self.client.get("/admin/", **self.authorization)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/admin/login/"))

    def test_bearer_token_still_authenticates_the_api(self):
        response = self.client.get("/api/v3/whoami/", **self.authorization)

        self.assertEqual(response.status_code, 200, response.content)


@pytest.mark.parametrize(
    "password",
    ["a", "12345678", "password", "token-owner-2026"],
)
def test_weak_admin_passwords_are_rejected(password):
    user = get_user_model()(username="token-owner", email="token-owner@example.com")

    with pytest.raises(ValidationError):
        validate_password(password, user)
    form = SetPasswordForm(user, {"new_password1": password, "new_password2": password})
    assert not form.is_valid()


def test_strong_admin_password_is_accepted():
    user = get_user_model()(username="token-owner", email="token-owner@example.com")

    validate_password("correct-Horse-battery-staple-91", user)
