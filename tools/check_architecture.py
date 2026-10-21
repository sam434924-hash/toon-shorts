"""
Purpose: Enforce architecture boundaries, plugin isolation, and security rules.
Inputs: Source code tree under src/toonshorts/.
Outputs: Architectural validation status and process exit code.
Depends on: ast, os, pathlib, sys
Used by: tests.unit.test_docs_and_architecture, tools.install_hooks
Config keys: None
Tests: tests/unit/test_docs_and_architecture.py
"""

import ast
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "toonshorts"
CORE_DIR = SRC_DIR / "core"
PLUGINS_DIR = SRC_DIR / "plugins"


def check_core_imports() -> list[str]:
    """Ensures core/ never imports plugins/."""
    violations = []
    if not CORE_DIR.exists():
        return [f"Core directory not found at {CORE_DIR}"]

    for py_file in CORE_DIR.glob("**/*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as e:
            violations.append(f"Failed to parse {py_file}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "plugins" in alias.name:
                        violations.append(
                            f"[CORE RULE VIOLATION] {py_file.name}:{node.lineno} imports '{alias.name}'. Core must never import plugins."
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "plugins" in mod:
                    violations.append(
                        f"[CORE RULE VIOLATION] {py_file.name}:{node.lineno} imports from '{mod}'. Core must never import plugins."
                    )
    return violations


def check_plugin_rules() -> list[str]:
    """Ensures plugins only import core, read keys only from config, and never print keys."""
    violations = []
    if not PLUGINS_DIR.exists():
        return [f"Plugins directory not found at {PLUGINS_DIR}"]

    for py_file in PLUGINS_DIR.glob("**/*.py"):
        if py_file.name.startswith("__"):
            continue
        plugin_type = py_file.parent.name  # llm, voice, render, motion

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as e:
            violations.append(f"Failed to parse {py_file}: {e}")
            continue

        for node in ast.walk(tree):
            # Check imports: cannot import sibling plugin folders
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for sibling in ["llm", "voice", "render", "motion"]:
                        if sibling != plugin_type and f"plugins.{sibling}" in alias.name:
                            violations.append(
                                f"[PLUGIN RULE VIOLATION] {py_file.name}:{node.lineno} imports sibling plugin '{alias.name}'."
                            )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for sibling in ["llm", "voice", "render", "motion"]:
                    if sibling != plugin_type and f"plugins.{sibling}" in mod:
                        violations.append(
                            f"[PLUGIN RULE VIOLATION] {py_file.name}:{node.lineno} imports from sibling plugin '{mod}'."
                        )

            # Check: no print of keys/secrets
            if isinstance(node, ast.Call):
                func = getattr(node.func, "id", None)
                if func == "print":
                    for arg in node.args:
                        arg_str = ast.unparse(arg).lower() if hasattr(ast, "unparse") else ""
                        if any(k in arg_str for k in ["api_key", "secret", "token", "password"]):
                            violations.append(
                                f"[SECURITY VIOLATION] {py_file.name}:{node.lineno} prints sensitive variable: {arg_str}"
                            )

            # Check: plugins must read keys from config only, not direct os.getenv for API keys
            if isinstance(node, ast.Call):
                func_str = ""
                if isinstance(node.func, ast.Attribute) and node.func.attr in ("getenv", "environ"):
                    violations.append(
                        f"[SECURITY NOTICE] {py_file.name}:{node.lineno} reads environment directly. Plugins must read keys from config only."
                    )
    return violations


def main() -> int:
    core_violations = check_core_imports()
    plugin_violations = check_plugin_rules()
    all_violations = core_violations + plugin_violations

    if all_violations:
        print("\n=== Architecture Violations Detected ===")
        for v in all_violations:
            print(f" - {v}")
        print("========================================\n")
        return 1

    print("Architecture check passed: All boundaries, plugin isolation, and security rules verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
