"""The public contact endpoint and its server-side delivery adapter."""

from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import serializers, status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    message = serializers.CharField(min_length=20, max_length=2000, trim_whitespace=True)
    locale = serializers.ChoiceField(choices=("it", "en"), required=False, write_only=True)


class ContactRateThrottle(SimpleRateThrottle):
    scope = "contact"

    def get_cache_key(self, request, view):
        address = self.get_ident(request) or "unknown"
        return f"contact-rate:{hashlib.sha256(address.encode()).hexdigest()}"


class DuplicateContactThrottle(SimpleRateThrottle):
    """Reject the same normalized message from the same client for a short period."""

    scope = "contact_duplicate"

    def get_cache_key(self, request, view):
        values = getattr(request, "_contact_values", request.data)
        address = self.get_ident(request) or "unknown"
        fingerprint = "\x00".join(
            [
                address,
                str(values.get("name", "")).strip(),
                str(values.get("email", "")).strip().lower(),
                str(values.get("message", "")).strip(),
            ]
        )
        return f"contact-duplicate:{hashlib.sha256(fingerprint.encode()).hexdigest()}"


class ContactView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ContactRateThrottle, DuplicateContactThrottle]

    def get_throttles(self):
        # Validation must not consume the abuse budget for malformed requests.
        return []

    def handle_exception(self, exc):
        if isinstance(exc, Throttled):
            response = Response(
                {"code": "throttled", "detail": "Too many contact requests. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            if exc.wait:
                response["Retry-After"] = str(exc.wait)
            return response
        return super().handle_exception(exc)

    def check_contact_throttles(self, request):
        for throttle in (throttle_class() for throttle_class in self.throttle_classes):
            if not throttle.allow_request(request, self):
                self.throttled(request, throttle.wait())

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"code": "validation_error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        values = serializer.validated_data
        request._contact_values = values
        self.check_contact_throttles(request)
        if not settings.CONTACT_RECIPIENT_EMAIL:
            return Response(
                {"code": "delivery_failed", "detail": "The message could not be delivered."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            send_mail(
                subject="New portfolio contact message",
                message=f"Name: {values['name']}\nEmail: {values['email']}\n\n{values['message']}",
                from_email=getattr(settings, "CONTACT_FROM_EMAIL", None),
                recipient_list=[settings.CONTACT_RECIPIENT_EMAIL],
                auth_user=None,
                auth_password=None,
                fail_silently=False,
            )
        except Exception:
            return Response(
                {"code": "delivery_failed", "detail": "The message could not be delivered."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({"success": True}, status=status.HTTP_200_OK)
