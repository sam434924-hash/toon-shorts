"""
Purpose: Octopus vector line-art drawing plugin.
Inputs: Start timing, stroke color, arm numbering option, and canvas sizing.
Outputs: Clean flat vector octopus SVG with 8 curved arms, round head, eyes, and arm numbering.
Depends on: html, typing, plugins.graphics.draw_svg
Used by: plugins.graphics
Config keys: None
Tests: tests/unit/test_graphics_plugins.py
"""

from typing import Any, Dict, List, Optional
from toonshorts.plugins.graphics.draw_svg import DrawSVGPlugin


class OctopusVectorPlugin:
    """Plugin for rendering clean vector line-art octopus with 8 curved arms and arm numbering."""
    name = "octopus_vector"

    # Precise hand-crafted vector paths for a friendly flat cartoon octopus (viewBox 0 0 700 450)
    HEAD_PATH = "M 350,70 C 270,70 210,130 210,210 C 210,265 245,295 285,310 C 315,322 385,322 415,310 C 455,295 490,265 490,210 C 490,130 430,70 350,70 Z"
    EYE_LEFT_PATH = "M 305,190 A 15,18 0 1,0 305,226 A 15,18 0 1,0 305,190"
    EYE_RIGHT_PATH = "M 395,190 A 15,18 0 1,0 395,226 A 15,18 0 1,0 395,190"
    SMILE_PATH = "M 325,250 Q 350,275 375,250"

    # 8 distinct curved arms spreading outward gracefully
    ARMS = [
        # Arm 1: far left looping up
        "M 245,295 C 190,320 120,300 80,240 C 60,210 75,175 110,185 C 135,192 140,225 115,245",
        # Arm 2: mid-left sweeping out
        "M 265,305 C 195,355 125,370 75,340 C 40,320 45,280 80,270 C 110,260 125,295 95,315",
        # Arm 3: lower-left curving down
        "M 290,315 C 220,380 160,420 120,400 C 85,385 100,345 135,345 C 165,345 175,380 145,395",
        # Arm 4: inner-left down curl
        "M 320,320 C 275,390 230,440 190,430 C 160,420 170,380 205,375 C 235,370 245,405 215,420",
        # Arm 5: inner-right down curl
        "M 380,320 C 425,390 470,440 510,430 C 540,420 530,380 495,375 C 465,370 455,405 485,420",
        # Arm 6: lower-right curving down
        "M 410,315 C 480,380 540,420 580,400 C 615,385 600,345 565,345 C 535,345 525,380 555,395",
        # Arm 7: mid-right sweeping out
        "M 435,305 C 505,355 575,370 625,340 C 660,320 655,280 620,270 C 590,260 575,295 605,315",
        # Arm 8: far right looping up
        "M 455,295 C 510,320 580,300 620,240 C 640,210 625,175 590,185 C 565,192 560,225 585,245",
    ]

    ARM_TIP_COORDS = [
        (115, 235),
        (95, 305),
        (145, 385),
        (215, 410),
        (485, 410),
        (555, 385),
        (605, 305),
        (585, 235),
    ]

    @classmethod
    def render(
        cls,
        element_id: str,
        start_ms: int = 0,
        duration_ms: int = 1200,
        stroke_color: str = "#38bdf8",
        show_numbers: bool = False,
        numbers_start_ms: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Renders vector octopus with animated stroke drawing and optional arm number pop-in badges."""
        all_paths = [cls.HEAD_PATH] + cls.ARMS + [cls.EYE_LEFT_PATH, cls.EYE_RIGHT_PATH, cls.SMILE_PATH]

        # Extra content: pupils and optional arm badges (1..8)
        extra_svg_elements = [
            '<circle cx="308" cy="208" r="6" fill="#38bdf8" />',
            '<circle cx="398" cy="208" r="6" fill="#38bdf8" />',
        ]

        if show_numbers:
            for idx, (tx, ty) in enumerate(cls.ARM_TIP_COORDS):
                arm_num = idx + 1
                badge_id = f"{element_id}-arm-badge-{arm_num}"
                extra_svg_elements.append(
                    f'<g id="{badge_id}" class="arm-num-badge" opacity="0">\n'
                    f'  <circle cx="{tx}" cy="{ty}" r="18" fill="#0f172a" stroke="#38bdf8" stroke-width="3" />\n'
                    f'  <text x="{tx}" y="{ty+6}" fill="#38bdf8" font-size="18" font-weight="900" '
                    f'text-anchor="middle" font-family="sans-serif">{arm_num}</text>\n'
                    f'</g>'
                )

        draw_result = DrawSVGPlugin.render(
            element_id=element_id,
            svg_paths=all_paths,
            view_box="0 0 700 450",
            stroke_color=stroke_color,
            stroke_width=4,
            fill_color="none",
            start_ms=start_ms,
            duration_ms=duration_ms,
            extra_content="\n".join(extra_svg_elements),
        )

        draw_result["descriptor"]["show_numbers"] = show_numbers
        draw_result["descriptor"]["numbers_start_ms"] = numbers_start_ms or (start_ms + 600)
        draw_result["descriptor"]["arm_count"] = 8

        return draw_result
