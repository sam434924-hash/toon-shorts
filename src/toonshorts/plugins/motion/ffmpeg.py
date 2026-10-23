"""
Purpose: Mathematical FFmpeg filter chain motion plugin for camera moves.
Inputs: CameraMove enums and duration in seconds.
Outputs: Predefined mathematical FFmpeg video filter strings.
Depends on: core.config, core.models, core.registry
Used by: None
Config keys: VIDEO_FPS
Tests: tests/contract/test_motion_contract.py
"""

from toonshorts.core import config
from toonshorts.core.models import CameraMove
from toonshorts.core.registry import MotionInterface, register_motion


@register_motion("ffmpeg")
class FFmpegMotionPlugin(MotionInterface):
    """Dynamic camera motions implemented via FFmpeg zoompan filter chains."""
    name = "ffmpeg"

    def get_filter_chain(self, camera_move: CameraMove, duration_seconds: float) -> str:
        fps = config.VIDEO_FPS
        frames = max(int(duration_seconds * fps), 1)

        if camera_move == CameraMove.ZOOM_IN:
            return (
                f"scale=1080:1920,"
                f"zoompan=z='min(zoom+0.0012,1.15)':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
            )
        elif camera_move == CameraMove.ZOOM_OUT:
            return (
                f"scale=1080:1920,"
                f"zoompan=z='max(1.15-0.0012*on,1.0)':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
            )
        elif camera_move == CameraMove.PAN_LEFT:
            return (
                f"scale=1080:1920,"
                f"zoompan=z=1.15:d={frames}:"
                f"x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
            )
        elif camera_move == CameraMove.PAN_RIGHT:
            return (
                f"scale=1080:1920,"
                f"zoompan=z=1.15:d={frames}:"
                f"x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps}"
            )
        elif camera_move == CameraMove.SHAKE:
            return (
                f"scale=1080:1920,"
                f"zoompan=z=1.08:d={frames}:"
                f"x='(iw-iw/zoom)/2+18*sin(on*2.5)':y='(ih-ih/zoom)/2+18*cos(on*3.1)':s=1080x1920:fps={fps}"
            )
        else:
            return (
                f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
            )

    def get_shot_filter_chain(
        self,
        shot_type: str,
        target: str,
        duration_seconds: float,
        zoom_amount: float = config.CAMERA_ZOOM_SPEAKER,
        ease_duration: float = config.CAMERA_EASE_DURATION_SEC,
    ) -> str:
        """
        Builds a smooth zoompan filter string for targeted camera motion:
        - target == 'speaker_left': eases into left character slot and returns
        - target == 'speaker_right': eases into right character slot and returns
        - target == 'board': eases into the top board panel and returns
        """
        fps = config.VIDEO_FPS
        frames = max(int(duration_seconds * fps), 1)
        ease_frames = max(int(ease_duration * fps), 1)
        hold_frames = max(frames - 2 * ease_frames, 1)

        # Center coordinates for pan/zoom
        if target in ("speaker_left", "boy_b", "left"):
            cx, cy = 0.32, 0.65
        elif target in ("speaker_right", "girl_a", "right"):
            cx, cy = 0.68, 0.65
        elif target in ("board", "screen"):
            cx, cy = 0.50, 0.32
        else:
            cx, cy = 0.50, 0.50

        # Mathematical easing: smooth sine curve between 1.0 and zoom_amount
        z_expr = (
            f"if(lte(on,{ease_frames}), 1.0 + ({zoom_amount - 1.0})*sin(on/{ease_frames}*PI/2), "
            f"if(lte(on,{ease_frames + hold_frames}), {zoom_amount}, "
            f"1.0 + ({zoom_amount - 1.0})*cos((on-{ease_frames + hold_frames})/{ease_frames}*PI/2)))"
        )
        x_expr = f"(iw*{cx} - iw/zoom/2)"
        y_expr = f"(ih*{cy} - ih/zoom/2)"

        return (
            f"scale=1080:1920,"
            f"zoompan=z='{z_expr}':d={frames}:x='{x_expr}':y='{y_expr}':s=1080x1920:fps={fps}"
        )
