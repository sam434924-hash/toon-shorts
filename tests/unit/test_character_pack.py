"""Unit tests for 2D layered SVG character pack system, security validation, and staging."""

from pathlib import Path
import pytest
from PIL import Image

from toonshorts.core.character_pack import (
    CharacterPack,
    load_character_pack,
    validate_pack_name,
    ensure_path_inside_dir,
    create_character_staging,
    validate_svg_security,
    validate_manifest_schema,
    ALLOWED_SVG_ELEMENTS,
    MAX_SVG_SIZE_BYTES,
)
from toonshorts.core.character2d import get_character, PROJECT_ROOT


@pytest.fixture
def boy_a_pack():
    return load_character_pack("boy_a")


def test_validate_pack_name():
    """Verifies strict character pack name validation."""
    assert validate_pack_name("boy_a") == "boy_a"
    assert validate_pack_name("hero-01_v2") == "hero-01_v2"

    with pytest.raises(ValueError, match="Invalid character pack name"):
        validate_pack_name("")
    with pytest.raises(ValueError, match="Invalid character pack name"):
        validate_pack_name("../evil")
    with pytest.raises(ValueError, match="Invalid character pack name"):
        validate_pack_name("name with spaces")
    with pytest.raises(ValueError, match="Invalid character pack name"):
        validate_pack_name("name$special")
    with pytest.raises(ValueError, match="Invalid character pack name"):
        validate_pack_name("a" * 33)


def test_ensure_path_inside_dir(tmp_path):
    """Verifies directory boundary protection against directory traversal."""
    root = tmp_path / "characters"
    root.mkdir()
    safe_child = root / "boy_a" / "character.svg"
    safe_child.parent.mkdir()
    safe_child.touch()

    assert ensure_path_inside_dir(safe_child, root) == safe_child.resolve()

    outside_file = tmp_path / "secret.env"
    outside_file.touch()
    with pytest.raises(ValueError, match="Security error"):
        ensure_path_inside_dir(outside_file, root)


def test_load_boy_a_character_pack(boy_a_pack):
    """Verifies loading of boy_a character pack and metadata integrity."""
    assert boy_a_pack.pack_id == "boy_a"
    assert boy_a_pack.name == "Boy A"
    assert boy_a_pack.default_eyes == "open"
    assert boy_a_pack.default_mouth == "closed"
    assert boy_a_pack.viewBox == "0 0 560 630"

    expected_eyes = ["open", "blink", "screen_left", "screen_right"]
    assert boy_a_pack.eye_states == expected_eyes

    expected_mouths = ["closed", "slightly_open", "wide_open", "round_o"]
    assert boy_a_pack.mouth_states == expected_mouths

    # Verification of validation
    errors = boy_a_pack.validate()
    assert errors == []


def test_get_character_loads_character_pack():
    """Verifies get_character resolves boy_a as a CharacterPack from central registry."""
    loaded = get_character("boy_a")
    assert isinstance(loaded, CharacterPack)
    assert loaded.pack_id == "boy_a"


def test_svg_size_under_limit(boy_a_pack):
    """Verifies that the character SVG is strictly under 200 KB limit."""
    svg_size = len(boy_a_pack.raw_svg.encode("utf-8"))
    assert svg_size < MAX_SVG_SIZE_BYTES
    # Ensure it's efficient: comfortably under 50 KB
    assert svg_size < 50 * 1024


def test_svg_no_gradients(boy_a_pack):
    """Verifies that no gradients are used (flattened 2-tone look)."""
    assert "<linearGradient" not in boy_a_pack.raw_svg
    assert "<radialGradient" not in boy_a_pack.raw_svg


