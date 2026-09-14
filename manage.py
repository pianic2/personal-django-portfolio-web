#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portfolio.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - exercised by installation evidence
        raise ImportError("Django is not installed. Run `uv sync --frozen` first.") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
