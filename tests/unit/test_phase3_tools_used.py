"""
Purpose: Unit tests for Phase 3: Tools Actually Used - asset planning, element indexing in library,
         and manifest tools_used tracking.
Inputs: Element specifications, mock scripts, and manifest generators.
Outputs: Assertion validations for index.json persistence, deduplication, and manifest tracking.
Depends on: pytest, pathlib, json, toonshorts.core.library, toonshorts.core.pipeline, toonshorts.core.paths
Used by: tests
Config keys: None
Tests: tests/unit/test_phase3_tools_used.py
"""

import json
from pathlib import Path
import pytest

from toonshorts.core import paths
from toonshorts.core.library import (
    compute_element_key,
    resolve_theme_tags,
    load_element_index,
    save_element_index,
    find_element,
    save_element_once,
    get_or_create_element,
)
from toonshorts.core.models import (
    ScriptPlan,
    Scene,
    Character,
    Visual,
)
from toonshorts.core.pipeline import generate_manifest, register_plan_custom_elements


def test_directing_skill_has_asset_planning_step():
    """Verify toon-shorts-directing skill contains mandatory asset planning step and animejs-animation reference."""
    skill_file = paths.PROJECT_ROOT / ".agents" / "skills" / "toon-shorts-directing" / "SKILL.md"
    assert skill_file.is_file(), "Directing skill file missing"
    content = skill_file.read_text(encoding="utf-8")

    assert "Asset Planning" in content
    assert "Library Asset" in content
    assert "Custom Animated SVG" in content
    assert "Generated Image" in content
    assert "Screen Recording" in content
    assert "animejs-animation" in content


def test_element_indexing_and_deduplication(tmp_path, monkeypatch):
    """Verify generated elements are saved ONCE into library/elements/<type>/ with index.json recording metadata."""
    lib_dir = tmp_path / "library"
    elements_dir = lib_dir / "elements"
    elements_dir.mkdir(parents=True)
    monkeypatch.setattr(paths, "LIBRARY_DIR", lib_dir)
    monkeypatch.setattr(paths, "LIBRARY_ELEMENTS_DIR", elements_dir)

    # 1. Compute element key
    custom_svg = '<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="blue"/></svg>'
    theme_tags = resolve_theme_tags("night_studio")
    assert "dark" in theme_tags

    key = compute_element_key(
        element_type="custom",
        content=custom_svg,
        theme_tags=theme_tags,
        source="code",
        animated=True,
    )
    assert len(key) == 64

    # 2. Check index before generating -> Miss
    existing = find_element("custom", key=key)
    assert existing is None

    # 3. Save element ONCE
    file_name = f"custom_glow_{key[:12]}.svg"
    out_path, is_hit = save_element_once(
        element_type="custom",
        key=key,
        file_name=file_name,
        content=custom_svg,
        theme_tags=theme_tags,
        animated=True,
        source="code",
    )
    assert not is_hit
    assert out_path.is_file()
    assert out_path.read_text(encoding="utf-8") == custom_svg

    # 4. Verify index.json file format and recorded attributes
    idx_file = elements_dir / "custom" / "index.json"
    assert idx_file.is_file()
    index_entries = json.loads(idx_file.read_text(encoding="utf-8"))
    assert len(index_entries) == 1
    entry = index_entries[0]
    assert entry["key"] == key
    assert entry["type"] == "custom"
    assert "dark" in entry["theme_tags"]
    assert entry["animated"] is True
    assert entry["source"] == "code"
    assert entry["file_name"] == file_name

    # 5. Check index again -> Hit
    found = find_element("custom", key=key)
    assert found is not None
    assert found["file_name"] == file_name

    # 6. Second save attempt with same key must return existing without rewriting
    out_path2, is_hit2 = save_element_once(
        element_type="custom",
        key=key,
        file_name=file_name,
        content=custom_svg,
        theme_tags=theme_tags,
        animated=True,
        source="code",
    )
    assert is_hit2 is True
    assert out_path2 == out_path

    # Verify still only 1 entry in index.json
    index_entries_after = json.loads(idx_file.read_text(encoding="utf-8"))
    assert len(index_entries_after) == 1


