"""
Purpose: Stroke-by-stroke SVG drawing plugin (draw_svg).
Inputs: SVG paths, stroke width, stroke color, trigger timing, and canvas sizing.
Outputs: SVG container with path length calculation and stroke-dashoffset animation.
Depends on: html, typing
Used by: plugins.graphics, plugins.graphics.octopus_vector
Config keys: None
Tests: tests/unit/test_graphics_plugins.py
"""

import html
from typing import Any, Dict, List, Optional


class DrawSVGPlugin:
    """Plugin for stroke-by-stroke SVG vector path drawing animations."""
    name = "draw_svg"

    @classmethod
    def render(
        cls,
        element_id: str,
        svg_paths: List[str],
        view_box: str = "0 0 600 400",
        stroke_color: str = "#38bdf8",
        stroke_width: int = 4,
        fill_color: str = "none",
        start_ms: int = 0,
        duration_ms: int = 1000,
        extra_content: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Builds SVG markup with animated stroke-dashoffset path styling and Anime.js descriptor.
        """
        paths_html = []
        for idx, p_d in enumerate(svg_paths):
            paths_html.append(
                f'<path class="draw-path draw-path-{idx}" d="{p_d}" '
                f'fill="{fill_color}" stroke="{stroke_color}" stroke-width="{stroke_width}" '
                f'stroke-linecap="round" stroke-linejoin="round" />'
            )

        html_markup = (
            f'<div id="{element_id}" class="draw-svg-container">\n'
            f'  <svg viewBox="{view_box}" class="draw-svg-element" style="width: 100%; height: 100%;">\n'
            f'    {"".join(paths_html)}\n'
            f'    {extra_content}\n'
            f'  </svg>\n'
            f'</div>'
        )

        css_rules = f"""
#{element_id} {{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 380px;
  position: relative;
  opacity: 0;
}}
#{element_id} .draw-path {{
  stroke-dasharray: 1200;
  stroke-dashoffset: 1200;
  transition: stroke 0.3s ease;
}}
"""
        js_descriptor = {
            "target": f"#{element_id}",
            "type": "draw_svg",
            "start_ms": start_ms,
            "duration_ms": duration_ms,
            "path_count": len(svg_paths),
        }

        return {
            "html": html_markup,
            "css": css_rules,
            "descriptor": js_descriptor,
        }
