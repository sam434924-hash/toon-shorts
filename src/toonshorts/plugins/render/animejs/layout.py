"""
Purpose: Layout constants, safe area bounds, and studio room SVG decorations.
Inputs: Scene identifiers, viewport dimensions, and gesture names.
Outputs: Coordinate boundaries and static SVG decoration elements.
Depends on: core.config, plugins.render.animejs.gestures, typing
Used by: plugins.render.animejs, plugins.render.animejs.html_builder
Config keys: VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py
"""

from typing import Dict, Tuple

from toonshorts.core import config
from toonshorts.plugins.render.animejs.gestures import sanitize_gesture

# Video composition layout & Safe Area boundaries (9:16 vertical 1080x1920)
SAFE_AREA = {
    "min_x": 50.0,
    "max_x": 1030.0,
    "min_y": 50.0,
    "max_y": 1870.0,
}

CHAR_RIG_LAYOUT = {
    "left": 75.0,
    "top": 670.0,
    "width": 560.0,
    "height": 630.0,
}

SUBTITLE_STRIP = getattr(
    config,
    "NIGHT_STUDIO_SUBTITLE_STRIP",
    {
        "top": 1640.0,
        "bottom": 1860.0,
        "left": 60.0,
        "right": 1020.0,
        "margin_v": 120,
        "font_size": 76,
        "max_lines": 2,
    },
)


def verify_subtitle_strip_clearance(theme: str = "night_studio") -> bool:
    """
    Verifies that the reserved subtitle strip is strictly clear of any
    board frame, character visible area, desk edge/props, or lamps.
    """
    strip_top = float(SUBTITLE_STRIP["top"])
    strip_bottom = float(SUBTITLE_STRIP["bottom"])

    # 1. Whiteboard boundary check (top: 65, height: 980 -> bottom: 1045)
    board_bottom = 1045.0
    if board_bottom > strip_top:
        return False

    # 2. Desk props boundary check (props top: 1420, height: 130 -> bottom: 1550)
    desk_props_bottom = 1550.0
    if desk_props_bottom > strip_top:
        return False

    # 3. Desk bevel/surface boundary check (top: 1540, surface height: 38 -> bottom: 1578)
    desk_surface_bottom = 1578.0
    if desk_surface_bottom > strip_top:
        return False

    # 4. Character visible bounds: characters seated behind desk (legs hidden below desk surface 1540)
    char_visible_bottom = 1540.0
    if char_visible_bottom > strip_top:
        return False

    # 5. Check safe area bounds
    if strip_top < SAFE_AREA["min_y"] or strip_bottom > SAFE_AREA["max_y"]:
        return False

    return True


