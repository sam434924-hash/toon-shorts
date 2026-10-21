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
