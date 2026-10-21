"""Contract tests for MotionInterface implementations."""

import pytest
from toonshorts.core.registry import list_motions, get_motion, MotionInterface
from toonshorts.core.models import CameraMove


@pytest.mark.parametrize("plugin_name", list_motions())
def test_motion_contract(plugin_name):
    """Every Motion plugin must fulfill the MotionInterface contract."""
    motion = get_motion(plugin_name)
    assert isinstance(motion, MotionInterface)
    assert motion.name == plugin_name

    duration = 3.5
    for move in CameraMove:
        filter_str = motion.get_filter_chain(move, duration)
        assert isinstance(filter_str, str)
        assert len(filter_str.strip()) > 0
        assert "1080" in filter_str or "scale" in filter_str
