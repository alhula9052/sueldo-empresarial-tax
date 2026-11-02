"""WSGI file to select in PythonAnywhere's Web tab after running setup."""

from pathlib import Path
import os
import sys

# Default for the distribution ZIP extracted in the account's home directory.
ROOT = Path(os.getenv("NEXO_ROOT", str(Path.home() / "nexo"))).resolve()
sys.path.insert(0, str(ROOT))

from deploy.runtime import runtime_environment  # noqa: E402

os.environ.update(runtime_environment(ROOT))

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
