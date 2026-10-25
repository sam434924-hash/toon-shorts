"""
Purpose: Data schemas for screenplay direction, audio timing, and review.
Inputs: Raw dictionary definitions or keyword arguments.
Outputs: Validated Pydantic models, enums, dataclasses, and safe filenames.
Depends on: dataclasses, enum, pathlib, pydantic, re, typing
Used by: brief, core, core.assembler, core.board_objects, core.client, core.cost, core.layout_planner, core.pipeline, core.registry, core.schemas, core.subtitles, core.sync, core.validator, core.visuals, inventory, models, plugins.graphics.kinetic_words, plugins.llm.fake, plugins.llm.gemini, plugins.motion.ffmpeg, plugins.motion.static, plugins.render.animejs.annotations, plugins.render.animejs.cast, plugins.render.animejs.html_builder, plugins.render.animejs.plugin, plugins.render.animejs.visual_renderer, plugins.render.blender3d, plugins.render.cairo, plugins.render.fake, plugins.render.gemini, plugins.render.pillow, plugins.voice.fake, plugins.voice.gemini_tts, plugins.voice.piper, plugins.voice.windows_sapi, voice, voice_utils
Config keys: None
Tests: tests/unit/test_sanitizing.py, tests/unit/test_validation.py, tests/unit/test_v2_validation.py
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanValidationError(ValueError):
    """Raised when a ScriptPlan breaks v1 or v2 validation or directing rules."""
    def __init__(self, message: str, scene_number: Optional[int] = None, field: Optional[str] = None):
        super().__init__(message)
        self.scene_number = scene_number
        self.field = field


def strip_speaker_label(text: str) -> str:
    """
    Strips leading speaker label prefixes like 'Boy:', 'Girl:', 'Presenter:', etc.
    Ensures speaker labels never contaminate dialogue, subtitles, kinetic text, or board cards.
    """
    if not text:
        return ""
    return re.sub(r"^(?:Boy|Girl|Presenter|Host|Speaker|[A-Za-z0-9_-]+)\s*:\s*", "", text.strip(), flags=re.IGNORECASE).strip()


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
    model_config = ConfigDict(extra="forbid")

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


class Shot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: float = Field(..., ge=0.0)
    end: float = Field(..., gt=0.0)
    type: Literal["wide", "close_up"] = Field(...)
    target: Optional[str] = Field(default=None, max_length=30)
    zoom: float = Field(default=1.0)
    ease_in: float = Field(default=0.5)
    ease_out: float = Field(default=0.5)


class Visual(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = Field(default=None, max_length=40)
    type: str = Field(..., min_length=1, max_length=30)
    trigger_word: str = Field(..., min_length=1, max_length=30)
    params: Dict[str, Any] = Field(default_factory=dict)


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_number: int = Field(..., ge=1, le=20)
    speaker: str = Field(..., min_length=1, max_length=30)
    dialogue_line: str = Field(..., min_length=1, max_length=250)
    action: str = Field(..., min_length=1, max_length=200)
    pose: Pose = Field(default=Pose.IDLE)
    camera_move: CameraMove = Field(default=CameraMove.STATIC)
    transition: Transition = Field(default=Transition.CUT)
    is_punchline: bool = Field(default=False)
    gesture: Optional[str] = Field(default=None, max_length=30)
    cast: Optional[List[str]] = Field(default=None)
    layout: Optional[Union[str, Dict[str, Any]]] = Field(default="cards")
    shots: Optional[List[Shot]] = Field(default=None)
    visuals: Optional[List[Visual]] = Field(default=None)
    board_objects: Optional[List[Dict[str, Any]]] = Field(default=None)
    word_timings: Optional[List[WordTiming]] = Field(default=None)

    @field_validator("dialogue_line", mode="before")
    @classmethod
    def strip_dialogue_speaker_label(cls, v: str) -> str:
        if isinstance(v, str):
            return strip_speaker_label(v)
        return v

    @field_validator("speaker", mode="before")
    @classmethod
    def sanitize_speaker_name(cls, v: str) -> str:
        if isinstance(v, str):
            return re.sub(r"[:\s]+$", "", v.strip())
        return v

    @field_validator("gesture")
    @classmethod
    def validate_gesture(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.lower().strip()
        allowed = {
            "idle", "wave", "point", "explain", "open_hand", "thumbs_up", "shrug",
            "point_board", "point_other", "nod", "head_tilt", "lean_speaker", "listening_reaction"
        }
        if clean not in allowed:
            raise ValueError(f"Invalid gesture '{v}'. Allowed gestures: {sorted(list(allowed))}")
        return clean

    @field_validator("layout")
    @classmethod
    def validate_layout_value(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        val = (v or "cards").lower().strip()
        if val not in ("cards", "stage"):
            raise ValueError(f"layout must be 'cards' or 'stage' (got '{v}')")
        return val


class ScriptPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1, le=2)
    title: str = Field(..., min_length=1, max_length=80)
    art_style: str = Field(..., min_length=1, max_length=50)
    emotional_arc: str = Field(..., min_length=5, max_length=200)
    characters: List[Character] = Field(..., min_length=2, max_length=3)
    scenes: List[Scene] = Field(..., min_length=4, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def adapt_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "version" not in data:
                data["version"] = 1
        return data

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
    revision_instructions: Optional[str] = Field(default=None, max_length=1500)


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


WINDOWS_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


def sanitize_filename(
    title: str,
    max_length: int = 100,
    default_name: str = "toon_short",
) -> str:
    """Sanitizes text for safe use as a filename across Windows/Linux/macOS.

    - Blocks Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) case-insensitively,
      including when followed by an extension (e.g. con.txt, nul.mp4).
    - Strips path separators ('/', '\\') and directory traversal sequences ('..').
    - Removes control characters and illegal filesystem characters.
    - Strips trailing dots and spaces.
    - Caps length to max_length (default 100 chars).
    - Falls back to safe default name if the result is empty or reserved.
    """
    if not title:
        return default_name

    clean = str(title)

    # 1. Strip control characters (\x00-\x1f, \x7f-\x9f)
    clean = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", clean)

    # 2. Strip path separators and traversal '..'
    clean = clean.replace("/", "").replace("\\", "")
    while ".." in clean:
        clean = clean.replace("..", "")

    # 3. Remove illegal filesystem characters (< > : " | ? *)
    clean = re.sub(r'[<>:"|?*]', "", clean)

    # 4. Strip trailing dots and spaces before converting whitespace
    clean = clean.rstrip(". ")

    # 5. Replace whitespace sequences with underscore
    clean = re.sub(r"\s+", "_", clean)

    # 6. Keep only word characters, dashes, and dots
    clean = re.sub(r"[^\w\-.]", "", clean)

    # 7. Strip trailing dots, spaces, and underscores
    clean = clean.rstrip(". _")

    # 8. Cap length to max_length
    if len(clean) > max_length:
        clean = clean[:max_length].rstrip(". _")

    # 9. Fallback to default name if empty
    if not clean:
        return default_name

    # 10. Block Windows reserved device names case-insensitively (including with extensions)
    stem = clean.split(".")[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        return default_name

    return clean


SAFE_VIDEO_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


def sanitize_video_name(name: str, max_length: int = 64) -> str:
    """Sanitizes a video name strictly enforcing alphanumeric, dash, and underscore characters.

    - Strips all special characters, directory traversal sequences, and path separators.
    - Capped to max_length (default 64).
    - Blocks Windows reserved device names.
    - Rejects names that resolve to empty or invalid characters.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Video name cannot be empty")

    clean = name.strip()
    # Normalize path traversal and separators
    clean = clean.replace("/", "_").replace("\\", "_")
    # Replace whitespace and illegal characters with underscores
    clean = re.sub(r"[^\w\-]", "_", clean)
    clean = re.sub(r"_+", "_", clean)
    clean = re.sub(r"-+", "-", clean).strip("_-")

    if not clean:
        raise ValueError("Video name cannot be empty or solely special characters")

    if len(clean) > max_length:
        clean = clean[:max_length].rstrip("_-")

    if not clean or not SAFE_VIDEO_NAME_REGEX.match(clean):
        raise ValueError(f"Invalid video name '{name}'. Only alphanumeric, dash, and underscore allowed.")

    stem = clean.split(".")[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        raise ValueError(f"Video name '{name}' is a reserved system name")

    return clean


def resolve_video_dir(name: str, base_dir: Optional[Path] = None) -> Path:
    """Resolves video directory and ensures it strictly resides inside the base videos directory."""
    from toonshorts.core import paths
    target_base = (base_dir or paths.VIDEOS_DIR).resolve()
    clean_name = sanitize_video_name(name)
    target_dir = (target_base / clean_name).resolve()
    if target_dir.parent != target_base:
        raise ValueError(f"Video name '{name}' resolves outside target directory '{target_base}'")
    return target_dir


class CharacterManifestItem(BaseModel):
    name: str
    pack: Optional[str] = None
    version: str = "1.0.0"


class VoiceManifestItem(BaseModel):
    engine: str
    voice_name: str
    model: Optional[str] = None


class VideoManifest(BaseModel):
    video_name: str
    created_at: str
    style: str
    characters: List[CharacterManifestItem]
    voice: VoiceManifestItem
    library_pieces_used: List[str] = Field(default_factory=list)
    tool_versions: Dict[str, str] = Field(default_factory=dict)
    level2_custom_visuals: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[Any] = Field(default_factory=list)
    images: List[Dict[str, Any]] = Field(default_factory=list)

