"""
Purpose: HTML5 / Anime.js whiteboard rendering plugin conforming to RenderInterface.
Inputs: Screenplay plans, character manifests, audio tracks, and style configurations.
Outputs: Generated scene video clips and still images.
Depends on: core.config, core.models, core.registry, logging, pathlib, plugins.render.animejs.annotations, plugins.render.animejs.capture, plugins.render.animejs.cast, plugins.render.animejs.html_builder, typing
Used by: plugins.render.animejs
Config keys: VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/contract/test_render_contract.py, tests/unit/test_animejs.py
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from toonshorts.core import config
from toonshorts.core.models import Character, Scene, ScriptPlan, SceneAudio
from toonshorts.core.registry import RenderInterface, register_renderer
from toonshorts.plugins.render.animejs.annotations import extract_whiteboard_content_and_annotations
from toonshorts.plugins.render.animejs.capture import capture_still_frame, render_whiteboard_video
from toonshorts.plugins.render.animejs.cast import build_characters_data, resolve_scene_cast
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html

logger = logging.getLogger(__name__)


@register_renderer("animejs")
class AnimeJSRenderPlugin(RenderInterface):
    """HTML5 / Anime.js code-driven whiteboard rendering engine with Rough.js hand-drawn sketches and character mouth sync."""

    @property
    def name(self) -> str:
        return "animejs"

    def render_scene(
        self,
        scene: Scene,
        characters: List[Character],
        style_preset: Dict[str, Any],
        output_path: Path,
        temp_dir: Path,
        char_refs: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """Renders a single still scene image frame at the completion state of the animation."""
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        duration_sec = 2.5
        title, words_data, annotations = extract_whiteboard_content_and_annotations(scene, duration_sec)

        scene_gesture = getattr(scene, "gesture", None) or "idle"
        scene_cast = resolve_scene_cast(scene, characters)
        characters_data = build_characters_data(
            scene_cast,
            scene=scene,
            style_preset=style_preset,
        )

        html_str = generate_whiteboard_html(
            title=title,
            words=words_data,
            duration_sec=duration_sec,
            mouth_cues=[False] * int(duration_sec * config.VIDEO_FPS),
            gesture=scene_gesture,
            width=config.VIDEO_WIDTH,
            height=config.VIDEO_HEIGHT,
            scene_number=scene.scene_number,
            annotations=annotations,
            characters_data=characters_data,
        )

        html_file = (temp_dir / f"animejs_scene_{scene.scene_number}.html").resolve()
        html_file.write_text(html_str, encoding="utf-8")

        return capture_still_frame(
            html_file=html_file,
            output_path=output_path,
            duration_sec=duration_sec,
            width=config.VIDEO_WIDTH,
            height=config.VIDEO_HEIGHT,
        )

    def render_whiteboard_video(
        self,
        title: str,
        words: List[Dict[str, Any]],
        audio_path: Optional[Path],
        output_path: Path,
        duration_sec: float = 3.0,
        gesture: str = "idle",
        fps: int = config.VIDEO_FPS,
        temp_dir: Optional[Path] = None,
        scene_number: int = 1,
        annotations: Optional[List[Dict[str, Any]]] = None,
        characters_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """
        Renders a fully animated MP4 video with easing transitions synced to an audio clip.
        Mouth flapping is driven by voice audio loudness (RMS).
        Character exhibits subtle idle motion.
        Streams Playwright frames directly into FFmpeg stdin.
        """
        return render_whiteboard_video(
            title=title,
            words=words,
            audio_path=audio_path,
            output_path=output_path,
            duration_sec=duration_sec,
            gesture=gesture,
            fps=fps,
            temp_dir=temp_dir,
            scene_number=scene_number,
            annotations=annotations,
            characters_data=characters_data,
            width=config.VIDEO_WIDTH,
            height=config.VIDEO_HEIGHT,
        )

    def render_all_scenes(
        self,
        plan: ScriptPlan,
        style_preset: Dict[str, Any],
        temp_dir: Path,
        character_refs: Optional[Dict[str, Path]] = None,
        scene_audios: Optional[List[SceneAudio]] = None,
    ) -> List[Path]:
        """
        Renders scenes for the screenplay plan.
        If scene_audios is provided, generates animated MP4 video clips with mouth sync and idle motion.
        Otherwise renders still PNG frames.
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        results = []

        if scene_audios and len(scene_audios) == len(plan.scenes):
            for i, (scene, audio) in enumerate(zip(plan.scenes, scene_audios)):
                clip_path = temp_dir / f"animejs_scene_{scene.scene_number}.mp4"
                title, words, annotations = extract_whiteboard_content_and_annotations(
                    scene, audio.scene_total_duration, audio.word_timings
                )
                scene_gesture = getattr(scene, "gesture", None) or "idle"
                scene_cast = resolve_scene_cast(scene, plan.characters)
                characters_data = build_characters_data(
                    scene_cast,
                    scene=scene,
                    style_preset=style_preset,
                )
                self.render_whiteboard_video(
                    title=title,
                    words=words,
                    audio_path=audio.audio_path,
                    output_path=clip_path,
                    duration_sec=audio.scene_total_duration,
                    gesture=scene_gesture,
                    fps=config.VIDEO_FPS,
                    temp_dir=temp_dir / f"scene_{scene.scene_number}_tmp",
                    scene_number=scene.scene_number,
                    annotations=annotations,
                    characters_data=characters_data,
                )
                results.append(clip_path)
        else:
            for scene in plan.scenes:
                out_path = temp_dir / f"animejs_scene_{scene.scene_number}.png"
                self.render_scene(scene, plan.characters, style_preset, out_path, temp_dir)
                results.append(out_path)

        return results
