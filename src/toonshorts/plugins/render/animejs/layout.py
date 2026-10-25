"""
Purpose: Layout constants, safe area bounds, and studio room SVG decorations.
Inputs: Scene identifiers, viewport dimensions, and gesture names.
Outputs: Coordinate boundaries and static SVG decoration elements.
Depends on: core.config, plugins.render.animejs.gestures, typing
Used by: plugins.render.animejs, plugins.render.animejs.capture, plugins.render.animejs.html_builder
Config keys: ENABLE_SPLIT_CAMERA_ZONES, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py, tests/unit/test_split_camera_zones.py
"""

import logging
from typing import Any, Dict, Optional, Tuple

from toonshorts.core import config
from toonshorts.plugins.render.animejs.gestures import sanitize_gesture

logger = logging.getLogger(__name__)

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


_TOPIC_LAYER_CACHE: Dict[str, str] = {}


def build_topic_background_layer(
    topic: Optional[str] = None,
    theme: str = "whiteboard",
    style_profile: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Builds separate, cached, slowly moving background elements per topic as their own layer.
    For security/hacking topics: faint code columns, small lock and shield icons drifting.
    Low contrast, staying strictly under the board layer.
    """
    clean_topic = (topic or "").strip().lower()
    cache_key = f"{theme}:{clean_topic}"
    if cache_key in _TOPIC_LAYER_CACHE:
        return _TOPIC_LAYER_CACHE[cache_key]

    is_night = theme == "night_studio"
    is_security = any(
        kw in clean_topic
        for kw in ("security", "hacker", "hack", "cyber", "password", "system", "auth", "crack", "breach", "leak", "2fa")
    )

    if is_security:
        # Faint code columns, small lock and shield icons drifting
        code_color = "#38bdf8" if is_night else "#2563EB"
        icon_color = "#818cf8" if is_night else "#475569"

        # Code column streams (faint binary & hex)
        # Drifting lock and shield vector symbols
        svg = f"""
    <svg class="bg-vector-svg topic-drift-slow" viewBox="-300 -300 1680 2520" width="1680" height="2520" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Small Lock Symbol -->
        <g id="topic-lock">
          <rect x="-10" y="0" width="20" height="16" rx="3" fill="none" stroke="{icon_color}" stroke-width="2.2" opacity="0.10"/>
          <path d="M -6 0 L -6 -6 A 6 6 0 0 1 6 -6 L 6 0" fill="none" stroke="{icon_color}" stroke-width="2.2" opacity="0.10"/>
          <circle cx="0" cy="7" r="2" fill="{icon_color}" opacity="0.10"/>
        </g>
        <!-- Small Shield Symbol -->
        <g id="topic-shield">
          <path d="M 0 -10 L 10 -6 L 10 2 C 10 8 0 14 0 14 C 0 14 -10 8 -10 2 L -10 -6 Z" fill="none" stroke="{code_color}" stroke-width="2.0" opacity="0.10"/>
          <path d="M 0 -7 L 6 -4 L 6 2 C 6 6 0 10 0 10 C 0 10 -6 6 -6 2 L -6 -4 Z" fill="none" stroke="{code_color}" stroke-width="1.2" opacity="0.08"/>
        </g>
      </defs>
      <!-- Faint Code Columns (Vertical Streams) -->
      <g opacity="0.07" fill="{code_color}" font-family="monospace" font-size="14" letter-spacing="2">
        <text x="-160" y="100">01001000 01100001 01100011 01101011</text>
        <text x="-160" y="130">0x7F4B 0x8A12 0x00FF 0xDE44 0x1122</text>
        <text x="-160" y="160">HASH_SHA256: e3b0c44298fc1c149afb</text>
        <text x="-160" y="190">AUTH_TOKEN:  Bearer eyJhbGciOiJIUz</text>
        <text x="-160" y="220">01110011 01111001 01110011 01110100</text>
        <text x="-160" y="250">0xDEAD 0xBEEF 0xCAFE 0xBABE 0x4242</text>

        <text x="1100" y="200">01110000 01100001 01110011 01110011</text>
        <text x="1100" y="230">0x5F37 0x59DF 0x1337 0x8899 0xA0F1</text>
        <text x="1100" y="260">SALT_ROUNDS: 12 bcrypt pbkdf2</text>
        <text x="1100" y="290">CIPHER: AES-256-GCM IV_NONCE_OK</text>
        <text x="1100" y="320">01010011 01000101 01000011 01010101</text>
        <text x="1100" y="350">PORT_SCAN: 22/tcp 443/tcp 8080/tcp</text>

        <text x="200" y="1400">01000010 01010010 01000101 01000001</text>
        <text x="200" y="1430">0xAA45 0x12FE 0x90B3 0x3344 0x5566</text>
        <text x="750" y="1400">01010011 01001000 01001001 01000101</text>
        <text x="750" y="1430">0x99AA 0xBBCC 0xDDEE 0xFF00 0x1122</text>
      </g>
      <!-- Small Drifting Lock and Shield Icons (Low Contrast, Faint) -->
      <use href="#topic-lock" x="-80" y="380" transform="scale(1.4)"/>
      <use href="#topic-shield" x="1220" y="450" transform="scale(1.5)"/>
      <use href="#topic-lock" x="1180" y="900" transform="scale(1.2)"/>
      <use href="#topic-shield" x="-100" y="950" transform="scale(1.3)"/>
      <use href="#topic-shield" x="100" y="1320" transform="scale(1.2)"/>
      <use href="#topic-lock" x="980" y="1340" transform="scale(1.3)"/>
    </svg>"""
    else:
        # Subtle ambient grid/nodes for general topics
        node_color = "#38bdf8" if is_night else "#94a3b8"
        svg = f"""
    <svg class="bg-vector-svg topic-drift-slow" viewBox="-300 -300 1680 2520" width="1680" height="2520" xmlns="http://www.w3.org/2000/svg">
      <g opacity="0.06" stroke="{node_color}" stroke-width="1.5">
        <circle cx="-50" cy="200" r="4" fill="{node_color}"/>
        <circle cx="1150" cy="280" r="4" fill="{node_color}"/>
        <circle cx="120" cy="1380" r="4" fill="{node_color}"/>
        <circle cx="950" cy="1420" r="4" fill="{node_color}"/>
        <line x1="-50" y1="200" x2="0" y2="280" stroke-dasharray="4 4"/>
        <line x1="1150" y1="280" x2="1100" y2="360" stroke-dasharray="4 4"/>
      </g>
    </svg>"""

    _TOPIC_LAYER_CACHE[cache_key] = svg
    return svg


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



def compute_speaker_bounding_box(
    speaker_slot: str,
    gesture: str = "idle",
    padding: float = 20.0,
    stage_anchors: Optional[Dict[str, Any]] = None,
    zone: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Computes a speaker's full bounding box (head to torso/legs, plus a raised pointing hand),
    with padding, inside the Character Zone local coordinate system.
    Accounts for Character A (left, facing right) and Character B (right, mirrored facing left).
    """
    if zone is None:
        zone = getattr(config, "SPLIT_CHARACTER_ZONE", {
            "top": 820.0, "bottom": 1350.0, "left": 60.0, "right": 960.0,
            "width": 900.0, "height": 530.0,
        })
    if stage_anchors is None:
        stage_anchors = getattr(config, "SPLIT_STAGE_ANCHORS", {
            "left": {"left": 60.0, "top": 20.0, "width": 420.0, "height": 480.0},
            "right": {"left": 420.0, "top": 20.0, "width": 420.0, "height": 480.0},
        })

    is_right = speaker_slot in ("right", "girl_a", "girl_close", "speaker_right", "character-rig-right")
    slot_key = "right" if is_right else "left"
    anchor = stage_anchors.get(slot_key, stage_anchors["left"])

    clean_gesture = sanitize_gesture(gesture)

    # Base rig viewBox: 560 x 630
    rig_vb_w = 560.0
    rig_vb_h = 630.0
    slot_w = float(anchor.get("width", 420.0))
    slot_h = float(anchor.get("height", 480.0))
    slot_x = float(anchor.get("left", 60.0 if not is_right else 420.0))
    slot_y = float(anchor.get("top", 20.0))

    scale_x = slot_w / rig_vb_w
    scale_y = slot_h / rig_vb_h

    # Head and torso/legs bounds in local rig coordinates (0..560, 0..630)
    body_local_min_x = 90.0
    body_local_max_x = 440.0
    body_local_min_y = 20.0
    body_local_max_y = 580.0

    # Arm / hand extension bounds in local rig coordinates
    if clean_gesture == "wave":
        hand_local_min_x = 348.0
        hand_local_max_x = 495.0
        hand_local_min_y = 145.0
        hand_local_max_y = 572.0
    elif clean_gesture in ("point", "point_board"):
        hand_local_min_x = 348.0
        hand_local_max_x = 520.0
        hand_local_min_y = 150.0
        hand_local_max_y = 572.0
    elif clean_gesture == "point_other":
        hand_local_min_x = 348.0
        hand_local_max_x = 515.0
        hand_local_min_y = 200.0
        hand_local_max_y = 572.0
    elif clean_gesture in ("explain", "open_hand"):
        hand_local_min_x = 348.0
        hand_local_max_x = 518.0
        hand_local_min_y = 300.0
        hand_local_max_y = 572.0
    elif clean_gesture == "thumbs_up":
        hand_local_min_x = 348.0
        hand_local_max_x = 475.0
        hand_local_min_y = 260.0
        hand_local_max_y = 572.0
    elif clean_gesture == "shrug":
        hand_local_min_x = 90.0
        hand_local_max_x = 440.0
        hand_local_min_y = 340.0
        hand_local_max_y = 572.0
    else:
        hand_local_min_x = 120.0
        hand_local_max_x = 405.0
        hand_local_min_y = 360.0
        hand_local_max_y = 572.0

    # Combined rig local bounding box
    local_min_x = min(body_local_min_x, hand_local_min_x)
    local_max_x = max(body_local_max_x, hand_local_max_x)
    local_min_y = min(body_local_min_y, hand_local_min_y)
    local_max_y = max(body_local_max_y, hand_local_max_y)

    if not is_right:
        # Character A (left slot): unmirrored, facing right
        box_min_x = slot_x + (local_min_x * scale_x) - padding
        box_max_x = slot_x + (local_max_x * scale_x) + padding
    else:
        # Character B (right slot): mirrored via scaleX(-1) around slot center
        box_min_x = slot_x + (slot_w - local_max_x * scale_x) - padding
        box_max_x = slot_x + (slot_w - local_min_x * scale_x) + padding

    box_min_y = slot_y + (local_min_y * scale_y) - padding
    box_max_y = slot_y + (local_max_y * scale_y) + padding

    box_w = max(1.0, box_max_x - box_min_x)
    box_h = max(1.0, box_max_y - box_min_y)

    zone_top = float(zone.get("top", 820.0))
    zone_left = float(zone.get("left", 60.0))

    return {
        "min_x": float(box_min_x),
        "max_x": float(box_max_x),
        "min_y": float(box_min_y),
        "max_y": float(box_max_y),
        "width": float(box_w),
        "height": float(box_h),
        "screen_min_x": float(zone_left + box_min_x),
        "screen_max_x": float(zone_left + box_max_x),
        "screen_min_y": float(zone_top + box_min_y),
        "screen_max_y": float(zone_top + box_max_y),
    }


def compute_character_camera_framing(
    speaker_slot: str,
    gesture: str = "idle",
    requested_zoom: float = 1.18,
    padding: float = 20.0,
    stage_anchors: Optional[Dict[str, Any]] = None,
    zone: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes deterministic zoom and pan for the character camera conforming to framing rules:
    1. Computes full speaker bounding box (head to torso/legs, plus raised hand), with padding.
    2. Zoom = min(requested zoom, largest zoom that keeps that whole box inside the zone). Never exceeds 1.35x.
    3. Clamps pan so the box stays inside the zone and clear of the right-edge button area (x <= 960).
    4. If a speaker cannot fit at any useful zoom (zoom < 1.05), reports it and adjusts stage anchors inward.
    5. Returns zoom, pan_x, pan_y, and transformed bounding boxes.
    """
    if zone is None:
        zone = getattr(config, "SPLIT_CHARACTER_ZONE", {
            "top": 820.0, "bottom": 1350.0, "left": 60.0, "right": 960.0,
            "width": 900.0, "height": 530.0,
        })
    zone_w = float(zone["width"])
    zone_h = float(zone["height"])
    max_allowed_zoom = float(getattr(config, "CAMERA_MAX_ZOOM", 1.35))

    current_anchors = dict(stage_anchors or getattr(config, "SPLIT_STAGE_ANCHORS", {
        "left": {"left": 60.0, "top": 20.0, "width": 420.0, "height": 480.0},
        "right": {"left": 420.0, "top": 20.0, "width": 420.0, "height": 480.0},
    }))

    bbox = compute_speaker_bounding_box(speaker_slot, gesture, padding, current_anchors, zone)
    max_fit_zoom = min(zone_w / bbox["width"], zone_h / bbox["height"])

    adjusted_inward = False
    if max_fit_zoom < 1.05:
        logger.warning(
            "Speaker '%s' cannot fit at useful zoom (max_fit_zoom=%.2f < 1.05); adjusting stage anchor inward",
            speaker_slot, max_fit_zoom
        )
        current_anchors = adjust_stage_anchors_inward(speaker_slot, current_anchors, shift_px=25.0)
        adjusted_inward = True
        bbox = compute_speaker_bounding_box(speaker_slot, gesture, padding, current_anchors, zone)
        max_fit_zoom = min(zone_w / bbox["width"], zone_h / bbox["height"])

    zoom = min(float(requested_zoom), float(max_fit_zoom), max_allowed_zoom)

    # Ideal centering pan
    ideal_cx = (bbox["min_x"] + bbox["max_x"]) / 2.0
    ideal_cy = (bbox["min_y"] + bbox["max_y"]) / 2.0
    cx = zone_w / 2.0
    cy = zone_h / 2.0
    ideal_pan_x = cx - ideal_cx
    ideal_pan_y = cy - ideal_cy

    # Pan limits to keep box inside [0, zone_w] and [0, zone_h] under transform:
    min_pan_x = - (cx + (bbox["min_x"] - cx) * zoom)
    max_pan_x = zone_w - (cx + (bbox["max_x"] - cx) * zoom)
    if min_pan_x > max_pan_x:
        min_pan_x, max_pan_x = max_pan_x, min_pan_x

    clamped_pan_x = max(min_pan_x, min(max_pan_x, ideal_pan_x))

    min_pan_y = - (cy + (bbox["min_y"] - cy) * zoom)
    max_pan_y = zone_h - (cy + (bbox["max_y"] - cy) * zoom)
    if min_pan_y > max_pan_y:
        min_pan_y, max_pan_y = max_pan_y, min_pan_y

    clamped_pan_y = max(min_pan_y, min(max_pan_y, ideal_pan_y))

    # Transformed bounding box inside Character Zone
    trans_min_x = cx + (bbox["min_x"] - cx) * zoom + clamped_pan_x
    trans_max_x = cx + (bbox["max_x"] - cx) * zoom + clamped_pan_x
    trans_min_y = cy + (bbox["min_y"] - cy) * zoom + clamped_pan_y
    trans_max_y = cy + (bbox["max_y"] - cy) * zoom + clamped_pan_y

    zone_left = float(zone.get("left", 60.0))
    zone_top = float(zone.get("top", 820.0))

    screen_min_x = zone_left + trans_min_x
    screen_max_x = zone_left + trans_max_x
    screen_min_y = zone_top + trans_min_y
    screen_max_y = zone_top + trans_max_y

    return {
        "speaker_slot": speaker_slot,
        "zoom": round(zoom, 4),
        "pan_x": round(clamped_pan_x, 2),
        "pan_y": round(clamped_pan_y, 2),
        "max_fit_zoom": round(max_fit_zoom, 4),
        "adjusted_inward": adjusted_inward,
        "bbox": bbox,
        "transformed_bbox": {
            "min_x": round(trans_min_x, 2),
            "max_x": round(trans_max_x, 2),
            "min_y": round(trans_min_y, 2),
            "max_y": round(trans_max_y, 2),
        },
        "screen_bbox": {
            "min_x": round(screen_min_x, 2),
            "max_x": round(screen_max_x, 2),
            "min_y": round(screen_min_y, 2),
            "max_y": round(screen_max_y, 2),
        },
    }


def adjust_stage_anchors_inward(
    speaker_slot: str,
    stage_anchors: Dict[str, Any],
    shift_px: float = 20.0,
) -> Dict[str, Any]:
    """Adjusts stage anchor inward towards screen center to ensure the speaker fits without cut-off."""
    updated = {k: dict(v) for k, v in stage_anchors.items()}
    is_right = speaker_slot in ("right", "girl_a", "girl_close", "speaker_right", "character-rig-right")
    slot_key = "right" if is_right else "left"
    if slot_key == "left":
        updated["left"]["left"] += shift_px
        updated["left"]["width"] = max(280.0, updated["left"]["width"] - shift_px)
    else:
        updated["right"]["left"] -= shift_px
        updated["right"]["width"] = max(280.0, updated["right"]["width"] - shift_px)
    return updated


def verify_speaker_in_character_zone(
    box: Dict[str, float],
    zone: Optional[Dict[str, float]] = None,
) -> bool:
    """Verifies that the speaker's bounding box is strictly inside the character zone."""
    if zone is None:
        zone = getattr(config, "SPLIT_CHARACTER_ZONE", {
            "width": 900.0, "height": 530.0,
        })
    zone_w = float(zone.get("width", 900.0))
    zone_h = float(zone.get("height", 530.0))
    eps = 0.5  # tolerance
    return (
        box["min_x"] >= -eps
        and box["max_x"] <= zone_w + eps
        and box["min_y"] >= -eps
        and box["max_y"] <= zone_h + eps
    )


def verify_no_safe_zone_overlap(element_bounds: Dict[str, float]) -> bool:
    """
    Verifies that element screen bounds stay strictly clear of YouTube Shorts safe zones:
    - Top 15% safe zone: y in [0, 288] (min_y >= 288)
    - Bottom 25% safe zone: y in [1440, 1920] (max_y <= 1440)
    - Right 120px safe zone: x in [960, 1080] (max_x <= 960)
    """
    top_limit = float(getattr(config, "SAFE_ZONE_TOP_PX", 288))
    bottom_limit = float(getattr(config, "SAFE_ZONE_BOTTOM_PX", 1440))
    right_limit = float(getattr(config, "SAFE_ZONE_RIGHT_BOUNDARY_PX", 960.0))
    eps = 0.5

    min_y = element_bounds.get("screen_min_y", element_bounds.get("min_y", 0.0))
    max_y = element_bounds.get("screen_max_y", element_bounds.get("max_y", 0.0))
    max_x = element_bounds.get("screen_max_x", element_bounds.get("max_x", 0.0))

    if min_y < top_limit - eps:
        return False
    if max_y > bottom_limit + eps:
        return False
    if max_x > right_limit + eps:
        return False
    return True
