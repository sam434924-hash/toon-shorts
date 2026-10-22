"""
Purpose: Scan module headers, verify imports, check features, and build CODEMAP.md.
Inputs: Source code files under src/toonshorts/ and docs/ files.
Outputs: Regenerated docs/CODEMAP.md and validation check results.
Depends on: ast, os, pathlib, re, sys
Used by: tests.unit.test_docs_and_architecture, tools.install_hooks
Config keys: None
Tests: tests/unit/test_docs_and_architecture.py
"""

import ast
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "toonshorts"
DOCS_DIR = PROJECT_ROOT / "docs"
CODEMAP_FILE = DOCS_DIR / "CODEMAP.md"
FEATURES_FILE = DOCS_DIR / "FEATURES.md"

REQUIRED_FIELDS = ["Purpose", "Inputs", "Outputs", "Depends on", "Used by", "Config keys", "Tests"]


def parse_header(file_path: Path) -> dict:
    """Parses and validates the file header docstring."""
    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    docstring_lines = []
    in_doc = False
    for line in lines[:25]:
        stripped = line.strip()
        if not in_doc:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_doc = True
                docstring_lines.append(stripped)
                if (stripped.count('"""') == 2 or stripped.count("'''") == 2) and len(stripped) > 3:
                    break
        else:
            docstring_lines.append(stripped)
            if '"""' in stripped or "'''" in stripped:
                break

    if not docstring_lines:
        return {"error": f"{file_path.name}: No header docstring found"}

    if len(docstring_lines) > 10:
        return {"error": f"{file_path.name}: Header exceeds 10 lines ({len(docstring_lines)} lines)"}

    parsed = {}
    for line in docstring_lines:
        for field in REQUIRED_FIELDS:
            prefix = f"{field}:"
            if line.startswith(prefix):
                parsed[field] = line[len(prefix):].strip()

    missing = [f for f in REQUIRED_FIELDS if f not in parsed]
    if missing:
        return {"error": f"{file_path.name}: Header missing required fields: {', '.join(missing)}"}

    return parsed


def normalize_mod_name(path: Path) -> str:
    """Computes a normalized dotted module name relative to src/toonshorts."""
    rel = path.relative_to(SRC_DIR).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else "__init__"


def extract_real_imports(py_file: Path) -> set[str]:
    """Extracts internal toonshorts modules imported by this file."""
    imports = set()
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except Exception:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "toonshorts" in alias.name:
                    mod = alias.name.replace("toonshorts.", "").strip()
                    if mod != "toonshorts":
                        imports.add(mod)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level > 0:
                cur = py_file.parent
                for _ in range(node.level - 1):
                    cur = cur.parent
                try:
                    rel_base = cur.relative_to(SRC_DIR).as_posix().replace("/", ".")
                except ValueError:
                    rel_base = ""
                full_base = f"{rel_base}.{base}".strip(".") if rel_base else base
                if full_base:
                    imports.add(full_base)
                for alias in node.names:
                    target = f"{full_base}.{alias.name}".strip(".") if full_base else alias.name
                    imports.add(target)
            elif "toonshorts" in base:
                mod = base.replace("toonshorts.", "").strip()
                if mod != "toonshorts":
                    imports.add(mod)
                for alias in node.names:
                    target = f"{mod}.{alias.name}".strip(".") if mod else alias.name
                    imports.add(target)

    return imports


def compute_used_by_map() -> dict[str, set[str]]:
    """Builds an exact map of target_module -> set of importer modules."""
    py_files = [p for p in SRC_DIR.glob("**/*.py") if not p.name.startswith("__pycache__")]
    file_map = {normalize_mod_name(p): p for p in py_files}

    used_by: dict[str, set[str]] = {mod: set() for mod in file_map}

    for py_file in py_files:
        importer = normalize_mod_name(py_file)
        real_imps = extract_real_imports(py_file)

        for imp in real_imps:
            matched_mod = None
            if imp in file_map:
                matched_mod = imp
            else:
                candidates = [m for m in file_map if imp == m or imp.startswith(m + ".")]
                if candidates:
                    matched_mod = max(candidates, key=len)

            if matched_mod and matched_mod != importer:
                used_by[matched_mod].add(importer)

    return used_by


def update_file_used_by(py_file: Path, actual_importers: set[str]):
    """Rewrites the Used by line in the file header to accurately reflect real imports."""
    content = py_file.read_text(encoding="utf-8")
    sorted_importers = sorted(list(actual_importers))
    used_by_str = ", ".join(sorted_importers) if sorted_importers else "None"

    def replacer(match):
        return f"Used by: {used_by_str}"

    new_content = re.sub(r"Used by:\s*[^\n]+", replacer, content, count=1)
    if new_content != content:
        py_file.write_text(new_content, encoding="utf-8")


