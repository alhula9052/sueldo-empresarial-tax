#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DEBUG="${DEBUG:-1}"
exec .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
