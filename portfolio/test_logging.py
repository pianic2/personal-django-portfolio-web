import logging.config
import sys
import types

from django.test import Client, override_settings
from django.urls import path

from portfolio import settings


def _server_error(request):
    raise RuntimeError("probe failure")


def test_production_500_logs_to_stderr_without_request_secrets(capsys):
    urlconf = types.ModuleType("portfolio.test_logging_urls")
    urlconf.urlpatterns = [path("probe/", _server_error)]
    sys.modules[urlconf.__name__] = urlconf
    logging.config.dictConfig(settings.LOGGING)

    with override_settings(ROOT_URLCONF=urlconf.__name__, DEBUG=False, SECURE_SSL_REDIRECT=False):
        response = Client(HTTP_HOST="testserver", raise_request_exception=False).get(
            "/probe/",
            data={"secret_body": "do-not-log"},
            HTTP_AUTHORIZATION="Bearer do-not-log",
        )

    assert response.status_code == 500
    stderr = capsys.readouterr().err
    assert "Internal Server Error: /probe/" in stderr
    assert "do-not-log" not in stderr
