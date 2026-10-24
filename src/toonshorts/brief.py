"""
Purpose: Screenplay brief data model, inventory validation, and serialization.
Inputs: User brief specifications or saved brief JSON files.
Outputs: Validated VideoBrief models and saved brief JSON files.
Depends on: json, pathlib, re, time, typing, pydantic, core.config, core.models, core.paths, inventory
Used by: cli
Config keys: None
Tests: tests/unit/test_brief.py
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Literal, Optional, Set, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from toonshorts.core import config, paths
from toonshorts.core.models import sanitize_video_name

BRIEFS_DIR = paths.VIDEOS_DIR

SAFE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")

KNOWN_KEYS = frozenset({
    "video_name",
    "story",
    "format",
    "style",
    "characters",
    "speaker",
    "voice",
    "voice_engine",
    "board_animations_use",
    "board_animations_avoid",
    "hand_gestures",
    "camera",
    "length_seconds",
    "custom",
    "created_at",
})


def validate_brief_filename(name: str) -> str:
    """Validates video name for path safety without shell or traversal characters."""
    return sanitize_video_name(name)









class VideoBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_name: str = Field(..., min_length=1, max_length=64)
    story: str = Field(..., min_length=1)
    format: str = Field(default="explanation video")
    style: str = Field(..., min_length=1)
    characters: List[str] = Field(..., min_length=1)
    speaker: str = Field(...)
    voice: str = Field(...)
    voice_engine: Optional[str] = Field(default=None)
    board_animations_use: List[str] = Field(default_factory=list)
    board_animations_avoid: List[str] = Field(default_factory=list)
    hand_gestures: Literal["on", "off"] = Field(default="on")
    camera: str = Field(default="zoom_speaker")
    length_seconds: int = Field(default=30, ge=10, le=120)
    custom: str = Field(default="")
    created_at: Optional[str] = Field(default=None)

    @field_validator("video_name")
    @classmethod
    def check_video_name(cls, v: str) -> str:
        return validate_brief_filename(v)

    def validate_against_inventory(self, inv: Optional[Dict[str, Any]] = None) -> List[str]:
        """Validates all brief choices against real installed inventory."""
        if inv is None:
            from toonshorts.inventory import get_inventory
            inv = get_inventory()

        errors: List[str] = []

        # 1. Validate style
        known_styles = {s["id"] for s in inv.get("styles", [])}
        if self.style not in known_styles:
            errors.append(f"Style '{self.style}' not found in inventory. Available: {sorted(known_styles)}")

        # 2. Validate characters
        chars_2d = inv.get("characters", {}).get("2d_packs", [])
        chars_2d_ids = {c["id"] for c in chars_2d}
        chars_2d_names = {c.get("name", "").lower() for c in chars_2d}
        proc = inv.get("characters", {}).get("procedural", [])
        proc_ids = {c["id"] for c in proc}
        proc_names = {c.get("name", "").lower() for c in proc}
        chars_3d = {c["id"] for c in inv.get("characters", {}).get("3d_models", [])}
        all_chars = chars_2d_ids | chars_3d | proc_ids | {"stickman", "cairo_stickman", "stick_hoodie"}

        for char in self.characters:
            char_clean = char.strip()
            if (
                char_clean not in all_chars
                and char_clean.lower() not in chars_2d_names
                and char_clean.lower() not in proc_names
            ):
                errors.append(f"Character '{char}' not found in inventory. Available: {sorted(all_chars | proc_names | chars_2d_names)}")

        # 3. Validate speaker
        valid_speakers = set(self.characters) | {"both", "all", "none"}
        if self.speaker not in valid_speakers:
            errors.append(f"Speaker '{self.speaker}' must be one of {sorted(valid_speakers)}")

        # 4. Validate voice
        v_info = inv.get("voices", {})
        gemini_voices = {v.lower() for v in v_info.get("gemini_voices", [])}
        piper_voices = {v.lower() for v in v_info.get("piper_models", [])}
        engines = {e.lower() for e in v_info.get("engines", [])}
        registered = {v["name"].lower() for v in v_info.get("registered_voices", [])}
        all_voices = gemini_voices | piper_voices | engines | registered
        if self.voice.lower() not in all_voices:
            errors.append(f"Voice '{self.voice}' not found in inventory. Available: {sorted(all_voices)}")

        # 5. Validate board animations
        anim_info = inv.get("board_animations", {})
        templates = set(anim_info.get("visual_templates", []))
        annotations = set(anim_info.get("sketch_annotations", []))
        all_anims = templates | annotations
        for anim in self.board_animations_use:
            if anim not in all_anims:
                errors.append(f"Animation '{anim}' in board_animations_use not found in inventory. Available: {sorted(all_anims)}")
        for anim in self.board_animations_avoid:
            if anim not in all_anims:
                errors.append(f"Animation '{anim}' in board_animations_avoid not found in inventory. Available: {sorted(all_anims)}")

        # 6. Validate camera
        cam_info = inv.get("camera_options", {})
        framing_ids = {f["id"] for f in cam_info.get("framing_modes", [])}
        moves = set(cam_info.get("camera_moves", []))
        all_cams = framing_ids | moves | {"zoom on speaker", "fixed", "zoom"}
        if self.camera not in all_cams and self.camera.lower() not in all_cams:
            errors.append(f"Camera option '{self.camera}' not in inventory. Available: {sorted(all_cams)}")

        return errors


def save_brief(brief: VideoBrief, briefs_dir: Path = BRIEFS_DIR) -> Path:
    """Validates and saves brief to briefs/<video-name>.json."""
    briefs_dir.mkdir(parents=True, exist_ok=True)
    errors = brief.validate_against_inventory()
    if errors:
        raise ValueError(f"Brief failed inventory validation:\n - " + "\n - ".join(errors))

    if not brief.created_at:
        brief.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    file_path = briefs_dir / f"{brief.video_name}.json"
    file_path.write_text(json.dumps(brief.model_dump(), indent=2), encoding="utf-8")
    return file_path


def load_brief(brief_identifier: Union[str, Path], briefs_dir: Path = BRIEFS_DIR) -> VideoBrief:
    """Loads and strictly validates a brief JSON file."""
    if isinstance(brief_identifier, Path):
        file_path = brief_identifier
    else:
        p = Path(brief_identifier)
        if p.is_file():
            file_path = p
        else:
            name = str(brief_identifier).strip()
            video_brief = paths.VIDEOS_DIR / name / "brief.json"
            if video_brief.is_file():
                file_path = video_brief
            else:
                if not name.endswith(".json"):
                    name = f"{name}.json"
                file_path = briefs_dir / name

    if not file_path.is_file():
        raise FileNotFoundError(f"Brief file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    raw_data = json.loads(content)

    if not isinstance(raw_data, dict):
        raise ValueError("Brief file content must be a JSON object")

    # Extra key validation (disallow unknown keys)
    extra_keys = set(raw_data.keys()) - KNOWN_KEYS
    if extra_keys:
        raise ValueError(f"Unknown keys in brief file '{file_path.name}': {sorted(extra_keys)}")

    brief = VideoBrief.model_validate(raw_data)
    errors = brief.validate_against_inventory()
    if errors:
        raise ValueError(f"Loaded brief failed inventory validation:\n - " + "\n - ".join(errors))

    return brief


def get_last_brief(briefs_dir: Path = BRIEFS_DIR) -> Optional[VideoBrief]:
    """Finds the most recently modified brief in the briefs directory."""
    if not briefs_dir.is_dir():
        return None
    brief_files = sorted(
        list(briefs_dir.glob("*/brief.json")) + list(briefs_dir.glob("*.json")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    for bf in brief_files:
        try:
            return load_brief(bf, briefs_dir=briefs_dir)
        except Exception:
            continue
    return None


def format_brief_summary(brief: VideoBrief) -> str:
    """
    Renders an exact, high-density summary in at most 10 lines.
    Part 4 requirement: Show me a short summary of the brief (max 10 lines) and wait for 'go'.
    """
    chars_str = ", ".join(brief.characters)
    anims_use = ", ".join(brief.board_animations_use) if brief.board_animations_use else "default"
    anims_avoid = ", ".join(brief.board_animations_avoid) if brief.board_animations_avoid else "none"
    custom_str = brief.custom if brief.custom else "none"

    lines = [
        f"Brief: {brief.video_name} ({brief.length_seconds}s, {brief.format})",
        f"Story: {brief.story[:80]}",
        f"Theme / Style: {brief.style}",
        f"Characters: {chars_str} | Speaker: {brief.speaker}",
        f"Voice: {brief.voice} (engine: {brief.voice_engine or 'auto'})",
        f"Board Animations: USE [{anims_use}] | AVOID [{anims_avoid}]",
        f"Gestures: {brief.hand_gestures} | Camera: {brief.camera}",
        f"Custom notes: {custom_str[:80]}",
        "Status: Ready to build. Reply 'go' to confirm.",
    ]
    # Ensure strictly <= 10 lines
    return "\n".join(lines[:10])