def generate_scene_decorations(scene_number: int = 1, theme: str = "whiteboard") -> Tuple[str, str]:
    """
    Generates consistent SVG studio wall fixtures and foreground desk props.
    Supports themes:
    - 'whiteboard': Classic daytime whiteboard studio.
    - 'night_studio': Night coding studio with navy wall, LED strips, city window, warm lamp, and desk props.
    """
    if theme == "night_studio":
        # Night Studio Wall Decor: City skyline window, vertical glowing purple & blue LED strips, shelf, lamp, plant
        shelf_svg = """
    <!-- Night Studio Vertical Purple and Blue LED Light Strips -->
    <div class="led-strip led-strip-purple" style="position: absolute; top: 40px; left: 35px; width: 8px; height: 1100px; background: #c084fc; border-radius: 4px; box-shadow: 0 0 25px #a855f7, 0 0 50px #9333ea; z-index: 1;"></div>
    <div class="led-strip led-strip-blue" style="position: absolute; top: 40px; right: 35px; width: 8px; height: 1100px; background: #38bdf8; border-radius: 4px; box-shadow: 0 0 25px #0284c7, 0 0 50px #0369a1; z-index: 1;"></div>

    <!-- Night City Window with Twinkling Windows (Behind Desk / Beside Board) -->
    <svg viewBox="0 0 160 280" style="position: absolute; top: 750px; left: 460px; width: 160px; height: 280px; z-index: 1; opacity: 0.85;">
      <rect x="0" y="0" width="160" height="280" rx="10" fill="#020617" stroke="#1e293b" stroke-width="6"/>
      <!-- Skyline silhouette -->
      <rect x="15" y="80" width="35" height="195" fill="#0f172a"/>
      <rect x="55" y="45" width="45" height="230" fill="#0b1120"/>
      <rect x="105" y="110" width="40" height="165" fill="#0f172a"/>
      <!-- Small lit windows -->
      <rect class="city-win win-1" x="22" y="95" width="6" height="8" rx="1" fill="#fbbf24"/>
      <rect class="city-win win-2" x="35" y="125" width="6" height="8" rx="1" fill="#fde68a"/>
      <rect class="city-win win-3" x="22" y="155" width="6" height="8" rx="1" fill="#38bdf8"/>
      <rect class="city-win win-4" x="65" y="60" width="8" height="10" rx="1" fill="#fbbf24"/>
      <rect class="city-win win-5" x="82" y="85" width="8" height="10" rx="1" fill="#fde68a"/>
      <rect class="city-win win-6" x="65" y="120" width="8" height="10" rx="1" fill="#fbbf24"/>
      <rect class="city-win win-7" x="82" y="150" width="8" height="10" rx="1" fill="#38bdf8"/>
      <rect class="city-win win-8" x="115" y="130" width="6" height="8" rx="1" fill="#fde68a"/>
      <rect class="city-win win-9" x="128" y="160" width="6" height="8" rx="1" fill="#fbbf24"/>
    </svg>

    <!-- Floating Dark Studio Shelf on Right Wall -->
    <div class="studio-shelf" style="top: 710px; left: 810px; width: 210px; background: #1e293b; box-shadow: 0 10px 25px rgba(0,0,0,0.6);"></div>
    <svg viewBox="0 0 100 90" style="position: absolute; top: 635px; left: 825px; width: 100px; height: 90px; z-index: 3;">
      <rect x="15" y="42" width="28" height="32" rx="4" fill="#0f172a" stroke="#334155" stroke-width="2"/>
      <path d="M 29 42 C 18 24, 6 30, 14 42 Z" fill="#10b981"/>
      <path d="M 29 42 C 34 16, 50 22, 42 42 Z" fill="#059669"/>
      <path d="M 22 50 Q 8 68 14 84" stroke="#047857" stroke-width="3" fill="none" stroke-linecap="round"/>
      <circle cx="14" cy="84" r="4.5" fill="#10b981"/>
      <path d="M 34 52 Q 44 68 40 80" stroke="#047857" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <circle cx="40" cy="80" r="3.5" fill="#059669"/>
      <rect x="52" y="32" width="12" height="42" rx="2" fill="#6366f1"/>
      <rect x="66" y="24" width="14" height="50" rx="2" fill="#ec4899"/>
      <rect x="82" y="36" width="10" height="38" rx="2" fill="#06b6d4"/>
    </svg>"""

        # Night Studio Desk Props: Warm desk lamp, laptop with glowing screen, coffee mug
        desk_svg = """
    <!-- Warm Desk Lamp (Cozy Amber Glow) -->
    <path d="M 120 120 L 160 50 L 180 50" stroke="#475569" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path d="M 170 45 L 210 65 L 185 85 Z" fill="#f59e0b"/>
    <circle cx="195" cy="70" r="24" fill="rgba(251, 191, 36, 0.25)" filter="blur(6px)"/>
    <!-- Glowing Modern Laptop -->
    <rect x="650" y="38" width="180" height="84" rx="6" fill="#1e293b" stroke="#334155" stroke-width="2"/>
    <rect x="660" y="46" width="160" height="68" rx="4" fill="#020617"/>
    <line x1="672" y1="58" x2="730" y2="58" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="70" x2="780" y2="70" stroke="#818cf8" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="82" x2="745" y2="82" stroke="#34d399" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="94" x2="710" y2="94" stroke="#f472b6" stroke-width="4" stroke-linecap="round"/>
    <polygon points="620,122 860,122 840,116 640,116" fill="#334155"/>
    <!-- Matte Navy Coffee Mug with Steam -->
    <rect x="548" y="58" width="46" height="56" rx="8" fill="#1e1e38"/>
    <path d="M 594 70 Q 610 70 610 86 Q 610 100 594 100" stroke="#1e1e38" stroke-width="6" fill="none"/>
    <path d="M 563 50 Q 558 40 563 30" stroke="#64748b" stroke-width="3" stroke-linecap="round" fill="none"/>
    <path d="M 576 50 Q 581 40 576 30" stroke="#64748b" stroke-width="3" stroke-linecap="round" fill="none"/>"""

        return shelf_svg, desk_svg

    shelf_svg = """
    <!-- Floating Studio Shelf on Right Wall (Constant Across All Scenes) -->
    <div class="studio-shelf" style="top: 710px; left: 810px; width: 210px;"></div>
    <svg viewBox="0 0 100 90" style="position: absolute; top: 635px; left: 825px; width: 100px; height: 90px; z-index: 3;">
      <rect x="15" y="42" width="28" height="32" rx="4" fill="#ffffff" stroke="#94a3b8" stroke-width="2"/>
      <path d="M 29 42 C 18 24, 6 30, 14 42 Z" fill="#22c55e"/>
      <path d="M 29 42 C 34 16, 50 22, 42 42 Z" fill="#15803d"/>
      <path d="M 22 50 Q 8 68 14 84" stroke="#16a34a" stroke-width="3" fill="none" stroke-linecap="round"/>
      <circle cx="14" cy="84" r="4.5" fill="#22c55e"/>
      <path d="M 34 52 Q 44 68 40 80" stroke="#16a34a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <circle cx="40" cy="80" r="3.5" fill="#15803d"/>
      <rect x="52" y="32" width="12" height="42" rx="2" fill="#3b82f6"/>
      <rect x="66" y="24" width="14" height="50" rx="2" fill="#f59e0b"/>
      <rect x="82" y="36" width="10" height="38" rx="2" fill="#ec4899"/>
    </svg>"""

    desk_svg = """
    <!-- Constant Foreground Desk Props Across All Scenes -->
    <!-- Modern Laptop with Clean Syntax Lines -->
    <rect x="650" y="38" width="180" height="84" rx="6" fill="#334155"/>
    <rect x="660" y="46" width="160" height="68" rx="4" fill="#090d16"/>
    <line x1="672" y1="58" x2="730" y2="58" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="70" x2="780" y2="70" stroke="#818cf8" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="82" x2="745" y2="82" stroke="#34d399" stroke-width="4" stroke-linecap="round"/>
    <line x1="672" y1="94" x2="710" y2="94" stroke="#f472b6" stroke-width="4" stroke-linecap="round"/>
    <polygon points="620,122 860,122 840,116 640,116" fill="#475569"/>
    <!-- Ceramic Navy Coffee Mug with Steam -->
    <rect x="548" y="58" width="46" height="56" rx="8" fill="#1e3a8a"/>
    <path d="M 594 70 Q 610 70 610 86 Q 610 100 594 100" stroke="#1e3a8a" stroke-width="6" fill="none"/>
    <path d="M 563 50 Q 558 40 563 30" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none"/>
    <path d="M 576 50 Q 581 40 576 30" stroke="#94a3b8" stroke-width="3" stroke-linecap="round" fill="none"/>"""

    return shelf_svg, desk_svg