def test_svg_allowlist_security_validation():
    """Verifies SVG allowlist validator rejects forbidden tags, on* attrs, remote URLs, javascript:, and @import."""
    valid_base = """<svg id="test-pack" viewBox="0 0 560 630" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="cp"><path d="M 0 0 L 10 10 Z"/></clipPath>
        <linearGradient id="g1"><stop offset="0%" stop-color="#fff"/></linearGradient>
        <radialGradient id="g2"><stop offset="0%" stop-color="#000"/></radialGradient>
        <style>.eye { display: inline; }</style>
      </defs>
      <g id="layer-head"><circle cx="280" cy="200" r="50" fill="url(#g1)"/></g>
      <rect x="10" y="10" width="100" height="80"/>
      <ellipse cx="50" cy="50" rx="20" ry="10"/>
      <polygon points="0,0 10,10 20,0"/>
      <polyline points="0,0 10,10 20,20"/>
      <line x1="0" y1="0" x2="10" y2="10"/>
    </svg>"""

    # 1. Valid SVG passes with zero errors
    assert validate_svg_security(valid_base) == []

    # 2. Disallowed elements (script, foreignObject, iframe, text, image, use)
    for bad_tag in ["<script>alert(1)</script>", "<foreignObject><div>x</div></foreignObject>", "<iframe></iframe>", "<text>Hello</text>", "<image href='#img'/>", "<use href='#g1'/>"]:
        svg = f"<svg viewBox='0 0 10 10'>{bad_tag}</svg>"
        errs = validate_svg_security(svg)
        assert any("Disallowed SVG element" in e for e in errs), f"Expected element rejection for {bad_tag}"

    # 3. on* event handler attributes
    for on_attr in ["onclick='alert(1)'", "onload='fetch()'", "onerror='evil()'"]:
        svg = f"<svg viewBox='0 0 10 10'><rect {on_attr} width='10' height='10'/></svg>"
        errs = validate_svg_security(svg)
        assert any("Disallowed event handler" in e for e in errs), f"Expected event handler rejection for {on_attr}"

    # 4. href not starting with #
    for bad_href in ["href='https://evil.com/x.svg'", "href='external.svg'", "xlink:href='http://evil.com/x'"]:
        svg = f"<svg xmlns:xlink='http://www.w3.org/1999/xlink' viewBox='0 0 10 10'><g {bad_href}></g></svg>"
        errs = validate_svg_security(svg)
        assert any("Disallowed href" in e for e in errs), f"Expected href rejection for {bad_href}: got {errs}"

    # 5. url() not starting with # in attributes
    for bad_url_attr in ["fill='url(https://evil.com/steal.png)'", "filter='url(http://other/filter)'", "fill='url(\"data:image/svg+xml,test\")'"]:
        svg = f"<svg viewBox='0 0 10 10'><rect {bad_url_attr} width='10' height='10'/></svg>"
        errs = validate_svg_security(svg)
        assert any("Disallowed url() reference" in e for e in errs), f"Expected url() rejection for {bad_url_attr}"

    # 6. style blocks that use @import
    svg_import = "<svg viewBox='0 0 10 10'><defs><style>@import url('https://fonts.googleapis.com');</style></defs></svg>"
    errs_import = validate_svg_security(svg_import)
    assert any("Disallowed @import" in e for e in errs_import)

    # 7. style blocks that use external URLs
    svg_style_ext = "<svg viewBox='0 0 10 10'><defs><style>.cls { background: url('https://evil.com/leak.png'); }</style></defs></svg>"
    errs_ext = validate_svg_security(svg_style_ext)
    assert any("Disallowed url() reference in style block" in e for e in errs_ext)

    # 8. javascript: values
    for js_val in ["<a href='javascript:alert(1)'></a>", "<rect fill='javascript:void(0)' width='10' height='10'/>"]:
        svg = f"<svg viewBox='0 0 10 10'>{js_val}</svg>"
        errs = validate_svg_security(svg)
        assert any("Disallowed javascript:" in e or "Disallowed SVG element" in e or "Disallowed href" in e for e in errs)

    # 9. Size limit exceeding 200 KB
    huge_svg = "<svg viewBox='0 0 10 10'>" + ("<g></g>" * 30000) + "</svg>"
    assert len(huge_svg.encode("utf-8")) > MAX_SVG_SIZE_BYTES
    errs_size = validate_svg_security(huge_svg)
    assert any("exceeds maximum limit" in e for e in errs_size)


