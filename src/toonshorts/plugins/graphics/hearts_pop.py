"""
Purpose: Pop-in bouncy heart icons plugin (hearts_pop).
Inputs: Number of hearts, start timings, colors, and layout spacing.
Outputs: Spring-bounce animated SVG hearts for cardiac facts.
Depends on: html, typing
Used by: plugins.graphics
Config keys: None
Tests: tests/unit/test_graphics_plugins.py
"""

from typing import Any, Dict, List, Optional


class HeartsPopPlugin:
    """Plugin for spring bounce animated pop-in heart icons."""
    name = "hearts_pop"

    # Smooth vector heart path inside 100x100 viewBox
    HEART_PATH = "M 50,28 C 50,15 35,5 20,5 C 8,5 0,16 0,30 C 0,55 35,75 50,92 C 65,75 100,55 100,30 C 100,16 92,5 80,5 C 65,5 50,15 50,28 Z"

    @classmethod
    def render(
        cls,
        element_id: str,
        count: int = 3,
        start_ms: int = 0,
        duration_ms: int = 600,
        stagger_ms: int = 240,
        color: str = "#ef4444",
        glow_color: str = "rgba(239, 68, 68, 0.4)",
        labels: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Builds 1 to 3 pop-in bouncy hearts with glowing gradient and optional labels."""
        heart_items = []
        for i in range(count):
            h_id = f"{element_id}-heart-{i+1}"
            lbl = labels[i] if labels and i < len(labels) else f"Heart {i+1}"
            heart_items.append(
                f'<div id="{h_id}" class="heart-item" style="opacity: 0; transform: scale(0);">'
                f'  <svg viewBox="0 0 100 100" class="heart-svg" style="width: 110px; height: 110px; filter: drop-shadow(0 0 18px {glow_color});">'
                f'    <path d="{cls.HEART_PATH}" fill="{color}" />'
                f'  </svg>'
                f'  <div class="heart-label" style="color: #f8fafc; font-size: 22px; font-weight: 700; margin-top: 10px; text-align: center;">{lbl}</div>'
                f'</div>'
            )

        html_markup = (
            f'<div id="{element_id}" class="hearts-pop-container" style="display: flex; align-items: center; justify-content: center; gap: 40px; width: 100%; height: 260px; margin-top: 20px;">\n'
            f'  {"".join(heart_items)}\n'
            f'</div>'
        )

        css_rules = f"""
#{element_id} .heart-item {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  will-change: transform, opacity;
}}
"""
        js_descriptor = {
            "target": f"#{element_id}",
            "type": "hearts_pop",
            "count": count,
            "start_ms": start_ms,
            "stagger_ms": stagger_ms,
        }

        return {
            "html": html_markup,
            "css": css_rules,
            "descriptor": js_descriptor,
        }
