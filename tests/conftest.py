from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Ensure subprocess calls (e.g. integration tests) can also import the package.
# Needed on macOS where .pth files in .venv/site-packages inherit UF_HIDDEN and
# are skipped by Python's site module, so editable-install path injection fails.
_existing = os.environ.get("PYTHONPATH", "")
if str(SRC) not in _existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = str(SRC) + (os.pathsep + _existing if _existing else "")
