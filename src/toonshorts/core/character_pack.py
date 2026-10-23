"""
Purpose: 2D layered SVG character pack system with security validation and test staging.
Inputs: Character pack directory, manifest JSON, layered SVG markup, eye/mouth state requests.
Outputs: Validated CharacterPack instances, state-swapped SVG code, rendered preview frames.
Depends on: json, os, pathlib, re, typing, xml.etree.ElementTree, PIL, core.config
Used by: core.character2d, inventory
Config keys: None
Tests: tests/unit/test_character_pack.py, tests/unit/test_character2d.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import xml.etree.ElementTree as ET

from PIL import Image

from toonshorts.core import paths
from toonshorts.core.config import PROJECT_ROOT

# Standard directory for 2D character assets
CHARACTERS2D_DIR = paths.CHARACTERS_2D_DIR

# Security: strict character name regex: letters, digits, dash, underscore, max 32 chars
CHARACTER_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,32}$")

# Maximum permitted SVG file size (200 KB)
MAX_SVG_SIZE_BYTES = 200 * 1024

# Security: Strict allowlist of permissible SVG element tags
ALLOWED_SVG_ELEMENTS = frozenset({
    "svg",
    "g",
    "path",
    "circle",
    "ellipse",
    "rect",
    "polygon",
    "polyline",
    "line",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "clipPath",
    "style",
})

URL_PATTERN = re.compile(r"url\s*\(\s*([^)]*)\s*\)", re.IGNORECASE)
IMPORT_PATTERN = re.compile(r"@import\b", re.IGNORECASE)
JAVASCRIPT_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)
ENTITY_PATTERN = re.compile(r"<!ENTITY\b", re.IGNORECASE)
DOCTYPE_PATTERN = re.compile(r"<!DOCTYPE\b", re.IGNORECASE)


def validate_svg_security(svg_content: str) -> List[str]:
    """
    Validates SVG content against strict security allowlist:
    - Maximum size 200 KB
    - Allowed elements only: svg, g, path, circle, ellipse, rect, polygon, polyline, line, defs, linearGradient, radialGradient, stop, clipPath, style
    - Reject any on* attribute
    - Reject any href or url() that does not start with #
    - Reject style blocks using @import or external URLs
    - Reject javascript: values
    - Reject XML DOCTYPE and ENTITY declarations (XXE)
    """
    errors: List[str] = []

    # 1. Size constraint
    svg_bytes = len(svg_content.encode("utf-8"))
    if svg_bytes > MAX_SVG_SIZE_BYTES:
        errors.append(
            f"SVG file size {svg_bytes} bytes exceeds maximum limit of {MAX_SVG_SIZE_BYTES} bytes (200 KB)"
        )

    # 2. Reject DOCTYPE / ENTITY declarations
    if DOCTYPE_PATTERN.search(svg_content) or ENTITY_PATTERN.search(svg_content):
        errors.append("Security violation: DOCTYPE or ENTITY declarations are forbidden")

    # 3. Parse XML
    try:
        root = ET.fromstring(svg_content)
    except Exception as e:
        errors.append(f"Invalid XML/SVG syntax: {e}")
        return errors

    def check_url_reference(val: str, context: str) -> None:
        for match in URL_PATTERN.finditer(val):
            target = match.group(1).strip("'\" \t\r\n")
            if not target.startswith("#"):
                errors.append(f"Security violation: Disallowed url() reference in {context}: '{target}' (must start with '#')")

    # 4. Check all elements and attributes
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag not in ALLOWED_SVG_ELEMENTS:
            errors.append(f"Security violation: Disallowed SVG element '<{tag}>'")

        # Check style element contents
        if tag == "style":
            style_text = (elem.text or "") + (elem.tail or "")
            if IMPORT_PATTERN.search(style_text):
                errors.append("Security violation: Disallowed @import in style block")
            if JAVASCRIPT_PATTERN.search(style_text):
                errors.append("Security violation: Disallowed javascript: in style block")
            check_url_reference(style_text, "style block")

        # Check element attributes
        for attr_raw, val in elem.attrib.items():
            attr = attr_raw.split("}")[-1] if "}" in attr_raw else attr_raw
            attr_lower = attr.lower()
            val_str = str(val)

            # Reject any on* attribute
            if attr_lower.startswith("on"):
                errors.append(f"Security violation: Disallowed event handler attribute '{attr}'")

            # Reject javascript: values
            if JAVASCRIPT_PATTERN.search(val_str):
                errors.append(f"Security violation: Disallowed javascript: URI in attribute '{attr}'")

            # Reject any href that does not start with #
            if attr_lower in ("href", "xlink:href"):
                if not val_str.startswith("#"):
                    errors.append(f"Security violation: Disallowed href in '{attr}': '{val_str}' (must start with '#')")

            # Check url() references in attribute values
            check_url_reference(val_str, f"attribute '{attr}'")

            # Check style attribute
            if attr_lower == "style":
                if IMPORT_PATTERN.search(val_str):
                    errors.append("Security violation: Disallowed @import in style attribute")

    return errors


def validate_manifest_schema(manifest: Dict[str, Any]) -> List[str]:
    """Validates pack manifest dictionary against required character pack schema."""
    errors: List[str] = []
    if not isinstance(manifest, dict):
        return ["Manifest must be a JSON object / dict"]

    # id
    pack_id = manifest.get("id")
    if not pack_id or not isinstance(pack_id, str):
        errors.append("Manifest missing required string field 'id'")
    else:
        try:
            validate_pack_name(pack_id)
        except ValueError as e:
            errors.append(str(e))

    # kind
    kind = manifest.get("kind")
    if kind not in ("vector", "raster"):
        errors.append(f"Manifest field 'kind' must be 'vector' or 'raster', got '{kind}'")

    # viewBox
    viewBox = manifest.get("viewBox")
    if not viewBox or not isinstance(viewBox, str) or len(viewBox.split()) != 4:
        errors.append(f"Manifest missing or invalid string field 'viewBox' (expected 4 numbers, got '{viewBox}')")

    # layers
    layers = manifest.get("layers")
    if not layers or not isinstance(layers, (list, dict)):
        errors.append("Manifest missing required list or dict field 'layers'")

    # mouth_states
    mouth_states = manifest.get("mouth_states")
    if not mouth_states or not isinstance(mouth_states, list) or not all(isinstance(s, str) for s in mouth_states):
        errors.append("Manifest missing required non-empty string list 'mouth_states'")

    # eye_states
    eye_states = manifest.get("eye_states")
    if not eye_states or not isinstance(eye_states, list) or not all(isinstance(s, str) for s in eye_states):
        errors.append("Manifest missing required non-empty string list 'eye_states'")

    # anchors
    anchors = manifest.get("anchors")
    if not isinstance(anchors, dict):
        errors.append("Manifest missing required dict field 'anchors'")

    # safe_bounding_box
    safe_bb = manifest.get("safe_bounding_box")
    if not isinstance(safe_bb, (dict, list)):
        errors.append("Manifest missing required field 'safe_bounding_box'")

    # default_slot
    default_slot = manifest.get("default_slot")
    if default_slot not in ("left", "right"):
        errors.append(f"Manifest field 'default_slot' must be 'left' or 'right', got '{default_slot}'")

    # scale
    scale = manifest.get("scale")
    if scale is None or not isinstance(scale, (int, float)) or scale <= 0:
        errors.append(f"Manifest field 'scale' must be a positive number, got '{scale}'")

    # allowed_gestures
    allowed_gestures = manifest.get("allowed_gestures")
    if allowed_gestures is not None:
        if not isinstance(allowed_gestures, list) or not all(isinstance(g, str) for g in allowed_gestures):
            errors.append("Manifest field 'allowed_gestures' must be a list of strings")

    return errors


def validate_pack_name(name: str) -> str:
    """Validates character pack name against strict alphanumeric + dash/underscore, max 32 chars."""
    if not isinstance(name, str):
        raise ValueError(f"Character name must be a string, got {type(name).__name__}")
    if not CHARACTER_NAME_REGEX.match(name):
        raise ValueError(
            f"Invalid character pack name '{name}'. Names must be 1-32 chars containing only letters, numbers, '-', '_'"
        )
    return name


def ensure_path_inside_dir(target_path: Path, parent_dir: Path) -> Path:
    """Ensures target_path resolves strictly within parent_dir to prevent path traversal."""
    resolved_parent = parent_dir.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_parent)
    except ValueError:
        raise ValueError(f"Security error: path '{target_path}' escapes outside '{parent_dir}'")
    return resolved_target


class CharacterPack:
    """
    Modular 2D Layered SVG Character Pack.
    Supports swappable eye states and mouth states while preserving identical head and hair geometry.
    """

    def __init__(
        self,
        pack_id: str,
        name: str,
        folder: Path,
        svg_content: str,
        manifest: Dict[str, Any],
        svg_path: Path,
    ):
        self.pack_id = validate_pack_name(pack_id)
        self.name = manifest.get("name", pack_id)
        self.folder = folder
        self.raw_svg = svg_content
        self.manifest = manifest
        self.svg_path = svg_path

        self.kind: str = manifest.get("kind", "vector")
        self.viewBox: str = manifest.get("viewBox", "0 0 560 630")
        self.layers: Union[List[Any], Dict[str, Any]] = manifest.get("layers", [])
        self.eye_states: List[str] = list(
            manifest.get("eye_states", ["open", "blink", "screen_left", "screen_right"])
        )
        self.mouth_states: List[str] = list(
            manifest.get("mouth_states", ["closed", "slightly_open", "wide_open", "round_o"])
        )
        self.anchors: Dict[str, Any] = manifest.get("anchors", {})
        self.safe_bounding_box: Dict[str, Any] = manifest.get("safe_bounding_box", {})
        self.default_slot: str = manifest.get("default_slot", "left")
        self.scale: float = float(manifest.get("scale", 1.0))
        self.allowed_gestures: List[str] = list(manifest.get("allowed_gestures") or ["idle"])

        self.default_eyes: str = manifest.get("default_eyes", "open")
        self.default_mouth: str = manifest.get("default_mouth", "closed")

        self.active_eyes: str = self.default_eyes
        self.active_mouth: str = self.default_mouth

    def set_state(self, eyes: Optional[str] = None, mouth: Optional[str] = None) -> None:
        """Sets active eye and mouth states after validating against available states."""
        if eyes is not None:
            if eyes not in self.eye_states:
                raise ValueError(
                    f"Invalid eye state '{eyes}'. Available states: {self.eye_states}"
                )
            self.active_eyes = eyes

        if mouth is not None:
            if mouth not in self.mouth_states:
                raise ValueError(
                    f"Invalid mouth state '{mouth}'. Available states: {self.mouth_states}"
                )
            self.active_mouth = mouth

    def get_svg(self, eyes: Optional[str] = None, mouth: Optional[str] = None) -> str:
        """
        Returns complete, self-contained SVG markup configured with the requested eye and mouth states.
        """
        target_eye = eyes if eyes is not None else self.active_eyes
        target_mouth = mouth if mouth is not None else self.active_mouth

        if target_eye not in self.eye_states:
            raise ValueError(
                f"Invalid eye state '{target_eye}'. Available states: {self.eye_states}"
            )
        if target_mouth not in self.mouth_states:
            raise ValueError(
                f"Invalid mouth state '{target_mouth}'. Available states: {self.mouth_states}"
            )

        # Build dynamic CSS rules to show only the selected states
        css_rules = [
            "      .eye-state { display: none !important; }",
            "      .mouth-state { display: none !important; }",
            f"      #eyes-{target_eye} {{ display: inline !important; }}",
            f"      #mouth-{target_mouth} {{ display: inline !important; }}",
        ]
        css_block = "<style>\n" + "\n".join(css_rules) + "\n    </style>"

        if "<style>" in self.raw_svg and "</style>" in self.raw_svg:
            updated_svg = re.sub(
                r"<style>.*?</style>",
                css_block,
                self.raw_svg,
                count=1,
                flags=re.DOTALL,
            )
        else:
            # Insert style block into <defs> or right after opening <svg> tag
            if "<defs>" in self.raw_svg:
                updated_svg = self.raw_svg.replace(
                    "<defs>", f"<defs>\n    {css_block}", 1
                )
            else:
                updated_svg = re.sub(
                    r"(<svg[^>]*>)",
                    r"\1\n  <defs>\n  " + css_block + r"\n  </defs>",
                    self.raw_svg,
                    count=1,
                )

        return updated_svg

    def validate(self) -> List[str]:
        """
        Performs comprehensive security, integrity, and schema validation.
        Returns a list of error strings (empty list indicates a valid pack).
        """
        errors = []

        # 1. Manifest schema validation
        errors.extend(validate_manifest_schema(self.manifest))

        # 2. SVG security allowlist validation
        errors.extend(validate_svg_security(self.raw_svg))

        # 3. Required layer IDs for eye states
        for eye in self.eye_states:
            layer_id = f"eyes-{eye}"
            if f'id="{layer_id}"' not in self.raw_svg and f"id='{layer_id}'" not in self.raw_svg:
                errors.append(f"Missing required eye state layer: #{layer_id}")

        # 4. Required layer IDs for mouth states
        for mouth in self.mouth_states:
            layer_id = f"mouth-{mouth}"
            if f'id="{layer_id}"' not in self.raw_svg and f"id='{layer_id}'" not in self.raw_svg:
                errors.append(f"Missing required mouth state layer: #{layer_id}")

        # 5. Core structural layers defined in manifest
        if isinstance(self.layers, list):
            for layer in self.layers:
                if isinstance(layer, str):
                    if f'id="{layer}"' not in self.raw_svg and f"id='{layer}'" not in self.raw_svg:
                        errors.append(f"Missing required structural layer defined in manifest: #{layer}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serializes character pack metadata."""
        return {
            "id": self.pack_id,
            "name": self.name,
            "kind": self.kind,
            "type": "layered_svg",
            "folder": str(self.folder),
            "svg_file": str(self.svg_path.name),
            "viewBox": self.viewBox,
            "layers": self.layers,
            "eye_states": self.eye_states,
            "mouth_states": self.mouth_states,
            "anchors": self.anchors,
            "safe_bounding_box": self.safe_bounding_box,
            "default_slot": self.default_slot,
            "scale": self.scale,
            "allowed_gestures": self.allowed_gestures,
            "active_eyes": self.active_eyes,
            "active_mouth": self.active_mouth,
            "default_eyes": self.default_eyes,
            "default_mouth": self.default_mouth,
        }

    def render_png(
        self,
        output_path: Path,
        eyes: Optional[str] = None,
        mouth: Optional[str] = None,
        width: int = 560,
        height: int = 630,
    ) -> Path:
        """
        Renders the active or specified character state to a PNG file using Playwright.
        """
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)

        svg_code = self.get_svg(eyes=eyes, mouth=mouth)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{
    margin: 0;
    padding: 0;
    width: {width}px;
    height: {height}px;
    background: transparent;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  svg {{
    width: 100%;
    height: 100%;
  }}
</style>
</head>
<body>
{svg_code}
</body>
</html>"""

        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
            page.set_content(html_content)
            page.screenshot(path=str(out_p), omit_background=True)
            browser.close()

        return out_p


def load_character_pack(
    pack_id_or_path: Union[str, Path],
    base_dir: Optional[Path] = None,
) -> CharacterPack:
    """
    Safely loads and validates a 2D Character Pack from disk.
    Prevents path traversal, sanitizes XML/SVG contents, and verifies layer integrity.
    """
    root_dir = (base_dir or CHARACTERS2D_DIR).resolve()

    if isinstance(pack_id_or_path, Path) or ("/" in str(pack_id_or_path) or "\\" in str(pack_id_or_path)):
        pack_path = Path(pack_id_or_path).resolve()
        # Security: must stay inside root_dir if base_dir is explicitly given or standard
        ensure_path_inside_dir(pack_path, root_dir)
        if pack_path.name == "vector":
            pack_id = pack_path.parent.name
        else:
            pack_id = pack_path.name
    else:
        pack_id = validate_pack_name(str(pack_id_or_path))
        pack_path = (root_dir / pack_id).resolve()
        ensure_path_inside_dir(pack_path, root_dir)
        if (pack_path / "vector" / "manifest.json").is_file():
            pack_path = pack_path / "vector"

    if not pack_path.is_dir():
        raise FileNotFoundError(f"Character pack directory not found at '{pack_path}'")

    manifest_file = pack_path / "manifest.json"
    if not manifest_file.is_file():
        raise FileNotFoundError(f"Missing manifest.json in character pack at '{pack_path}'")

    ensure_path_inside_dir(manifest_file, pack_path)
    with open(manifest_file, "r", encoding="utf-8") as f:
        try:
            manifest = json.load(f)
        except Exception as e:
            raise ValueError(f"Malformed manifest.json in character pack: {e}")

    svg_file_name = manifest.get("svg_file", "character.svg")
    svg_file = pack_path / svg_file_name
    ensure_path_inside_dir(svg_file, pack_path)

    if not svg_file.is_file():
        raise FileNotFoundError(f"Character SVG file not found at '{svg_file}'")

    svg_content = svg_file.read_text(encoding="utf-8")

    name = manifest.get("name", pack_id)
    pack = CharacterPack(
        pack_id=pack_id,
        name=name,
        folder=pack_path,
        svg_content=svg_content,
        manifest=manifest,
        svg_path=svg_file,
    )

    validation_errors = pack.validate()
    if validation_errors:
        raise ValueError(
            f"Character pack '{pack_id}' failed validation: {'; '.join(validation_errors)}"
        )

    return pack


def create_character_staging(
    pack: CharacterPack,
    output_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """
    Generates test staging artifacts for a character pack:
    1. An interactive staging HTML workbench with state switcher, blink loop, and viseme test.
    2. A comprehensive 4x2 contact sheet PNG of the reference states.
    3. Individual PNG renders for each reference state.
    """
    target_dir = Path(output_dir or (pack.folder / "staging")).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    artifacts: Dict[str, Path] = {}

    # 1. Interactive Staging HTML workbench
    workbench_path = target_dir / "index.html"
    raw_svg_escaped = pack.get_svg(eyes=pack.default_eyes, mouth=pack.default_mouth)

    eye_buttons = "".join(
        f'<button class="btn eye-btn" data-eye="{eye}">{eye}</button>\n'
        for eye in pack.eye_states
    )
    mouth_buttons = "".join(
        f'<button class="btn mouth-btn" data-mouth="{mouth}">{mouth}</button>\n'
        for mouth in pack.mouth_states
    )

    html_workbench = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ToonShorts 2D Character Staging - {pack.name} ({pack.pack_id})</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0f172a;
    color: #f8fafc;
    margin: 0;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  h1 {{ margin-top: 0; font-size: 24px; color: #38bdf8; }}
  .container {{
    display: flex;
    gap: 32px;
    background: #1e293b;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    max-width: 1000px;
    width: 100%;
  }}
  .preview-stage {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #ffffff;
    border-radius: 8px;
    overflow: hidden;
    padding: 12px;
    min-height: 480px;
  }}
  .controls {{
    width: 340px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}
  .panel {{
    background: #334155;
    padding: 14px;
    border-radius: 8px;
  }}
  .panel h3 {{
    margin: 0 0 10px 0;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
  }}
  .btn-group {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }}
  .btn {{
    background: #475569;
    color: #ffffff;
    border: none;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s ease;
  }}
  .btn:hover {{ background: #64748b; }}
  .btn.active {{
    background: #0284c7;
    box-shadow: 0 0 0 2px #38bdf8;
  }}
  .btn.auto {{
    background: #059669;
    grid-column: span 2;
  }}
  .btn.auto.active {{
    background: #10b981;
    box-shadow: 0 0 0 2px #34d399;
  }}
  .status {{
    font-size: 13px;
    color: #cbd5e1;
    font-family: monospace;
    background: #0f172a;
    padding: 8px;
    border-radius: 4px;
  }}
</style>
</head>
<body>
  <h1>Character Staging Studio: {pack.name} [<code>{pack.pack_id}</code>]</h1>
  <div class="container">
    <div class="preview-stage" id="stage-host">
      {raw_svg_escaped}
    </div>
    <div class="controls">
      <div class="panel">
        <h3>Eye States</h3>
        <div class="btn-group">
          {eye_buttons}
          <button class="btn auto" id="toggle-blink">Toggle Auto-Blink</button>
        </div>
      </div>
      <div class="panel">
        <h3>Mouth States</h3>
        <div class="btn-group">
          {mouth_buttons}
          <button class="btn auto" id="toggle-talk">Toggle Viseme Talk</button>
        </div>
      </div>
      <div class="panel">
        <h3>Active State</h3>
        <div class="status" id="active-status">Eyes: {pack.default_eyes} | Mouth: {pack.default_mouth}</div>
      </div>
    </div>
  </div>

  <script>
    let currentEyes = "{pack.default_eyes}";
    let currentMouth = "{pack.default_mouth}";
    let blinkInterval = null;
    let talkInterval = null;

    const eyeList = {json.dumps(pack.eye_states)};
    const mouthList = {json.dumps(pack.mouth_states)};

    function updateCharacter(eyes, mouth) {{
      if (eyes) currentEyes = eyes;
      if (mouth) currentMouth = mouth;

      // Update button styles
      document.querySelectorAll(".eye-btn").forEach(b => {{
        b.classList.toggle("active", b.dataset.eye === currentEyes);
      }});
      document.querySelectorAll(".mouth-btn").forEach(b => {{
        b.classList.toggle("active", b.dataset.mouth === currentMouth);
      }});

      // Toggle SVG visibility
      eyeList.forEach(e => {{
        const el = document.getElementById("eyes-" + e);
        if (el) el.style.display = (e === currentEyes ? "inline" : "none");
      }});
      mouthList.forEach(m => {{
        const el = document.getElementById("mouth-" + m);
        if (el) el.style.display = (m === currentMouth ? "inline" : "none");
      }});

      document.getElementById("active-status").textContent = `Eyes: ${{currentEyes}} | Mouth: ${{currentMouth}}`;
    }}

    document.querySelectorAll(".eye-btn").forEach(b => {{
      b.addEventListener("click", () => updateCharacter(b.dataset.eye, null));
    }});
    document.querySelectorAll(".mouth-btn").forEach(b => {{
      b.addEventListener("click", () => updateCharacter(null, b.dataset.mouth));
    }});

    // Auto blink
    const blinkBtn = document.getElementById("toggle-blink");
    blinkBtn.addEventListener("click", () => {{
      if (blinkInterval) {{
        clearInterval(blinkInterval);
        blinkInterval = null;
        blinkBtn.classList.remove("active");
        updateCharacter("open", null);
      }} else {{
        blinkBtn.classList.add("active");
        blinkInterval = setInterval(() => {{
          updateCharacter("blink", null);
          setTimeout(() => updateCharacter("open", null), 160);
        }}, 2400);
      }}
    }});

    // Auto talk / viseme simulation
    const talkBtn = document.getElementById("toggle-talk");
    let talkIdx = 0;
    const talkSequence = ["closed", "slightly_open", "wide_open", "round_o", "slightly_open", "wide_open"];
    talkBtn.addEventListener("click", () => {{
      if (talkInterval) {{
        clearInterval(talkInterval);
        talkInterval = null;
        talkBtn.classList.remove("active");
        updateCharacter(null, "closed");
      }} else {{
        talkBtn.classList.add("active");
        talkInterval = setInterval(() => {{
          talkIdx = (talkIdx + 1) % talkSequence.length;
          updateCharacter(null, talkSequence[talkIdx]);
        }}, 180);
      }}
    }});

    // Init
    updateCharacter(currentEyes, currentMouth);
  </script>
</body>
</html>
"""
    workbench_path.write_text(html_workbench, encoding="utf-8")
    artifacts["staging_html"] = workbench_path

    # 2. Render individual reference pose PNGs
    reference_poses = [
        ("r1_c0_closed", "open", "closed"),
        ("r1_c1_slightly_open", "open", "slightly_open"),
        ("r2_c0_wide_open", "open", "wide_open"),
        ("r2_c1_round_o", "open", "round_o"),
        ("r3_c0_neutral", "open", "closed"),
        ("r3_c1_blink", "blink", "closed"),
        ("r4_c0_screen_left", "screen_left", "closed"),
        ("r4_c1_screen_right", "screen_right", "closed"),
    ]

    rendered_images = []
    for pose_name, eye_st, mouth_st in reference_poses:
        img_out = target_dir / f"{pose_name}.png"
        pack.render_png(img_out, eyes=eye_st, mouth=mouth_st, width=560, height=630)
        artifacts[pose_name] = img_out
        rendered_images.append(img_out)

    # 3. Create composite contact sheet
    sheet_w = 560 * 2
    sheet_h = 630 * 4
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (255, 255, 255, 255))
    for idx, img_path in enumerate(rendered_images):
        row = idx // 2
        col = idx % 2
        with Image.open(img_path) as im:
            sheet.paste(im, (col * 560, row * 630), mask=im.split()[3] if im.mode == "RGBA" else None)

    contact_sheet_path = target_dir / f"{pack.pack_id}_contact_sheet.png"
    sheet.save(contact_sheet_path)
    artifacts["contact_sheet"] = contact_sheet_path

    return artifacts