def test_get_or_create_element_creator_called_only_on_miss(tmp_path, monkeypatch):
    """Verify creator callback is executed on index miss and bypassed on hit."""
    lib_dir = tmp_path / "library"
    elements_dir = lib_dir / "elements"
    elements_dir.mkdir(parents=True)
    monkeypatch.setattr(paths, "LIBRARY_DIR", lib_dir)
    monkeypatch.setattr(paths, "LIBRARY_ELEMENTS_DIR", elements_dir)

    call_count = 0

    def mock_creator():
        nonlocal call_count
        call_count += 1
        return b"fake_png_image_bytes"

    key = "image_key_12345"
    tags = ["vintage-paper"]

    # First call: miss -> creator called
    path1, is_hit1 = get_or_create_element(
        element_type="image",
        key=key,
        file_name="vintage_icon.png",
        creator_fn=mock_creator,
        theme_tags=tags,
        animated=False,
        source="image",
    )
    assert not is_hit1
    assert call_count == 1
    assert path1.is_file()

    # Second call: hit -> creator NOT called
    path2, is_hit2 = get_or_create_element(
        element_type="image",
        key=key,
        file_name="vintage_icon.png",
        creator_fn=mock_creator,
        theme_tags=tags,
        animated=False,
        source="image",
    )
    assert is_hit2
    assert call_count == 1
    assert path2 == path1


def test_manifest_tools_used_records_all_four_categories(tmp_path, monkeypatch):
    """Verify manifest.json contains a tools_used list spanning skills, image gen, library hits, and custom visuals."""
    lib_dir = tmp_path / "library"
    elements_dir = lib_dir / "elements"
    elements_dir.mkdir(parents=True)
    monkeypatch.setattr(paths, "LIBRARY_DIR", lib_dir)
    monkeypatch.setattr(paths, "LIBRARY_ELEMENTS_DIR", elements_dir)

    # Build screenplay containing custom visual
    custom_svg = '<svg viewBox="0 0 100 100"><rect width="80" height="80" fill="green"/></svg>'
    plan = ScriptPlan(
        title="Tools Used Test",
        art_style="whiteboard",
        emotional_arc="curiosity to clarity",
        characters=[
            Character(name="Sam", visual_description="Guide"),
            Character(name="Alex", visual_description="Student"),
        ],
        scenes=[
            Scene(
                scene_number=1,
                speaker="Sam",
                dialogue_line="Checking our tool tracking.",
                action="Displaying custom visual element",
                board_objects=[
                    {
                        "id": "bo_cust_1",
                        "type": "custom",
                        "slot": "top",
                        "data": {
                            "level": 1,
                            "svg": custom_svg,
                            "timeline": {"preset": "pop_in", "duration_ms": 600},
                        },
                    }
                ],
            ),
            Scene(
                scene_number=2,
                speaker="Alex",
                dialogue_line="Looks great Sam.",
                action="Nodding",
            ),
            Scene(
                scene_number=3,
                speaker="Sam",
                dialogue_line="Here is the second point.",
                action="Explaining",
            ),
            Scene(
                scene_number=4,
                speaker="Alex",
                dialogue_line="Understood perfectly.",
                action="Thumbs up",
            ),
        ],
    )

    library_pieces = ["library/backgrounds/bg_whiteboard_far_1234.png"]

    # Register custom elements
    register_plan_custom_elements(plan, "whiteboard", library_pieces)
    assert any("library/elements/custom/" in p for p in library_pieces)

    # Generate manifest
    class MockVoice:
        name = "gemini_tts"
        model_name = "gemini-tts-flash"

    manifest = generate_manifest(
        video_name="Tools_Used_Test",
        style="whiteboard",
        plan=plan,
        voice_plugin=MockVoice(),
        library_pieces_used=library_pieces,
        renderer_name="pillow",
    )

    manifest_dict = manifest.model_dump()
    assert "tools_used" in manifest_dict
    tools_used = manifest_dict["tools_used"]
    assert isinstance(tools_used, list)
    assert len(tools_used) > 0

    # Verify all four required categories are present
    categories = {entry.get("category") for entry in tools_used if isinstance(entry, dict)}
    assert "skills" in categories
    assert "image generation" in categories
    assert "library hits" in categories
    assert "custom visuals" in categories

    # Verify specific skill names
    skill_names = [e.get("name") for e in tools_used if e.get("category") == "skills"]
    assert "toon-shorts-directing" in skill_names
    assert "animejs-animation" in skill_names
    assert "toon-shorts-visual-check" in skill_names

    # Verify custom visual entry
    custom_entries = [e for e in tools_used if e.get("category") == "custom visuals"]
    assert len(custom_entries) == 1
    assert custom_entries[0]["id"] == "bo_cust_1"
    assert custom_entries[0]["level"] == 1