def test_manifest_schema_validation():
    """Verifies pack manifest schema validation for required fields."""
    valid_manifest = {
        "id": "test_pack",
        "kind": "vector",
        "viewBox": "0 0 560 630",
        "layers": ["layer-1", "layer-2"],
        "mouth_states": ["closed", "slightly_open", "wide_open", "round_o"],
        "eye_states": ["open", "blink", "screen_left", "screen_right"],
        "anchors": {"head": [280, 260]},
        "safe_bounding_box": {"min_x": 0, "min_y": 0, "max_x": 560, "max_y": 630},
        "default_slot": "left",
        "scale": 1.0,
        "allowed_gestures": ["idle", "wave"],
    }
    assert validate_manifest_schema(valid_manifest) == []

    # Test rejection of missing/invalid kind
    bad_kind = dict(valid_manifest, kind="3d_mesh")
    assert any("Manifest field 'kind'" in e for e in validate_manifest_schema(bad_kind))

    # Test rejection of invalid default_slot
    bad_slot = dict(valid_manifest, default_slot="center")
    assert any("Manifest field 'default_slot'" in e for e in validate_manifest_schema(bad_slot))

    # Test rejection of invalid scale
    bad_scale = dict(valid_manifest, scale=-1.5)
    assert any("Manifest field 'scale'" in e for e in validate_manifest_schema(bad_scale))

    # Test rejection of missing layers
    no_layers = dict(valid_manifest)
    del no_layers["layers"]
    assert any("Manifest missing required list or dict field 'layers'" in e for e in validate_manifest_schema(no_layers))


def test_swappable_layer_switching(boy_a_pack):
    """Verifies swappable eye and mouth states via get_svg."""
    # Test setting screen_left and wide_open
    svg = boy_a_pack.get_svg(eyes="screen_left", mouth="wide_open")
    assert "#eyes-screen_left { display: inline !important; }" in svg
    assert "#mouth-wide_open { display: inline !important; }" in svg
    assert ".eye-state { display: none !important; }" in svg
    assert ".mouth-state { display: none !important; }" in svg

    # Test invalid eye state
    with pytest.raises(ValueError, match="Invalid eye state"):
        boy_a_pack.get_svg(eyes="laser_eyes")

    # Test invalid mouth state
    with pytest.raises(ValueError, match="Invalid mouth state"):
        boy_a_pack.get_svg(mouth="screaming")


def test_eyebrows_head_hair_identical_across_states(boy_a_pack):
    """Verifies that eyebrows, hair, and head base are identical static layers outside state groups."""
    raw = boy_a_pack.raw_svg

    # Core layers are independent from the swappable groups
    assert 'id="layer-head-base"' in raw
    assert 'id="layer-hair-front"' in raw
    assert 'id="layer-hair-back"' in raw
    assert 'id="layer-eyebrows"' in raw
    assert 'id="layer-neck"' in raw
    assert 'id="layer-hoodie-front"' in raw

    # Ensure eyebrows are NOT nested inside swappable eye states
    assert 'id="layer-eyebrows"' not in raw.split('<g id="layer-eyes">')[1].split('</g>')[0]


def test_hair_does_not_overlap_eyebrows(boy_a_pack):
    """Verifies hair fringe and bangs stay well clear of eyebrows with no overlapping."""
    import re
    raw = boy_a_pack.raw_svg

    # Extract layer-hair-front contents
    hair_front = raw.split('id="layer-hair-front"')[1].split('</g>')[0]

    # Find all polygon points in hair fringe
    points_matches = re.findall(r'points="([^"]+)"', hair_front)
    for pts_str in points_matches:
        pairs = pts_str.strip().split()
        for p in pairs:
            if "," in p:
                x_str, y_str = p.split(",")
                x, y = float(x_str), float(y_str)
                # Forehead area where eyebrows sit (X between 150 and 410)
                if 150 <= x <= 410:
                    assert y < 185, f"Hair bang lock point ({x}, {y}) is too low, risk overlapping eyebrows (y >= 198)!"


def test_render_png_and_staging(boy_a_pack, tmp_path):
    """Verifies rendering character state to PNG and generating full staging artifacts."""
    out_png = tmp_path / "test_neutral.png"
    boy_a_pack.render_png(out_png, eyes="open", mouth="closed", width=280, height=315)
    assert out_png.is_file()
    with Image.open(out_png) as im:
        assert im.size == (280, 315)
        assert im.mode == "RGBA"

    # Test staging generation
    staging_dir = tmp_path / "staging"
    artifacts = create_character_staging(boy_a_pack, output_dir=staging_dir)

    assert "staging_html" in artifacts
    assert artifacts["staging_html"].is_file()
    html_text = artifacts["staging_html"].read_text(encoding="utf-8")
    assert "Character Staging Studio" in html_text
    assert "screen_left" in html_text
    assert "screen_right" in html_text

    assert "contact_sheet" in artifacts
    assert artifacts["contact_sheet"].is_file()
    with Image.open(artifacts["contact_sheet"]) as c_im:
        assert c_im.size == (560 * 2, 630 * 4)
