"""
Purpose: Data schemas for screenplay direction, audio timing, and review.
Inputs: Raw dictionary definitions or keyword arguments.
Outputs: Validated Pydantic models, enums, dataclasses, and safe filenames.
Depends on: dataclasses, enum, pathlib, pydantic, re, typing
Used by: core, core.assembler, core.client, core.cost, core.pipeline, core.registry, core.schemas, core.subtitles, models, plugins.llm.fake, plugins.llm.gemini, plugins.motion.ffmpeg, plugins.motion.static, plugins.render.animejs.annotations, plugins.render.animejs.cast, plugins.render.animejs.html_builder, plugins.render.animejs.plugin, plugins.render.blender3d, plugins.render.cairo, plugins.render.fake, plugins.render.gemini, plugins.render.pillow, plugins.voice.fake, plugins.voice.gemini_tts, plugins.voice.piper, plugins.voice.windows_sapi, voice, voice_utils
Config keys: None
Tests: tests/unit/test_sanitizing.py, tests/unit/test_validation.py
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional
import re
from pydantic import BaseModel, Field, field_validator, model_validator


class CameraMove(str, Enum):
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    SHAKE = "shake"
    STATIC = "static"


class Transition(str, Enum):
    CUT = "cut"
    FADE = "fade"
    WIPE = "wipe"
    NONE = "none"


class Pose(str, Enum):
    IDLE = "idle"
    WAVING = "waving"
    JUMPING = "jumping"
    SHOCKED = "shocked"
    LAUGHING = "laughing"


class Character(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)
    visual_description: str = Field(..., min_length=5, max_length=200)
    voice_id: str = Field(default="voice_default", min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        clean = re.sub(r"[^\w\s-]", "", v).strip()
        if not clean:
            raise ValueError("Character name must contain alphanumeric characters")
        return clean


class Scene(BaseModel):
    scene_number: int = Field(..., ge=1, le=20)
    speaker: str = Field(..., min_length=1, max_length=30)
    dialogue_line: str = Field(..., min_length=1, max_length=250)
    action: str = Field(..., min_length=1, max_length=200)
    pose: Pose = Field(default=Pose.IDLE)
    camera_move: CameraMove = Field(default=CameraMove.STATIC)
    transition: Transition = Field(default=Transition.CUT)
    is_punchline: bool = Field(default=False)
    gesture: Optional[str] = Field(default=None)

    @field_validator("gesture")
    @classmethod
    def validate_gesture(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.lower().strip()
        allowed = {"idle", "wave", "point", "explain", "open_hand", "thumbs_up", "shrug"}
        if clean not in allowed:
            raise ValueError(f"Invalid gesture '{v}'. Allowed gestures: {sorted(list(allowed))}")
        return clean


class ScriptPlan(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)
    art_style: str = Field(..., min_length=1, max_length=50)
    emotional_arc: str = Field(..., min_length=5, max_length=200)
    characters: List[Character] = Field(..., min_length=2, max_length=3)
    scenes: List[Scene] = Field(..., min_length=4, max_length=10)

    @model_validator(mode="after")
    def validate_characters_and_speakers(self) -> "ScriptPlan":
        char_names = {c.name.lower() for c in self.characters}
        for s in self.scenes:
            if s.speaker.lower() not in char_names:
                matched = next((c.name for c in self.characters if c.name.lower() == s.speaker.lower()), None)
                if matched:
                    s.speaker = matched
                else:
                    raise ValueError(f"Scene speaker '{s.speaker}' is not in the declared characters: {list(char_names)}")
        return self


class CriticReview(BaseModel):
    score: float = Field(..., ge=1.0, le=10.0)
    hook_strength: float = Field(..., ge=1.0, le=10.0)
    joke_quality: float = Field(..., ge=1.0, le=10.0)
    pacing: float = Field(..., ge=1.0, le=10.0)
    variety: float = Field(..., ge=1.0, le=10.0)
    weakest_scene_index: Optional[int] = Field(default=None, ge=1, le=20)
    revision_instructions: Optional[str] = Field(default=None, max_length=500)


@dataclass
class WordTiming:
    word: str
    start_time: float
    end_time: float


@dataclass
class SceneAudio:
    scene_index: int
    audio_path: Path
    duration_seconds: float
    scene_total_duration: float
    word_timings: List[WordTiming]


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """Sanitizes text for safe use as a filename across Windows/Linux/macOS."""
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)
    clean = re.sub(r"\s+", "_", clean).strip("_.-")
    clean = re.sub(r"[^\w\-.]", "", clean)
    if not clean:
        clean = "toon_short"
    return clean[:max_length]
