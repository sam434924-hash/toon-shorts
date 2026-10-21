"""
Purpose: Static framing motion plugin without dynamic pan or zoom.
Inputs: CameraMove enums and duration in seconds.
Outputs: Basic FFmpeg scale and pad filter chain string.
Depends on: core.models, core.registry
Used by: None
Config keys: None
Tests: tests/contract/test_motion_contract.py
"""

from toonshorts.core.models import CameraMove
from toonshorts.core.registry import MotionInterface, register_motion


@register_motion("static")
class StaticMotionPlugin(MotionInterface):
    """Static framing motion plugin maintaining fixed 9:16 aspect ratio."""
    name = "static"

    def get_filter_chain(self, camera_move: CameraMove, duration_seconds: float) -> str:
        return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