def discover_registered_plugins() -> dict[str, list[str]]:
    """Lists registered plugins discovered in plugins directory."""
    plugins_dir = SRC_DIR / "plugins"
    categories = ["llm", "voice", "render", "motion"]
    registry = {}
    for cat in categories:
        cat_dir = plugins_dir / cat
        plugins = []
        if cat_dir.is_dir():
            for item in sorted(cat_dir.iterdir()):
                if item.name.startswith("__") or item.name.startswith("."):
                    continue
                if item.is_file() and item.suffix == ".py":
                    plugins.append(item.stem)
                elif item.is_dir() and (item / "__init__.py").exists():
                    plugins.append(item.name)
        registry[cat] = plugins
    return registry


def generate_codemap() -> str:
    """Builds compact CODEMAP.md content from file headers and plugin registry."""
    lines = [
        "# Codebase Map",
        "",
        "> AUTO-GENERATED by `tools/update_docs.py`. Never edit by hand.",
        "",
        "## Core & Plugins Registry",
    ]

    plugins = discover_registered_plugins()
    for cat, items in plugins.items():
        lines.append(f"- **{cat.upper()}**: {', '.join(items)}")

    lines.append("")
    lines.append("## Module Index")

    py_files = sorted(
        [p for p in SRC_DIR.glob("**/*.py") if not p.name.startswith("__pycache__")],
        key=lambda p: str(p.relative_to(PROJECT_ROOT)).replace("\\", "/")
    )

    for py_file in py_files:
        rel_path = str(py_file.relative_to(PROJECT_ROOT)).replace("\\", "/")
        header = parse_header(py_file)
        if "error" in header:
            continue
        purpose = header.get("Purpose", "No description")
        depends = header.get("Depends on", "None")
        used = header.get("Used by", "None")
        lines.append(f"- `{rel_path}`: {purpose} | Depends: {depends} | Used by: {used}")

    lines.append("")
    return "\n".join(lines)


def check_features_file(plugins: dict[str, list[str]]) -> list[str]:
    """Verifies that all plugins and CLI commands are documented in docs/FEATURES.md."""
    violations = []
    if not FEATURES_FILE.exists():
        return ["docs/FEATURES.md does not exist."]

    features_text = FEATURES_FILE.read_text(encoding="utf-8")

    cli_commands = ["make"]
    for cmd in cli_commands:
        if cmd not in features_text:
            violations.append(f"docs/FEATURES.md is missing CLI command '{cmd}'")

    for cat, plugin_names in plugins.items():
        for name in plugin_names:
            if name not in features_text:
                violations.append(f"docs/FEATURES.md is missing {cat} plugin '{name}'")

    return violations


def main() -> int:
    check_mode = "--check" in sys.argv
    plugins = discover_registered_plugins()
    used_by_map = compute_used_by_map()
    violations = []

    py_files = [p for p in SRC_DIR.glob("**/*.py") if not p.name.startswith("__pycache__")]

    if not check_mode:
        for py_file in py_files:
            mod_name = normalize_mod_name(py_file)
            actual = used_by_map.get(mod_name, set())
            update_file_used_by(py_file, actual)

    for py_file in py_files:
        header = parse_header(py_file)
        if "error" in header:
            violations.append(header["error"])
        else:
            mod_name = normalize_mod_name(py_file)
            declared_used_by = {x.strip() for x in header["Used by"].split(",") if x.strip() and x.strip() != "None"}
            actual_used_by = used_by_map.get(mod_name, set())
            if declared_used_by != actual_used_by:
                missing = actual_used_by - declared_used_by
                extra = declared_used_by - actual_used_by
                if missing:
                    violations.append(f"{py_file.name}: 'Used by' missing: {', '.join(sorted(missing))}")
                if extra:
                    violations.append(f"{py_file.name}: 'Used by' has extra: {', '.join(sorted(extra))}")

    feat_violations = check_features_file(plugins)
    violations.extend(feat_violations)

    expected_codemap = generate_codemap()

    if check_mode:
        if not CODEMAP_FILE.exists():
            violations.append("docs/CODEMAP.md does not exist.")
        else:
            current_codemap = CODEMAP_FILE.read_text(encoding="utf-8")
            if current_codemap.strip() != expected_codemap.strip():
                violations.append("docs/CODEMAP.md is stale. Run 'python tools/update_docs.py' to regenerate.")
    else:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        CODEMAP_FILE.write_text(expected_codemap, encoding="utf-8")
        print(f"Updated {CODEMAP_FILE.relative_to(PROJECT_ROOT)}")

    if violations:
        print("\n=== Documentation Check Violations ===")
        for v in violations:
            print(f" - {v}")
        print("======================================\n")
        return 1

    print("All documentation checks passed: headers valid, Used-by consistent, CODEMAP up to date, FEATURES complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
