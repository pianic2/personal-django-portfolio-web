import json

from django.http import JsonResponse


class ImmutableStableIDMiddleware:
    """Reject API page updates that attempt to change a page identity."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "PATCH" and request.path.startswith("/api/v3/pages/"):
            try:
                payload = json.loads(request.body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = None
            if isinstance(payload, dict) and "stable_id" in payload:
                return JsonResponse(
                    {"detail": "stable_id is immutable after page creation."},
                    status=400,
                )
        return self.get_response(request)
