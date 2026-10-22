"""
Purpose: Automatic discovery and loading for all swappable plugin modules.
Inputs: File system paths of plugins directory.
Outputs: Executed module registrations in core registries.
Depends on: importlib, inspect, os, pathlib, pkgutil
Used by: None
Config keys: None
Tests: tests/unit/test_registry.py
"""

import importlib
from pathlib import Path


def discover_plugins():
    """Dynamically imports all plugin modules so their registration decorators execute."""
    plugins_dir = Path(__file__).resolve().parent
    subdirs = ["llm", "voice", "render", "motion"]

    for sub in subdirs:
        sub_path = plugins_dir / sub
        if not sub_path.is_dir():
            continue
        for item in sorted(sub_path.iterdir()):
            if item.name.startswith("__") or item.name.startswith("."):
                continue
            if item.is_file() and item.suffix == ".py":
                plugin_name = item.stem
            elif item.is_dir() and (item / "__init__.py").exists():
                plugin_name = item.name
            else:
                continue

            module_name = f"toonshorts.plugins.{sub}.{plugin_name}"
            try:
                importlib.import_module(module_name)
            except Exception as e:
                # Fallback relative import if running without top-level package install
                try:
                    importlib.import_module(f".{sub}.{plugin_name}", package=__name__)
                except Exception:
                    raise e


# Automatically discover plugins upon package import
discover_plugins()
