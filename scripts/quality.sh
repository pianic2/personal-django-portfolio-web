#!/usr/bin/env bash

set -euo pipefail

uv run ruff check .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest -q
