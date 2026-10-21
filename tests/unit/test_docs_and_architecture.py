"""Tests verifying file headers, CODEMAP freshness, FEATURES completeness, and architecture isolation."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_documentation_integrity():
    """Fails if any source file lacks a valid header, CODEMAP is stale, or FEATURES.md is incomplete."""
    cmd = [sys.executable, str(PROJECT_ROOT / "tools" / "update_docs.py"), "--check"]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert res.returncode == 0, f"update_docs.py --check failed:\n{res.stdout}\n{res.stderr}"


def test_architecture_rules():
    """Fails if core imports plugins, plugins violate boundaries, or secrets are exposed."""
    cmd = [sys.executable, str(PROJECT_ROOT / "tools" / "check_architecture.py")]
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    assert res.returncode == 0, f"check_architecture.py failed:\n{res.stdout}\n{res.stderr}"
