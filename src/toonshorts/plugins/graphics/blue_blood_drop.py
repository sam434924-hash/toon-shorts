"""
Purpose: Pop-in blue blood droplet graphic plugin (blue_blood_drop).
Inputs: Start timing, droplet size, and labeling.
Outputs: Stylized glowing blue blood droplet SVG and animated Anime.js keyframes.
Depends on: html, typing
Used by: plugins.graphics
Config keys: None
Tests: tests/unit/test_graphics_plugins.py
"""

from typing import Any, Dict, Optional


class BlueBloodDropPlugin:
    """Plugin for rendering a stylized glowing blue blood drop popping in on speech cue."""
    name = "blue_blood_drop"

    DROP_PATH = "M 100,20 C 100,20 170,110 170,150 C 170,190 140,220 100,220 C 60,220 30,190 30,150 C 30,110 100,20 100,20 Z"
    HIGHLIGHT_PATH = "M 75,130 C 70,145 75,175 95,190 C 85,185 80,165 82,140 Z"

    @classmethod
    def render(
        cls,
        element_id: str,
        start_ms: int = 0,
        duration_ms: int = 600,
        label: str = "Copper Hemocyanin",
        sub_label: str = "Vivid Blue Blood",
        **kwargs,
    ) -> Dict[str, Any]:
        """Builds glowing blue blood droplet SVG with pop and ripple animation."""
        html_markup = (
            f'<div id="{element_id}" class="blue-drop-container" style="display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 320px; opacity: 0; transform: scale(0);">\n'
            f'  <svg viewBox="0 0 200 240" class="blue-drop-svg" style="width: 170px; height: 204px; filter: drop-shadow(0 0 30px rgba(56, 189, 248, 0.7));">\n'
            f'    <defs>\n'
            f'      <linearGradient id="{element_id}-grad" x1="0%" y1="0%" x2="100%" y2="100%">\n'
            f'        <stop offset="0%" stop-color="#38bdf8" />\n'
            f'        <stop offset="100%" stop-color="#0284c7" />\n'
            f'      </linearGradient>\n'
            f'    </defs>\n'
            f'    <path d="{cls.DROP_PATH}" fill="url(#{element_id}-grad)" />\n'
            f'    <path d="{cls.HIGHLIGHT_PATH}" fill="#ffffff" opacity="0.45" />\n'
            f'  </svg>\n'
            f'  <div style="color: #38bdf8; font-size: 32px; font-weight: 900; margin-top: 14px; letter-spacing: -0.01em;">{label}</div>\n'
            f'  <div style="color: #94a3b8; font-size: 22px; font-weight: 600; margin-top: 4px;">{sub_label}</div>\n'
            f'</div>'
        )

        css_rules = f"""
#{element_id} {{
  will-change: transform, opacity;
}}
"""
        js_descriptor = {
            "target": f"#{element_id}",
            "type": "blue_blood_drop",
            "start_ms": start_ms,
            "duration_ms": duration_ms,
        }

        return {
            "html": html_markup,
            "css": css_rules,
            "descriptor": js_descriptor,
        }
