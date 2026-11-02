#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
DEBUG=1 .venv/bin/python manage.py migrate --noinput
DEBUG=1 .venv/bin/python manage.py check
