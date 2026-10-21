"""Pytest configuration ensuring src/ layout is in sys.path."""

import sys
from pathlib import Path

# Add src to sys.path so toonshorts is importable directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure plugins are discovered
try:
    import toonshorts.plugins
except Exception:
    pass