def build_parallax_background_layers(
    theme: str = "whiteboard",
    style_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Builds 3 oversized multiplane background depth layers (far, mid, near) as pure vector SVG.
    All colors, strokes, and accents match the active style profile exactly.
    Oversized to [-300, 1380] x [-300, 2220] to guarantee zero empty edges at extreme camera moves.
    """
    prof = style_profile or {}
    pal = prof.get("palette") or (
        ["#0b0f19", "#0f172a", "#1e293b", "#38bdf8", "#818cf8"]
        if theme == "night_studio"
        else ["#0f172a", "#f8fafc", "#2563EB", "#F59E0B", "#e2e8f0"]
    )
    outline = prof.get("outline_color") or ("#1e293b" if theme == "night_studio" else "#94a3b8")
    stroke_w = float(prof.get("stroke_width", 5.0))
    highlight = prof.get("highlight_color") or ("#38bdf8" if theme == "night_studio" else "#2563EB")
    bg_main = pal[0] if theme == "night_studio" else (pal[1] if len(pal) > 1 else "#f8fafc")
    bg_deep = "#03060c" if theme == "night_studio" else "#f1f5f9"
    accent = pal[3] if len(pal) > 3 else highlight

    # 1. FAR LAYER (depth 0.08): Deep sky/wall gradient, distant city skyline or architectural verticals
    far_svg = f"""
    <svg class="bg-vector-svg" viewBox="-300 -300 1680 2520" width="1680" height="2520" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="far-grad" cx="50%" cy="30%" r="75%">
          <stop offset="0%" stop-color="{bg_main}" stop-opacity="1.0"/>
          <stop offset="60%" stop-color="{bg_deep}" stop-opacity="1.0"/>
          <stop offset="100%" stop-color="#020408" stop-opacity="1.0"/>
        </radialGradient>
      </defs>
      <!-- Deep Wall Base Surface -->
      <rect x="-300" y="-300" width="1680" height="2520" fill="url(#far-grad)"/>
      <!-- Distant City Skyline / Structural Pillars -->
      <rect x="-150" y="450" width="120" height="1800" fill="{bg_main}" opacity="0.35"/>
      <rect x="50" y="320" width="90" height="1900" fill="{bg_main}" opacity="0.25"/>
      <rect x="420" y="520" width="140" height="1700" fill="{bg_main}" opacity="0.30"/>
      <rect x="920" y="280" width="110" height="1950" fill="{bg_main}" opacity="0.25"/>
      <rect x="1150" y="480" width="130" height="1750" fill="{bg_main}" opacity="0.35"/>
    </svg>"""

    # 2. MID LAYER (depth 0.18): Studio room window, vertical LED strips, acoustic diffusers
    mid_svg = f"""
    <svg class="bg-vector-svg" viewBox="-300 -300 1680 2520" width="1680" height="2520" xmlns="http://www.w3.org/2000/svg">
      <!-- Vertical Architectural Diffuser Battens -->
      <line x1="-120" y1="-200" x2="-120" y2="1800" stroke="{outline}" stroke-width="{stroke_w * 0.8:.1f}" opacity="0.4"/>
      <line x1="1200" y1="-200" x2="1200" y2="1800" stroke="{outline}" stroke-width="{stroke_w * 0.8:.1f}" opacity="0.4"/>
      <!-- Studio Window Frame with lit panes -->
      <g transform="translate(460, 750)">
        <rect x="0" y="0" width="160" height="280" rx="10" fill="{bg_deep}" stroke="{outline}" stroke-width="{stroke_w:.1f}"/>
        <rect x="15" y="80" width="35" height="195" fill="{bg_main}"/>
        <rect x="55" y="45" width="45" height="230" fill="{bg_deep}"/>
        <rect x="105" y="110" width="40" height="165" fill="{bg_main}"/>
        <rect class="city-win win-1" x="22" y="95" width="6" height="8" rx="1" fill="{highlight}"/>
        <rect class="city-win win-2" x="35" y="125" width="6" height="8" rx="1" fill="{accent}"/>
        <rect class="city-win win-3" x="65" y="60" width="8" height="10" rx="1" fill="{highlight}"/>
        <rect class="city-win win-4" x="82" y="85" width="8" height="10" rx="1" fill="{accent}"/>
        <rect class="city-win win-5" x="115" y="130" width="6" height="8" rx="1" fill="{highlight}"/>
      </g>
      <!-- Vertical Glowing LED Edge Bars -->
      <rect x="35" y="40" width="8" height="1100" rx="4" fill="{highlight}" opacity="0.9"/>
      <rect x="1037" y="40" width="8" height="1100" rx="4" fill="{accent}" opacity="0.9"/>
    </svg>"""

    # 3. NEAR LAYER (depth 0.32): Wall shelves, books, geometric potted plant, framed badge
    near_svg = f"""
    <svg class="bg-vector-svg" viewBox="-300 -300 1680 2520" width="1680" height="2520" xmlns="http://www.w3.org/2000/svg">
      <!-- Floating Wall Shelf on Right Studio Wall -->
      <g transform="translate(810, 635)">
        <rect x="0" y="75" width="220" height="18" rx="4" fill="{outline}" stroke="{outline}" stroke-width="{stroke_w * 0.6:.1f}"/>
        <!-- Plant in Pot -->
        <rect x="15" y="42" width="28" height="32" rx="4" fill="{bg_main}" stroke="{outline}" stroke-width="{stroke_w * 0.6:.1f}"/>
        <path d="M 29 42 C 18 24, 6 30, 14 42 Z" fill="#10b981"/>
        <path d="M 29 42 C 34 16, 50 22, 42 42 Z" fill="#059669"/>
        <!-- Studio Books on Shelf -->
        <rect x="52" y="32" width="12" height="42" rx="2" fill="{highlight}"/>
        <rect x="66" y="24" width="14" height="50" rx="2" fill="{accent}"/>
        <rect x="82" y="36" width="10" height="38" rx="2" fill="{pal[2] if len(pal) > 2 else '#3b82f6'}"/>
      </g>
    </svg>"""

    return {"far": far_svg, "mid": mid_svg, "near": near_svg}


def compute_gesture_bounds(
    gesture: str,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
) -> Dict[str, float]:
    """
    Computes screen-space bounding box for all arm and hand geometry of a gesture.
    Returns dictionary with min_x, max_x, min_y, max_y in pixel coordinates.
    All bounds are guaranteed to lie strictly within the safe area.
    """
    clean = sanitize_gesture(gesture)
    rig_x = CHAR_RIG_LAYOUT["left"]
    rig_y = CHAR_RIG_LAYOUT["top"]

    # Hand & arm bounds inside SVG local viewBox (0..560, 0..630)
    # Physically attached to arm sleeve with zero gaps
    if clean == "wave":
        local_min_x = 348.0
        local_max_x = 495.0
        local_min_y = 145.0
        local_max_y = 572.0
    elif clean in ("point", "point_board"):
        local_min_x = 348.0
        local_max_x = 520.0
        local_min_y = 150.0
        local_max_y = 572.0
    elif clean == "point_other":
        local_min_x = 348.0
        local_max_x = 515.0
        local_min_y = 200.0
        local_max_y = 572.0
    elif clean in ("explain", "open_hand"):
        local_min_x = 348.0
        local_max_x = 518.0
        local_min_y = 320.0
        local_max_y = 572.0
    elif clean == "thumbs_up":
        local_min_x = 348.0
        local_max_x = 475.0
        local_min_y = 260.0
        local_max_y = 572.0
    elif clean == "shrug":
        local_min_x = 90.0
        local_max_x = 440.0
        local_min_y = 350.0
        local_max_y = 572.0
    elif clean in ("nod", "head_tilt", "lean_speaker", "listening_reaction"):
        local_min_x = 110.0
        local_max_x = 415.0
        local_min_y = 340.0
        local_max_y = 572.0
    else:  # idle
        local_min_x = 120.0
        local_max_x = 405.0
        local_min_y = 360.0
        local_max_y = 572.0

    return {
        "min_x": float(rig_x + local_min_x),
        "max_x": float(rig_x + local_max_x),
        "min_y": float(rig_y + local_min_y),
        "max_y": float(rig_y + local_max_y),
    }


def resolve_listener_glance_eye(
    listener_slot: str,
    speaker_slot: str = "left",
) -> str:
    """
    Determines the appropriate SVG eye layer ID ('eyes-screen_left' or 'eyes-screen_right')
    for a listener character so that pupils appear directed towards the speaker on screen,
    accounting for horizontal mirroring in the right character slot (scaleX(-1)).

    - Left slot (unmirrored):
      Speaker on right -> look screen-right -> local 'eyes-screen_right'
    - Right slot (mirrored with scaleX(-1)):
      Speaker on left -> look screen-left -> local 'eyes-screen_right'
      (Because scaleX(-1) inverts local X, local screen_right renders to screen-left).
    """
    is_listener_right = listener_slot in ("right", "character-rig-right")
    is_speaker_right = speaker_slot in ("right", "character-rig-right")

    speaker_on_screen_right = is_speaker_right and not is_listener_right
    screen_direction = "right" if speaker_on_screen_right else "left"

    if is_listener_right:
        return "eyes-screen_right" if screen_direction == "left" else "eyes-screen_left"
    else:
        return "eyes-screen_right" if screen_direction == "right" else "eyes-screen_left"
