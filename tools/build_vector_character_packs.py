"""
Purpose: Generator and renderer for clean vector (SVG) character packs (boy_b and girl_a).
Inputs: Source reference images in assets/sources/
Outputs:
  - assets/2d/characters/boy_b/vector/ (manifest.json, character.json, layers/*.svg, staging/*)
  - assets/2d/characters/girl_a/vector/ (manifest.json, character.json, layers/*.svg, staging/*)
Depends on: json, pathlib, xml.etree.ElementTree, PIL, playwright
Used by: Character staging, vector character verification
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from toonshorts.core import paths
from toonshorts.core.character_pack import validate_svg_security, validate_manifest_schema


def get_boy_b_layers() -> Dict[str, str]:
    """Returns SVG content for all 22 layers of boy_b."""
    # Palette constants
    STROKE_THICK = "#1b1516"
    STROKE_THIN = "#1b1516"
    STROKE_SUBTLE = "#2b1d1f"
    HAIR_BASE = "#482920"
    HAIR_SHADOW = "#2c1813"
    HAIR_LIGHT = "#5b3429"
    HAIR_DARK = "#361f19"
    SKIN_BASE = "#f3be9b"
    SKIN_SHADOW = "#db9c79"
    HOODIE_BASE = "#4f82ba"
    HOODIE_SHADOW = "#3b689a"
    HOODIE_INNER = "#274567"
    HOODIE_CUFF = "#3b689a"
    DRAWSTRING = "#ffffff"
    METAL_TIP = "#d2d7de"
    JEANS_BASE = "#4d6276"
    JEANS_SHADOW = "#3a4c5c"
    JEANS_CUFF = "#5c7489"
    SHOE_PURPLE = "#5e3364"
    SHOE_SHADOW = "#432247"
    SHOE_WHITE = "#ffffff"
    SHOE_SOLE = "#f4f6f9"
    SHOE_SOLE_SHADOW = "#e0e4e9"
    SOCK_WHITE = "#edf0f5"
    MOUTH_DARK = "#2a1814"
    MOUTH_TONGUE = "#e27a7a"
    MOUTH_TEETH = "#ffffff"

    layers = {}

    # 1. head_back
    layers["head_back"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_back">
    <path fill="{HAIR_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M500 60 L445 95 L385 130 L330 180 L270 240 L250 310 L280 345 L240 410 L290 430 L250 485 L315 490 L305 535 L365 495 L375 540 L435 485 L500 510 L565 485 L625 540 L635 495 L695 535 L685 490 L750 485 L710 430 L760 410 L720 345 L750 310 L730 240 L670 180 L615 130 L555 95 Z" />
    <polygon points="330,240 270,310 320,330" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="270,310 280,345 240,410" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="240,410 290,430 250,485" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="670,240 730,310 680,330" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="730,310 720,345 760,410" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="760,410 710,430 750,485" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <!-- Top Back Facets for back view -->
    <polygon points="500,60 445,95 500,150" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="500,60 500,150 555,95" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="445,95 385,130 440,175" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="445,95 440,175 500,150" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="555,95 500,150 560,175" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="555,95 615,130 560,175" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
  </g>
</svg>"""

    # 2. head_base (cranium, jaw, ears, eyebrows, nose, neck, glasses frames, hair front - NO eyes, NO mouth)
    layers["head_base"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_base">
    <!-- Neck extending downward under torso collar -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M465 440 L465 545 L535 545 L535 440 Z" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M472 440 L472 525 C472 538 528 538 528 525 L528 440 Z" />
    <!-- Ears -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M380 320 C330 320 330 390 380 400 Z" />
    <path fill="none" stroke="{STROKE_SUBTLE}" stroke-width="3.5" stroke-linecap="round" d="M370 342 C350 348 350 372 370 378" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M620 320 C670 320 670 390 620 400 Z" />
    <path fill="none" stroke="{STROKE_SUBTLE}" stroke-width="3.5" stroke-linecap="round" d="M630 342 C650 348 650 372 630 378" />
    <!-- Head Jaw and Cranium (full dome prevents hair gap bleed) -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M360 300 C360 100 640 100 640 300 C625 395 580 465 500 465 C420 465 375 395 375 300 Z" />
    <!-- Chin Shadow -->
    <path fill="{SKIN_SHADOW}" d="M480 442 C440 442 410 412 400 385 C420 422 460 438 500 438 C540 438 580 422 600 385 C590 412 560 442 520 442 Z" />
    <!-- Eyebrows -->
    <path fill="{HAIR_SHADOW}" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M405 272 Q445 260 478 276 L474 290 Q445 278 410 286 Z" />
    <path fill="{HAIR_SHADOW}" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M595 272 Q555 260 522 276 L526 290 Q555 278 590 286 Z" />
    <!-- Nose -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M492 370 Q500 380 508 370 Z" />
    <!-- Glasses Frames (Spectacles) -->
    <circle cx="445" cy="336" r="47" fill="none" stroke="#251a17" stroke-width="11" />
    <circle cx="555" cy="336" r="47" fill="none" stroke="#251a17" stroke-width="11" />
    <path fill="none" stroke="#251a17" stroke-width="9" stroke-linecap="round" d="M492 336 Q500 325 508 336" />
    <line x1="398" y1="336" x2="362" y2="330" stroke="#251a17" stroke-width="7" stroke-linecap="round" />
    <line x1="602" y1="336" x2="638" y2="330" stroke="#251a17" stroke-width="7" stroke-linecap="round" />
    <!-- Hair Front Solid Silhouette Underlay (prevents seam slivers, pinholes, and white gaps) -->
    <path fill="{HAIR_DARK}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M500 60 L445 100 L390 130 L335 175 L315 240 L355 275 L385 245 L400 205 L450 215 L485 245 L500 200 L515 245 L550 215 L600 205 L615 245 L645 275 L685 240 L665 175 L610 130 L555 100 Z" />
    <!-- Hair Front Facets -->
    <polygon points="500,60 445,100 500,120" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="500,60 500,120 555,100" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="445,100 390,130 440,150" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="445,100 440,150 500,120" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="555,100 500,120 560,150" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="555,100 610,130 560,150" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="440,150 400,205 450,215" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="440,150 450,215 480,175" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="500,120 440,150 480,175" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="500,120 480,175 520,175" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="500,120 520,175 560,150" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="560,150 520,175 550,215" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="560,150 550,215 600,205" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="480,175 450,215 485,245" fill="{HAIR_SHADOW}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="480,175 485,245 500,200" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <!-- Center connecting facet (previously missing, leaving white hole) -->
    <polygon points="480,175 520,175 500,200" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="520,175 500,200 515,245" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="520,175 515,245 550,215" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="390,130 335,175 365,225" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="390,130 365,225 400,205" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="365,225 315,240 355,275" fill="{HAIR_SHADOW}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="365,225 355,275 385,245" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="365,225 385,245 400,205" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="610,130 595,205 635,225" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="610,130 635,225 665,175" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="635,225 615,245 645,275" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="635,225 600,205 615,245" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="635,225 645,275 685,240" fill="{HAIR_SHADOW}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <!-- Outer Contour Stroke -->
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M500 60 L445 100 L390 130 L335 175 L315 240 L355 275 L385 245 L400 205 L450 215 L485 245 L500 200 L515 245 L550 215 L600 205 L615 245 L645 275 L685 240 L665 175 L610 130 L555 100 Z" />
  </g>
</svg>"""

    # 3. eyes_open
    layers["eyes_open"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_open">
    <!-- Left Eye -->
    <ellipse cx="445" cy="336" rx="36" ry="37" fill="#ffffff" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="447" cy="336" rx="24" ry="25" fill="#2a1814" />
    <ellipse cx="447" cy="336" rx="14" ry="15" fill="#100806" />
    <circle cx="440" cy="328" r="7.5" fill="#ffffff" />
    <circle cx="456" cy="344" r="4" fill="#ffffff" />
    <!-- Right Eye -->
    <ellipse cx="555" cy="336" rx="36" ry="37" fill="#ffffff" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="553" cy="336" rx="24" ry="25" fill="#2a1814" />
    <ellipse cx="553" cy="336" rx="14" ry="15" fill="#100806" />
    <circle cx="546" cy="328" r="7.5" fill="#ffffff" />
    <circle cx="562" cy="344" r="4" fill="#ffffff" />
  </g>
</svg>"""

    # 4. eyes_blink
    layers["eyes_blink"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_blink">
    <!-- Left Eye Blink curve -->
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" d="M418 338 Q445 352 472 338" />
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" d="M430 345 L425 352" />
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" d="M460 345 L465 352" />
    <!-- Right Eye Blink curve -->
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" d="M528 338 Q555 352 582 338" />
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" d="M540 345 L535 352" />
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" d="M570 345 L575 352" />
  </g>
</svg>"""

    # 5. eyes_look_left
    layers["eyes_look_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_look_left">
    <!-- Left Eye: Pupil shifted left -->
    <ellipse cx="445" cy="336" rx="36" ry="37" fill="#ffffff" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="433" cy="336" rx="22" ry="25" fill="#2a1814" />
    <ellipse cx="433" cy="336" rx="13" ry="15" fill="#100806" />
    <circle cx="427" cy="328" r="7" fill="#ffffff" />
    <circle cx="441" cy="344" r="3.5" fill="#ffffff" />
    <!-- Right Eye: Pupil shifted left -->
    <ellipse cx="555" cy="336" rx="36" ry="37" fill="#ffffff" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="541" cy="336" rx="22" ry="25" fill="#2a1814" />
    <ellipse cx="541" cy="336" rx="13" ry="15" fill="#100806" />
    <circle cx="535" cy="328" r="7" fill="#ffffff" />
    <circle cx="549" cy="344" r="3.5" fill="#ffffff" />
  </g>
</svg>"""

    # 6. eyes_look_right
    layers["eyes_look_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_look_right">
    <!-- Left Eye: Pupil shifted right -->
    <ellipse cx="445" cy="336" rx="36" ry="37" fill="#ffffff" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="459" cy="336" rx="22" ry="25" fill="#2a1814" />
    <ellipse cx="459" cy="336" rx="13" ry="15" fill="#100806" />
    <circle cx="453" cy="328" r="7" fill="#ffffff" />
    <circle cx="467" cy="344" r="3.5" fill="#ffffff" />
    <!-- Right Eye: Pupil shifted right -->
    <ellipse cx="555" cy="336" rx="36" ry="37" fill="#ffffff" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="567" cy="336" rx="22" ry="25" fill="#2a1814" />
    <ellipse cx="567" cy="336" rx="13" ry="15" fill="#100806" />
    <circle cx="561" cy="328" r="7" fill="#ffffff" />
    <circle cx="575" cy="344" r="3.5" fill="#ffffff" />
  </g>
</svg>"""

    # 7. mouth_closed
    layers["mouth_closed"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_closed">
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M468 405 Q500 422 532 405" />
    <path fill="{SKIN_SHADOW}" d="M490 420 Q500 424 510 420 Z" />
  </g>
</svg>"""

    # 8. mouth_slightly_open
    layers["mouth_slightly_open"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_slightly_open">
    <path fill="{MOUTH_DARK}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M472 404 Q500 398 528 404 Q500 422 472 404 Z" />
    <!-- Upper teeth sliver -->
    <path fill="{MOUTH_TEETH}" d="M480 404 Q500 400 520 404 Q500 409 480 404 Z" />
    <path fill="{SKIN_SHADOW}" d="M490 425 Q500 429 510 425 Z" />
  </g>
</svg>"""

    # 9. mouth_wide_open
    layers["mouth_wide_open"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_wide_open">
    <path fill="{MOUTH_DARK}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M464 398 Q500 392 536 398 C536 432 522 444 500 444 C478 444 464 432 464 398 Z" />
    <!-- Teeth -->
    <path fill="{MOUTH_TEETH}" d="M472 398 Q500 394 528 398 C526 408 474 408 472 398 Z" />
    <!-- Tongue -->
    <path fill="{MOUTH_TONGUE}" d="M480 440 C485 425 515 425 520 440 C510 443 490 443 480 440 Z" />
    <path fill="{SKIN_SHADOW}" d="M488 448 Q500 452 512 448 Z" />
  </g>
</svg>"""

    # 10. mouth_round_o
    layers["mouth_round_o"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_round_o">
    <ellipse cx="500" cy="410" rx="18" ry="22" fill="{MOUTH_DARK}" stroke="{STROKE_THICK}" stroke-width="5" />
    <ellipse cx="500" cy="418" rx="10" ry="8" fill="{MOUTH_TONGUE}" />
    <path fill="{SKIN_SHADOW}" d="M490 436 Q500 440 510 436 Z" />
  </g>
</svg>"""

    # 11. mouth_open_smile
    layers["mouth_open_smile"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_open_smile">
    <path fill="{MOUTH_DARK}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M460 400 Q500 390 540 400 C535 435 518 442 500 442 C480 442 465 435 460 400 Z" />
    <!-- Full upper teeth band -->
    <path fill="{MOUTH_TEETH}" stroke="{STROKE_THIN}" stroke-width="2" d="M466 400 Q500 392 534 400 C530 410 470 410 466 400 Z" />
    <!-- Tongue arc -->
    <path fill="{MOUTH_TONGUE}" d="M478 438 C484 424 516 424 522 438 C512 441 488 441 478 438 Z" />
    <path fill="{SKIN_SHADOW}" d="M488 446 Q500 450 512 446 Z" />
  </g>
</svg>"""

    # 12. torso (hoodie body, collar, kangaroo pocket, drawstrings, waistband)
    layers["torso"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_torso">
    <!-- Interior hood opening behind neck -->
    <path fill="{HOODIE_INNER}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M420 475 C440 435 560 435 580 475 C605 525 395 525 420 475 Z" />
    <!-- Torso main shadow -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M395 520 L370 805 L630 805 L605 520 Z" />
    <!-- Torso main base -->
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M405 515 C440 528 560 528 595 515 L622 805 L378 805 Z" />
    <!-- Waistband / hem (covers upper leg joint overlap) -->
    <rect x="370" y="805" width="260" height="68" rx="6" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <rect x="375" y="805" width="250" height="62" rx="4" fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" />
    <!-- Kangaroo pocket -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M415 690 L445 690 L435 790 L405 790 Z" />
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M585 690 L555 690 L565 790 L595 790 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M440 690 L560 690 L585 790 L415 790 Z" />
    <line x1="415" y1="790" x2="440" y2="690" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" />
    <line x1="585" y1="790" x2="560" y2="690" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" />
    <!-- Center zipper seam -->
    <line x1="500" y1="535" x2="500" y2="865" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" />
    <rect x="496" y="545" width="8" height="16" rx="2" fill="{METAL_TIP}" stroke="{STROKE_THIN}" stroke-width="3" />
    <!-- Front hood collar wrap -->
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M415 480 C440 535 490 545 500 545 C510 545 560 535 585 480 C555 518 445 518 415 480 Z" />
    <!-- Drawstrings -->
    <path fill="none" stroke="{DRAWSTRING}" stroke-width="4.5" stroke-linecap="round" d="M465 535 L465 615" />
    <rect x="462" y="615" width="6" height="20" rx="2" fill="{METAL_TIP}" stroke="{STROKE_SUBTLE}" stroke-width="2.5" />
    <path fill="none" stroke="{DRAWSTRING}" stroke-width="4.5" stroke-linecap="round" d="M535 535 L535 615" />
    <rect x="532" y="615" width="6" height="20" rx="2" fill="{METAL_TIP}" stroke="{STROKE_SUBTLE}" stroke-width="2.5" />
  </g>
</svg>"""

    # 13. arm_upper_left (shoulder to elbow, blue hoodie sleeve with shoulder cap and elbow hem)
    # Shoulder pivot at (415, 525), Elbow at (390, 660)
    layers["arm_upper_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_upper_left">
    <!-- Shoulder overlap cap (hidden under torso shoulder) -->
    <circle cx="415" cy="525" r="32" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Upper arm sleeve body -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M410 520 L360 655 L420 670 L445 545 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M412 520 L368 655 L415 668 L440 555 Z" />
    <!-- Elbow sleeve hem (covers lower arm joint cap) -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M355 650 Q390 665 425 665" />
  </g>
</svg>"""

    # 14. arm_lower_left (forearm sleeve and hand left, with rounded elbow cap and wrist cuff)
    # Elbow pivot at (390, 660), Wrist at (345, 785), Hand to 895
    layers["arm_lower_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_lower_left">
    <!-- Elbow overlap cap extending into upper sleeve -->
    <circle cx="390" cy="660" r="28" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Lower arm sleeve body -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M362 655 L315 775 L372 795 L418 665 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M368 655 L325 775 L368 792 L412 665 Z" />
    <!-- Wrist hoodie cuff (covers hand joint cap) -->
    <g transform="rotate(20, 345, 785)">
      <rect x="306" y="768" width="76" height="34" rx="7" fill="{HOODIE_CUFF}" stroke="{STROKE_THICK}" stroke-width="6" />
      <rect x="309" y="771" width="70" height="28" rx="5" fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="3" />
    </g>
    <!-- Redrawn Hand matching hands sheet -->
    <g id="boy_hand_l">
      <!-- Wrist link under cuff -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M330 795 L318 840 L358 852 L365 802 Z" />
      <!-- Palm Base -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M320 835 C308 860 308 880 318 900 C326 910 344 910 354 900 C366 888 368 860 362 835 Z" />
      <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" d="M324 840 C314 860 314 878 322 895 C328 902 342 902 350 895 C360 885 362 860 356 840 Z" />
      <!-- Inward Thumb -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M352 840 C366 850 374 865 370 877 C364 885 354 881 348 870 Z" />
      <!-- Subtle Finger Crease Strokes -->
      <line x1="330" y1="901" x2="330" y2="870" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="339" y1="903" x2="339" y2="865" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="347" y1="899" x2="347" y2="868" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
    </g>
  </g>
</svg>"""

    # 15. arm_upper_right (shoulder to elbow, blue hoodie sleeve with shoulder cap and elbow hem)
    # Shoulder pivot at (585, 525), Elbow at (610, 660)
    layers["arm_upper_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_upper_right">
    <!-- Shoulder overlap cap (hidden under torso shoulder) -->
    <circle cx="585" cy="525" r="32" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Upper arm sleeve body -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M590 520 L640 655 L580 670 L555 545 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M588 520 L632 655 L585 668 L560 555 Z" />
    <!-- Elbow sleeve hem (covers lower arm joint cap) -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M645 650 Q610 665 575 665" />
  </g>
</svg>"""

    # 16. arm_lower_right (forearm sleeve and hand right, with rounded elbow cap and wrist cuff)
    # Elbow pivot at (610, 660), Wrist at (655, 785), Hand to 895
    layers["arm_lower_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_lower_right">
    <!-- Elbow overlap cap extending into upper sleeve -->
    <circle cx="610" cy="660" r="28" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Lower arm sleeve body -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M638 655 L685 775 L628 795 L582 665 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M632 655 L675 775 L632 792 L588 665 Z" />
    <!-- Wrist hoodie cuff (covers hand joint cap) -->
    <g transform="rotate(-20, 655, 785)">
      <rect x="618" y="768" width="76" height="34" rx="7" fill="{HOODIE_CUFF}" stroke="{STROKE_THICK}" stroke-width="6" />
      <rect x="621" y="771" width="70" height="28" rx="5" fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="3" />
    </g>
    <!-- Redrawn Hand matching hands sheet -->
    <g id="boy_hand_r">
      <!-- Wrist link under cuff -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M670 795 L682 840 L642 852 L635 802 Z" />
      <!-- Palm Base -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M680 835 C692 860 692 880 682 900 C674 910 656 910 646 900 C634 888 632 860 638 835 Z" />
      <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" d="M676 840 C686 860 686 878 678 895 C672 902 658 902 650 895 C640 885 638 860 644 840 Z" />
      <!-- Inward Thumb -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M648 840 C634 850 626 865 630 877 C636 885 646 881 652 870 Z" />
      <!-- Subtle Finger Crease Strokes -->
      <line x1="670" y1="901" x2="670" y2="870" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="661" y1="903" x2="661" y2="865" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="653" y1="899" x2="653" y2="868" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
    </g>
  </g>
</svg>"""

    # 17. leg_upper_left (thigh left from hip to knee)
    # Hip pivot at (435, 870), Knee pivot at (425, 1100)
    layers["leg_upper_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_left">
    <!-- Hip overlap cap (hidden under torso waistband) -->
    <circle cx="435" cy="870" r="48" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Thigh body -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M390 870 L380 1100 L480 1100 L495 870 Z" />
    <path fill="{JEANS_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M400 870 L390 1100 L475 1100 L493 870 Z" />
    <!-- Knee hem covering lower leg cap -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M375 1095 Q430 1108 485 1095" />
  </g>
</svg>"""

    # 18. leg_lower_left (calf left from knee to ankle, with jeans cuff)
    # Knee pivot at (425, 1100), Ankle pivot at (420, 1345)
    layers["leg_lower_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_lower_left">
    <!-- Knee overlap cap (hidden under upper leg knee hem) -->
    <circle cx="425" cy="1100" r="42" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Calf body -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M380 1100 L375 1310 L475 1310 L480 1100 Z" />
    <path fill="{JEANS_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M390 1100 L387 1310 L473 1310 L475 1100 Z" />
    <!-- Jeans cuff at ankle (covers shoe joint cap) -->
    <rect x="370" y="1305" width="108" height="40" rx="6" fill="{JEANS_CUFF}" stroke="{STROKE_THICK}" stroke-width="6" />
  </g>
</svg>"""

    # 19. shoe_left (authentic 3/4 perspective sneaker matching boy_b_front_large.png)
    # Ankle pivot at (420, 1345)
    layers["shoe_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_left">
    <!-- Ankle joint cap (tucks under jeans cuff at (420, 1345)) -->
    <circle cx="420" cy="1345" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- White sock sliver on medial side -->
    <path fill="{SOCK_WHITE}" stroke="{STROKE_THICK}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" d="M442 1338 L468 1338 L468 1368 L442 1368 Z" />
    
    <!-- Purple tongue (flat/angled top sticking out under cuff) -->
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M384 1338 L442 1338 L440 1364 L386 1364 Z" />
    
    <!-- Throat / Instep Underlay (dark purple canvas behind laces) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M386 1364 L440 1364 L404 1442 L346 1420 Z" />
    
    <!-- 4 White Laces Bars across instep -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M383 1368 L436 1369 L431 1378 L378 1377 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M373 1382 L426 1384 L421 1393 L368 1391 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M363 1396 L416 1399 L411 1408 L358 1405 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M353 1410 L407 1414 L402 1423 L348 1419 Z" />

    <!-- Lateral purple canvas quarter (heel counter / side panel) -->
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M440 1362 L468 1372 L472 1436 L404 1444 L440 1362 Z" />
    <!-- Heel shadow/contour accent -->
    <path fill="{SHOE_SHADOW}" d="M455 1370 L468 1372 L472 1436 L458 1438 Z" />

    <!-- White rubber toe cap (Solid 3D volume matching source) -->
    <!-- Top slope facet -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M346 1420 L404 1424 L404 1444 L345 1448 L308 1436 Z" />
    <!-- Front vertical face facet -->
    <path fill="#f0f3f6" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M308 1436 L345 1448 L404 1444 L396 1453 L338 1457 L305 1446 Z" />

    <!-- Thick Rubber Sole (continuous, clean, solid outline) -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M305 1446 L338 1457 L404 1444 L472 1436 L474 1455 L465 1466 L340 1468 L305 1458 Z" />
    <!-- Sole groove / bottom contour shadow -->
    <path fill="{SHOE_SOLE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="2" stroke-linejoin="round" d="M307 1453 L340 1463 L466 1461 L465 1466 L340 1468 L305 1458 Z" />
  </g>
</svg>"""

    # 20. leg_upper_right (thigh right from hip to knee)
    # Hip pivot at (565, 870), Knee pivot at (575, 1100)
    layers["leg_upper_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_right">
    <!-- Hip overlap cap (hidden under torso waistband) -->
    <circle cx="565" cy="870" r="48" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Thigh body -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M505 870 L520 1100 L620 1100 L610 870 Z" />
    <path fill="{JEANS_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M507 870 L525 1100 L613 1100 L600 870 Z" />
    <!-- Knee hem covering lower leg cap -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M515 1095 Q570 1108 625 1095" />
  </g>
</svg>"""

    # 21. leg_lower_right (calf right from knee to ankle, with jeans cuff)
    # Knee pivot at (575, 1100), Ankle pivot at (580, 1345)
    layers["leg_lower_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_lower_right">
    <!-- Knee overlap cap (hidden under upper leg knee hem) -->
    <circle cx="575" cy="1100" r="42" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Calf body -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M520 1100 L525 1310 L625 1310 L620 1100 Z" />
    <path fill="{JEANS_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M525 1100 L527 1310 L613 1310 L613 1100 Z" />
    <!-- Jeans cuff at ankle (covers shoe joint cap) -->
    <rect x="522" y="1305" width="108" height="40" rx="6" fill="{JEANS_CUFF}" stroke="{STROKE_THICK}" stroke-width="6" />
  </g>
</svg>"""

    # 22. shoe_right (authentic 3/4 perspective sneaker matching boy_b_front_large.png)
    # Ankle pivot at (580, 1345)
    layers["shoe_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_right">
    <!-- Ankle joint cap (tucks under jeans cuff at (580, 1345)) -->
    <circle cx="580" cy="1345" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- White sock sliver on medial side -->
    <path fill="{SOCK_WHITE}" stroke="{STROKE_THICK}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" d="M558 1338 L532 1338 L532 1368 L558 1368 Z" />
    
    <!-- Purple tongue (flat/angled top sticking out under cuff) -->
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M616 1338 L558 1338 L560 1364 L614 1364 Z" />
    
    <!-- Throat / Instep Underlay (dark purple canvas behind laces) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M614 1364 L560 1364 L596 1442 L654 1420 Z" />
    
    <!-- 4 White Laces Bars across instep -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M617 1368 L564 1369 L569 1378 L622 1377 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M627 1382 L574 1384 L579 1393 L632 1391 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M637 1396 L584 1399 L589 1408 L642 1405 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="2.5" stroke-linejoin="round" d="M647 1410 L593 1414 L598 1423 L652 1419 Z" />

    <!-- Lateral purple canvas quarter (heel counter / side panel) -->
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M560 1362 L532 1372 L528 1436 L596 1444 L560 1362 Z" />
    <!-- Heel shadow/contour accent -->
    <path fill="{SHOE_SHADOW}" d="M545 1370 L532 1372 L528 1436 L542 1438 Z" />

    <!-- White rubber toe cap (Solid 3D volume matching source) -->
    <!-- Top slope facet -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M654 1420 L596 1424 L596 1444 L655 1448 L692 1436 Z" />
    <!-- Front vertical face facet -->
    <path fill="#f0f3f6" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M692 1436 L655 1448 L596 1444 L604 1453 L662 1457 L695 1446 Z" />

    <!-- Thick Rubber Sole (continuous, clean, solid outline) -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M695 1446 L662 1457 L596 1444 L528 1436 L526 1455 L535 1466 L660 1468 L695 1458 Z" />
    <!-- Sole groove / bottom contour shadow -->
    <path fill="{SHOE_SOLE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="2" stroke-linejoin="round" d="M693 1453 L660 1463 L534 1461 L535 1466 L660 1468 L695 1458 Z" />
  </g>
</svg>"""

    # 23. torso_back (hoodie back, draped hood with center seam, waistband, NO front zipper/pocket)
    layers["torso_back"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_torso_back">
    <!-- Interior hood opening shadow -->
    <path fill="{HOODIE_INNER}" d="M440 480 C460 460 540 460 560 480 C540 500 460 500 440 480 Z" />
    
    <!-- Torso main body back -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M395 520 L370 805 L630 805 L605 520 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M405 515 C440 528 560 528 595 515 L622 805 L378 805 Z" />
    
    <!-- Side seam accents matching boy_b_right.png -->
    <line x1="420" y1="640" x2="400" y2="800" stroke="{STROKE_SUBTLE}" stroke-width="3.5" stroke-linecap="round" />
    <line x1="580" y1="640" x2="600" y2="800" stroke="{STROKE_SUBTLE}" stroke-width="3.5" stroke-linecap="round" />
    
    <!-- Ribbed Waistband / hem -->
    <rect x="370" y="805" width="260" height="68" rx="6" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <rect x="375" y="805" width="250" height="62" rx="4" fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" />
    <line x1="375" y1="836" x2="625" y2="836" stroke="{HOODIE_SHADOW}" stroke-width="3" stroke-linecap="round" />
    
    <!-- Draped Hood down over upper back (curved draped hood with center seam, NO front zipper/pocket) -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M435 480 C395 520 400 635 500 670 C600 635 605 520 565 480 C540 465 460 465 435 480 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M440 484 C408 522 412 625 500 660 C588 625 592 522 560 484 C538 472 462 472 440 484 Z" />
    
    <!-- Inner fold depth of draped hood -->
    <path fill="{HOODIE_SHADOW}" d="M455 490 C430 525 435 595 500 635 C565 595 570 525 545 490 C560 520 555 580 500 615 C445 580 440 520 455 490 Z" />
    
    <!-- Hood center back seam -->
    <path fill="none" stroke="{STROKE_THICK}" stroke-width="4.5" stroke-linecap="round" d="M500 472 L500 660" />
  </g>
</svg>"""

    # 24. shoe_back_left (rear view of left sneaker: heel counter, purple pull tab, white sole)
    layers["shoe_back_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_back_left">
    <!-- Ankle joint cap tucks under jeans cuff at (420, 1345) -->
    <circle cx="420" cy="1345" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- White sock band under cuff -->
    <rect x="390" y="1335" width="60" height="25" rx="3" fill="{SOCK_WHITE}" stroke="{STROKE_THICK}" stroke-width="4.5" />
    
    <!-- Heel counter (purple canvas rear cup) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M372 1358 L468 1358 L476 1445 L364 1445 Z" />
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THIN}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M380 1360 L460 1360 L470 1443 L370 1443 Z" />
    
    <!-- Vertical Purple Heel Pull Tab -->
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THICK}" stroke-width="3.5" stroke-linecap="round" d="M413 1355 Q420 1342 427 1355" />
    <rect x="413" y="1350" width="14" height="85" rx="3" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="3" />
    <rect x="415" y="1352" width="10" height="81" rx="2" fill="{SHOE_PURPLE}" />
    
    <!-- White Rubber Sole (continuous wrapped heel sole) -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M360 1445 L480 1445 L480 1466 L360 1466 Z" />
    <rect x="360" y="1460" width="120" height="6" fill="{SHOE_SOLE_SHADOW}" />
  </g>
</svg>"""

    # 25. shoe_back_right (rear view of right sneaker: heel counter, purple pull tab, white sole)
    layers["shoe_back_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_back_right">
    <!-- Ankle joint cap tucks under jeans cuff at (580, 1345) -->
    <circle cx="580" cy="1345" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- White sock band under cuff -->
    <rect x="550" y="1335" width="60" height="25" rx="3" fill="{SOCK_WHITE}" stroke="{STROKE_THICK}" stroke-width="4.5" />
    
    <!-- Heel counter (purple canvas rear cup) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M532 1358 L628 1358 L636 1445 L524 1445 Z" />
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THIN}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M540 1360 L620 1360 L630 1443 L530 1443 Z" />
    
    <!-- Vertical Purple Heel Pull Tab -->
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THICK}" stroke-width="3.5" stroke-linecap="round" d="M573 1355 Q580 1342 587 1355" />
    <rect x="573" y="1350" width="14" height="85" rx="3" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="3" />
    <rect x="575" y="1352" width="10" height="81" rx="2" fill="{SHOE_PURPLE}" />
    
    <!-- White Rubber Sole (continuous wrapped heel sole) -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_THICK}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M520 1445 L640 1445 L640 1466 L520 1466 Z" />
    <rect x="520" y="1460" width="120" height="6" fill="{SHOE_SOLE_SHADOW}" />
  </g>
</svg>"""

    # 26. leg_upper_back_left (left thigh back with rear pocket and yoke seam)
    layers["leg_upper_back_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_back_left">
    <circle cx="435" cy="870" r="48" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M390 870 L380 1100 L480 1100 L495 870 Z" />
    <path fill="{JEANS_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M400 870 L390 1100 L475 1100 L493 870 Z" />
    <!-- Rear horizontal yoke seam -->
    <line x1="395" y1="895" x2="495" y2="915" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" />
    <!-- Rear pocket left -->
    <polygon points="410,915 470,915 465,978 440,992 415,978" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="4" stroke-linejoin="round" />
    <path fill="none" stroke="{STROKE_SUBTLE}" stroke-width="2.5" d="M420 940 Q440 958 460 940" />
    <!-- Center back seam line -->
    <line x1="495" y1="915" x2="480" y2="1100" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" />
    <!-- Knee hem -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M375 1095 Q430 1108 485 1095" />
  </g>
</svg>"""

    # 27. leg_upper_back_right (right thigh back with rear pocket and yoke seam)
    layers["leg_upper_back_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_back_right">
    <circle cx="565" cy="870" r="48" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M505 870 L520 1100 L620 1100 L610 870 Z" />
    <path fill="{JEANS_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M507 870 L525 1100 L613 1100 L600 870 Z" />
    <!-- Rear horizontal yoke seam -->
    <line x1="505" y1="915" x2="605" y2="895" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" />
    <!-- Rear pocket right -->
    <polygon points="530,915 590,915 585,978 560,992 535,978" fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="4" stroke-linejoin="round" />
    <path fill="none" stroke="{STROKE_SUBTLE}" stroke-width="2.5" d="M540 940 Q560 958 580 940" />
    <!-- Center back seam line -->
    <line x1="505" y1="915" x2="520" y2="1100" stroke="{STROKE_THICK}" stroke-width="4" stroke-linecap="round" />
    <!-- Knee hem -->
    <path fill="{JEANS_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" d="M515 1095 Q570 1108 625 1095" />
  </g>
</svg>"""

    return layers


def get_girl_a_layers() -> Dict[str, str]:
    """Returns SVG content for all 22 layers of girl_a."""
    STROKE_MAIN = "#2a1523"
    STROKE_INNER = "#2a1523"
    STROKE_FACET = "#3e1b12"
    HAIR_DARK = "#9e3108"
    HAIR_MID = "#d34a10"
    HAIR_BASE = "#eb5e1b"
    HAIR_LIGHT = "#f8782a"
    SKIN_BASE = "#fedbc3"
    SKIN_SHADOW = "#f1b799"
    FRECKLE = "#d5896a"
    SHIRT_DARK = "#2b1f2b"
    VEST_BASE = "#934c9c"
    VEST_SHADOW = "#6f3477"
    PANTS_BASE = "#395779"
    PANTS_SHADOW = "#293f59"
    PANTS_CUFF = "#4d7199"
    GLASSES_RIM = "#5b285f"
    GLASSES_INNER = "#7b3880"
    IRIS_BASE = "#208759"
    IRIS_DARK = "#135537"
    IRIS_LIGHT = "#51ba86"
    PUPIL = "#162319"
    MOUTH_DARK = "#2a1523"
    MOUTH_TONGUE = "#e27a7a"
    MOUTH_TEETH = "#ffffff"
    SHOE_BASE = "#934c9c"
    SHOE_SHADOW = "#6f3477"
    SHOE_WHITE = "#ffffff"
    SHOE_SOLE = "#f0e8f2"
    SHOE_SOLE_SHADOW = "#ded4e0"

    layers = {}

    # 1. head_back
    layers["head_back"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_back">
    <path fill="{HAIR_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M500 45 L440 85 L375 120 L320 165 L270 235 L240 310 L275 345 L220 415 L280 435 L225 510 L300 500 L285 570 L360 520 L370 580 L440 510 L500 540 L560 510 L630 580 L640 520 L715 570 L700 500 L775 510 L720 435 L780 415 L725 345 L760 310 L730 235 L680 165 L625 120 L560 85 Z" />
    <polygon points="240,310 275,345 320,290" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="275,345 220,415 300,380" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="220,415 280,435 295,455" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="280,435 225,510 300,480" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="760,310 725,345 680,290" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="725,345 780,415 700,380" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="780,415 720,435 705,455" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="720,435 775,510 700,480" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <!-- Top Back Facets for back view -->
    <polygon points="500,45 440,85 500,140" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="500,45 500,140 560,85" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="440,85 375,120 440,165" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="440,85 440,165 500,140" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="560,85 500,140 560,165" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="560,85 625,120 560,165" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
  </g>
</svg>"""

    # 2. head_base (neck, ears, cranium, jaw, eyebrows, glasses frames, freckles, nose, front hair - NO eyes, NO mouth)
    layers["head_base"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_base">
    <!-- Neck extending under collar -->
    <path fill="{SKIN_SHADOW}" d="M460 450 L460 550 L540 550 L540 450 Z" />
    <line x1="460" y1="450" x2="460" y2="520" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" />
    <line x1="540" y1="450" x2="540" y2="520" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" />
    <path fill="{SKIN_BASE}" d="M468 450 L468 545 C468 552 532 552 532 545 L532 450 Z" />
    <line x1="468" y1="450" x2="468" y2="520" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" />
    <line x1="532" y1="450" x2="532" y2="520" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" />
    <!-- Ears -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M370 340 C310 340 310 420 370 430 Z" />
    <path fill="none" stroke="{SKIN_SHADOW}" stroke-width="4" stroke-linecap="round" d="M360 365 C340 370 340 395 360 405" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M630 340 C690 340 690 420 630 430 Z" />
    <path fill="none" stroke="{SKIN_SHADOW}" stroke-width="4" stroke-linecap="round" d="M640 365 C660 370 660 395 640 405" />
    <!-- Face Jaw and Cranium (full dome prevents hair gap bleed) -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M350 310 C350 100 650 100 650 310 C640 420 590 485 500 485 C410 485 360 420 360 310 Z" />
    <path fill="{SKIN_SHADOW}" d="M470 460 C430 460 395 435 385 400 C410 440 450 455 500 455 C550 455 590 440 615 400 C605 435 570 460 530 460 Z" />
    <!-- Eyebrows -->
    <path fill="{HAIR_DARK}" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M390 295 Q435 278 475 296 L468 312 Q435 298 395 310 Z" />
    <path fill="{HAIR_DARK}" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M610 295 Q565 278 525 296 L532 312 Q565 298 605 310 Z" />
    <!-- Round Thick Purple Glasses Frames -->
    <circle cx="440" cy="360" r="54" fill="none" stroke="{GLASSES_RIM}" stroke-width="12" stroke-linecap="round" />
    <circle cx="440" cy="360" r="48" fill="none" stroke="{GLASSES_INNER}" stroke-width="4" />
    <circle cx="560" cy="360" r="54" fill="none" stroke="{GLASSES_RIM}" stroke-width="12" stroke-linecap="round" />
    <circle cx="560" cy="360" r="48" fill="none" stroke="{GLASSES_INNER}" stroke-width="4" />
    <path fill="none" stroke="{GLASSES_RIM}" stroke-width="10" stroke-linecap="round" d="M494 360 Q500 348 506 360" />
    <line x1="386" y1="358" x2="340" y2="350" stroke="{GLASSES_RIM}" stroke-width="9" stroke-linecap="round" />
    <line x1="614" y1="358" x2="660" y2="350" stroke="{GLASSES_RIM}" stroke-width="9" stroke-linecap="round" />
    <!-- Freckles -->
    <circle cx="395" cy="410" r="3" fill="{FRECKLE}" />
    <circle cx="410" cy="418" r="3.5" fill="{FRECKLE}" />
    <circle cx="425" cy="412" r="3" fill="{FRECKLE}" />
    <circle cx="405" cy="426" r="2.5" fill="{FRECKLE}" />
    <circle cx="605" cy="410" r="3" fill="{FRECKLE}" />
    <circle cx="590" cy="418" r="3.5" fill="{FRECKLE}" />
    <circle cx="575" cy="412" r="3" fill="{FRECKLE}" />
    <circle cx="595" cy="426" r="2.5" fill="{FRECKLE}" />
    <!-- Nose -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M492 390 Q500 402 508 390 Z" />
    <!-- Hair Front Solid Silhouette Underlay (prevents seam slivers, pinholes, and white gaps) -->
    <path fill="{HAIR_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M500 45 L440 90 L375 125 L320 170 L295 245 L345 280 L375 250 L390 205 L445 215 L485 250 L500 205 L515 250 L555 215 L610 205 L625 250 L655 280 L705 245 L680 170 L625 125 L560 90 Z" />
    <!-- Hair Front Facets -->
    <polygon points="500,45 440,90 500,115" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="500,45 500,115 560,90" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="440,90 375,125 435,145" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="440,90 435,145 500,115" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="560,90 500,115 565,145" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="560,90 625,125 565,145" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="435,145 390,205 445,215" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="435,145 445,215 480,175" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="500,115 435,145 480,175" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="500,115 480,175 520,175" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="500,115 520,175 565,145" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="565,145 520,175 555,215" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="565,145 555,215 610,205" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="480,175 445,215 485,250" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="480,175 485,250 500,205" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <!-- Center connecting facet (previously missing, leaving white hole) -->
    <polygon points="480,175 520,175 500,205" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="520,175 500,205 515,250" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="520,175 515,250 555,215" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="375,125 320,170 355,220" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="375,125 355,220 390,205" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="355,220 295,245 345,280" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="355,220 345,280 375,250" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="355,220 375,250 390,205" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="625,125 610,205 645,220" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="625,125 645,220 680,170" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="645,220 625,250 655,280" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="645,220 610,205 625,250" fill="{HAIR_BASE}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="645,220 655,280 705,245" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <!-- Outer Contour Stroke -->
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M500 45 L440 90 L375 125 L320 170 L295 245 L345 280 L375 250 L390 205 L445 215 L485 250 L500 205 L515 250 L555 215 L610 205 L625 250 L655 280 L705 245 L680 170 L625 125 L560 90 Z" />
  </g>
</svg>"""

    # 3. eyes_open
    layers["eyes_open"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_open">
    <!-- Left Eye -->
    <ellipse cx="440" cy="360" rx="42" ry="44" fill="#ffffff" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="442" cy="360" rx="28" ry="30" fill="{IRIS_DARK}" />
    <ellipse cx="442" cy="362" rx="24" ry="26" fill="{IRIS_BASE}" />
    <ellipse cx="442" cy="368" rx="18" ry="16" fill="{IRIS_LIGHT}" />
    <ellipse cx="442" cy="360" rx="15" ry="16" fill="{PUPIL}" />
    <circle cx="432" cy="350" r="9" fill="#ffffff" />
    <circle cx="454" cy="370" r="4.5" fill="#ffffff" />
    <!-- Right Eye -->
    <ellipse cx="560" cy="360" rx="42" ry="44" fill="#ffffff" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="558" cy="360" rx="28" ry="30" fill="{IRIS_DARK}" />
    <ellipse cx="558" cy="362" rx="24" ry="26" fill="{IRIS_BASE}" />
    <ellipse cx="558" cy="368" rx="18" ry="16" fill="{IRIS_LIGHT}" />
    <ellipse cx="558" cy="360" rx="15" ry="16" fill="{PUPIL}" />
    <circle cx="550" cy="350" r="9" fill="#ffffff" />
    <circle cx="572" cy="370" r="4.5" fill="#ffffff" />
  </g>
</svg>"""

    # 4. eyes_blink
    layers["eyes_blink"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_blink">
    <!-- Left Eye Blink curve -->
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" d="M412 362 Q440 378 468 362" />
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" d="M424 370 L418 379" />
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" d="M456 370 L462 379" />
    <!-- Right Eye Blink curve -->
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" d="M532 362 Q560 378 588 362" />
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" d="M544 370 L538 379" />
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" d="M576 370 L582 379" />
  </g>
</svg>"""

    # 5. eyes_look_left
    layers["eyes_look_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_look_left">
    <!-- Left Eye: Look Left -->
    <ellipse cx="440" cy="360" rx="42" ry="44" fill="#ffffff" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="428" cy="360" rx="26" ry="30" fill="{IRIS_DARK}" />
    <ellipse cx="428" cy="362" rx="22" ry="26" fill="{IRIS_BASE}" />
    <ellipse cx="428" cy="368" rx="16" ry="16" fill="{IRIS_LIGHT}" />
    <ellipse cx="428" cy="360" rx="13" ry="16" fill="{PUPIL}" />
    <circle cx="420" cy="350" r="8" fill="#ffffff" />
    <circle cx="440" cy="370" r="4" fill="#ffffff" />
    <!-- Right Eye: Look Left -->
    <ellipse cx="560" cy="360" rx="42" ry="44" fill="#ffffff" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="546" cy="360" rx="26" ry="30" fill="{IRIS_DARK}" />
    <ellipse cx="546" cy="362" rx="22" ry="26" fill="{IRIS_BASE}" />
    <ellipse cx="546" cy="368" rx="16" ry="16" fill="{IRIS_LIGHT}" />
    <ellipse cx="546" cy="360" rx="13" ry="16" fill="{PUPIL}" />
    <circle cx="538" cy="350" r="8" fill="#ffffff" />
    <circle cx="558" cy="370" r="4" fill="#ffffff" />
  </g>
</svg>"""

    # 6. eyes_look_right
    layers["eyes_look_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_eyes_look_right">
    <!-- Left Eye: Look Right -->
    <ellipse cx="440" cy="360" rx="42" ry="44" fill="#ffffff" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="454" cy="360" rx="26" ry="30" fill="{IRIS_DARK}" />
    <ellipse cx="454" cy="362" rx="22" ry="26" fill="{IRIS_BASE}" />
    <ellipse cx="454" cy="368" rx="16" ry="16" fill="{IRIS_LIGHT}" />
    <ellipse cx="454" cy="360" rx="13" ry="16" fill="{PUPIL}" />
    <circle cx="446" cy="350" r="8" fill="#ffffff" />
    <circle cx="466" cy="370" r="4" fill="#ffffff" />
    <!-- Right Eye: Look Right -->
    <ellipse cx="560" cy="360" rx="42" ry="44" fill="#ffffff" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="572" cy="360" rx="26" ry="30" fill="{IRIS_DARK}" />
    <ellipse cx="572" cy="362" rx="22" ry="26" fill="{IRIS_BASE}" />
    <ellipse cx="572" cy="368" rx="16" ry="16" fill="{IRIS_LIGHT}" />
    <ellipse cx="572" cy="360" rx="13" ry="16" fill="{PUPIL}" />
    <circle cx="564" cy="350" r="8" fill="#ffffff" />
    <circle cx="584" cy="370" r="4" fill="#ffffff" />
  </g>
</svg>"""

    # 7. mouth_closed
    layers["mouth_closed"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_closed">
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" d="M465 425 Q500 440 535 425" />
    <path fill="{SKIN_SHADOW}" d="M490 440 Q500 445 510 440 Z" />
  </g>
</svg>"""

    # 8. mouth_slightly_open
    layers["mouth_slightly_open"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_slightly_open">
    <path fill="{MOUTH_DARK}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M470 422 Q500 415 530 422 Q500 442 470 422 Z" />
    <path fill="{MOUTH_TEETH}" d="M478 422 Q500 417 522 422 Q500 427 478 422 Z" />
    <path fill="{SKIN_SHADOW}" d="M490 444 Q500 448 510 444 Z" />
  </g>
</svg>"""

    # 9. mouth_wide_open
    layers["mouth_wide_open"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_wide_open">
    <path fill="{MOUTH_DARK}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M462 416 Q500 410 538 416 C538 452 522 464 500 464 C478 464 462 452 462 416 Z" />
    <path fill="{MOUTH_TEETH}" d="M470 416 Q500 412 530 416 C528 426 472 426 470 416 Z" />
    <path fill="{MOUTH_TONGUE}" d="M480 460 C485 445 515 445 520 460 C510 463 490 463 480 460 Z" />
    <path fill="{SKIN_SHADOW}" d="M488 468 Q500 472 512 468 Z" />
  </g>
</svg>"""

    # 10. mouth_round_o
    layers["mouth_round_o"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_round_o">
    <ellipse cx="500" cy="428" rx="18" ry="22" fill="{MOUTH_DARK}" stroke="{STROKE_MAIN}" stroke-width="5" />
    <ellipse cx="500" cy="436" rx="10" ry="8" fill="{MOUTH_TONGUE}" />
    <path fill="{SKIN_SHADOW}" d="M490 454 Q500 458 510 454 Z" />
  </g>
</svg>"""

    # 11. mouth_open_smile
    layers["mouth_open_smile"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_mouth_open_smile">
    <path fill="{MOUTH_DARK}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M458 418 Q500 408 542 418 C537 455 520 462 500 462 C480 462 463 455 458 418 Z" />
    <path fill="{MOUTH_TEETH}" stroke="{STROKE_INNER}" stroke-width="2" d="M465 418 Q500 410 535 418 C530 428 470 428 465 418 Z" />
    <path fill="{MOUTH_TONGUE}" d="M478 458 C484 444 516 444 522 458 C512 461 488 461 478 458 Z" />
    <path fill="{SKIN_SHADOW}" d="M488 466 Q500 470 512 466 Z" />
  </g>
</svg>"""

    # 12. torso (crew-neck collar, dark t-shirt underlay, curved waistcoat vest panels, jeans waistband with fly)
    # Hip joints at (435, 930) and (565, 930), Vest hem extends to y=948
    layers["torso"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_torso">
    <!-- Neck skin base connection under collar -->
    <path fill="{SKIN_BASE}" stroke="none" d="M465 500 L465 524 Q500 545 535 524 L535 500 Z" />
    
    <!-- Dark under-shirt body -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M412 522 L360 670 L366 885 L634 885 L640 670 L588 522 Z" />
    
    <!-- Crew-neck ribbed collar band -->
    <path fill="#221622" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M455 516 Q500 552 545 516 C548 532 542 544 538 549 Q500 568 462 549 C458 544 452 532 455 516 Z" />
    <!-- Collar inner rim shadow -->
    <path fill="none" stroke="#180f19" stroke-width="2.5" stroke-linecap="round" d="M459 524 Q500 556 541 524" />
    
    <!-- Jeans Waistband & Pelvis Area (covers leg joints, shows between vest panels) -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M366 880 L362 945 L638 945 L634 880 Z" />
    <path fill="{PANTS_BASE}" stroke="none" d="M368 883 L364 942 L636 942 L632 883 Z" />
    <!-- Jeans Fly / J-stitch -->
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" d="M500 882 L500 928 C500 938 492 944 482 944" />
    <!-- Rivet / Waistband Button -->
    <circle cx="500" cy="894" r="5" fill="#d29a4a" stroke="{STROKE_MAIN}" stroke-width="2.5" />
    <!-- Curved Pocket Openings on sides -->
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linecap="round" d="M395 905 Q415 918 425 942" />
    <path fill="none" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linecap="round" d="M605 905 Q585 918 575 942" />

    <!-- Vest Shadow on Flanks -->
    <path fill="{VEST_SHADOW}" d="M412 522 L368 670 C364 730 362 800 365 860 L368 915 C372 935 380 948 398 948 L460 942 C470 938 474 928 472 915 C468 850 464 760 458 680 L442 522 Z" />
    <path fill="{VEST_SHADOW}" d="M588 522 L632 670 C636 730 638 800 635 860 L632 915 C628 935 620 948 602 948 L540 942 C530 938 526 928 528 915 C532 850 536 760 542 680 L558 522 Z" />

    <!-- Left Vest Panel (Tailored sleeveless waistcoat with curved lapel, clean armhole, rounded hem) -->
    <path fill="{VEST_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M442 522 L408 528 C418 572 405 624 372 670 C366 730 364 800 366 860 L370 915 C372 935 382 948 398 948 C420 948 445 946 460 942 C470 938 474 926 472 915 C468 850 464 760 458 680 C454 620 448 565 442 522 Z" />
    <!-- Left Lapel facing accent line -->
    <path fill="none" stroke="#7b3a82" stroke-width="3" stroke-linecap="round" d="M445 535 C451 615 456 715 460 815 C462 855 463 895 464 925" />

    <!-- Right Vest Panel (Tailored sleeveless waistcoat with curved lapel, clean armhole, rounded hem) -->
    <path fill="{VEST_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M558 522 L592 528 C582 572 595 624 628 670 C634 730 636 800 634 860 L630 915 C628 935 618 948 602 948 C580 948 555 946 540 942 C530 938 526 926 528 915 C532 850 536 760 542 680 C546 620 552 565 558 522 Z" />
    <!-- Right Lapel facing accent line -->
    <path fill="none" stroke="#7b3a82" stroke-width="3" stroke-linecap="round" d="M555 535 C549 615 544 715 540 815 C538 855 537 895 536 925" />
  </g>
</svg>"""

    # 13. arm_upper_left (short shirt sleeve from shoulder to elbow)
    # Shoulder at (415, 525), Elbow at (345, 705)
    layers["arm_upper_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_upper_left">
    <!-- Shoulder overlap cap (tucks under torso shoulder) -->
    <circle cx="415" cy="525" r="32" fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Sleeve Body -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M415 525 L310 680 L385 715 L435 550 Z" />
    <!-- Sleeve Cuff (covers forearm joint cap) -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M305 675 L388 718" />
  </g>
</svg>"""

    # 14. arm_lower_left (forearm skin and hand left)
    # Elbow at (345, 705), Wrist at (300, 945), Hand to 1075
    layers["arm_lower_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_lower_left">
    <!-- Elbow overlap cap extending into sleeve cuff -->
    <circle cx="345" cy="705" r="28" fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" />
    <!-- Forearm skin -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M335 695 L270 940 L340 950 L375 710 Z" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M340 695 L278 940 L338 950 L370 710 Z" />
    <!-- Redrawn Hand matching hands sheet -->
    <g id="girl_hand_l">
      <!-- Wrist link -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M280 940 L260 1010 L320 1025 L335 945 Z" />
      <!-- Palm -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M272 970 C248 1005 244 1040 254 1068 C264 1088 284 1088 298 1074 C318 1054 326 1020 322 975 Z" />
      <!-- Inward Thumb -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M305 985 C325 1005 334 1028 328 1045 C320 1056 310 1050 302 1035 Z" />
      <!-- Fingers Crease Lines -->
      <line x1="270" y1="1075" x2="270" y2="1032" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" />
      <line x1="282" y1="1078" x2="282" y2="1028" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" />
      <line x1="294" y1="1072" x2="294" y2="1028" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" />
    </g>
  </g>
</svg>"""

    # 15. arm_upper_right (short shirt sleeve from shoulder to elbow)
    # Shoulder at (585, 525), Elbow at (655, 705)
    layers["arm_upper_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_upper_right">
    <!-- Shoulder overlap cap (tucks under torso shoulder) -->
    <circle cx="585" cy="525" r="32" fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Sleeve Body -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M585 525 L690 680 L615 715 L565 550 Z" />
    <!-- Sleeve Cuff (covers forearm joint cap) -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M695 675 L612 718" />
  </g>
</svg>"""

    # 16. arm_lower_right (forearm skin and hand right)
    # Elbow at (655, 705), Wrist at (700, 945), Hand to 1075
    layers["arm_lower_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_lower_right">
    <!-- Elbow overlap cap extending into sleeve cuff -->
    <circle cx="655" cy="705" r="28" fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" />
    <!-- Forearm skin -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M665 695 L730 940 L660 950 L625 710 Z" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M660 695 L722 940 L662 950 L630 710 Z" />
    <!-- Redrawn Hand matching hands sheet -->
    <g id="girl_hand_r">
      <!-- Wrist link -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M720 940 L740 1010 L680 1025 L665 945 Z" />
      <!-- Palm -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M728 970 C752 1005 756 1040 746 1068 C736 1088 716 1088 702 1074 C682 1054 674 1020 678 975 Z" />
      <!-- Inward Thumb -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M695 985 C675 1005 666 1028 672 1045 C680 1056 690 1050 698 1035 Z" />
      <!-- Fingers Crease Lines -->
      <line x1="730" y1="1075" x2="730" y2="1032" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" />
      <line x1="718" y1="1078" x2="718" y2="1028" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" />
      <line x1="706" y1="1072" x2="706" y2="1028" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" />
    </g>
  </g>
</svg>"""

    # 17. leg_upper_left (thigh left from hip to knee)
    # Hip at (435, 930), Knee at (415, 1150)
    layers["leg_upper_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_left">
    <!-- Hip overlap cap (tucks under vest hem) -->
    <circle cx="435" cy="930" r="48" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Thigh body -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M375 920 L358 1150 L470 1150 L485 920 Z" />
    <path fill="{PANTS_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M388 920 L370 1150 L465 1150 L482 920 Z" />
    <!-- Knee hem covering lower leg cap -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" d="M355 1145 Q415 1158 475 1145" />
  </g>
</svg>"""

    # 18. leg_lower_left (calf left from knee to ankle, with cuff)
    # Knee at (415, 1150), Ankle at (400, 1370)
    layers["leg_lower_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_lower_left">
    <!-- Knee overlap cap (tucks under thigh hem) -->
    <circle cx="415" cy="1150" r="44" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Calf body -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M358 1150 L345 1370 L465 1370 L470 1150 Z" />
    <path fill="{PANTS_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M370 1150 L360 1370 L462 1370 L465 1150 Z" />
    <!-- Pants cuff at ankle (covers shoe joint cap) -->
    <rect x="335" y="1360" width="135" height="52" rx="8" fill="{PANTS_CUFF}" stroke="{STROKE_MAIN}" stroke-width="6" />
  </g>
</svg>"""

    # 19. shoe_left (authentic 3/4 perspective sneaker matching girl_a vest palette)
    # Ankle at (400, 1370), Cuff ends at 1412
    layers["shoe_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_left">
    <!-- Ankle joint cap (tucks under pants cuff at (400, 1370)) -->
    <circle cx="400" cy="1370" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" />
    
    <!-- Bare skin on medial side (inner ankle) -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" d="M418 1406 L444 1406 L444 1426 L418 1426 Z" />
    
    <!-- Sneaker Tongue (purple rounded top sticking out above collar) -->
    <path fill="{SHOE_BASE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M366 1410 C374 1402 410 1402 418 1410 L418 1426 L366 1426 Z" />
    
    <!-- Throat / Instep Underlay (dark purple canvas) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M366 1426 L418 1426 L394 1474 L342 1456 Z" />
    
    <!-- 3 White Laces Bars across instep -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="2.5" stroke-linejoin="round" d="M365 1429 C380 1432 400 1432 414 1429 L411 1437 C397 1440 378 1440 362 1437 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="2.5" stroke-linejoin="round" d="M355 1441 C371 1445 391 1445 405 1441 L402 1449 C388 1453 368 1453 352 1449 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="2.5" stroke-linejoin="round" d="M346 1453 C362 1457 382 1457 396 1453 L393 1461 C379 1465 359 1465 343 1461 Z" />

    <!-- Lateral purple canvas quarter (heel counter) -->
    <path fill="{SHOE_BASE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M418 1424 L446 1432 C454 1446 456 1460 454 1471 L394 1475 L418 1424 Z" />
    <!-- Heel shadow accent -->
    <path fill="{SHOE_SHADOW}" d="M438 1431 C446 1445 450 1458 450 1471 L440 1472 C440 1458 434 1444 426 1432 Z" />

    <!-- Rubber Toe Cap (Rounded 3D dome matching girl_a_body.png) -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M342 1456 C324 1460 312 1466 312 1474 C312 1478 322 1481 350 1479 L394 1475 L394 1466 Z" />
    <!-- Toe highlight -->
    <path fill="#fbf8fc" d="M340 1459 C326 1463 316 1468 316 1474 L348 1473 L390 1470 L388 1464 Z" />

    <!-- Thick Rubber Sole (continuous, max y = 1490, NO CLIPPING) -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M312 1474 C311 1480 318 1488 348 1490 L448 1487 C455 1484 456 1476 454 1471 L394 1475 C360 1478 326 1478 312 1474 Z" />
    <!-- Sole shadow contour -->
    <path fill="{SHOE_SOLE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="2" stroke-linejoin="round" d="M314 1480 C328 1483 358 1484 398 1482 L452 1478 L450 1483 C444 1486 415 1488 358 1488 C328 1488 316 1484 314 1480 Z" />
  </g>
</svg>"""

    # 20. leg_upper_right (thigh right from hip to knee)
    # Hip at (565, 930), Knee at (585, 1150)
    layers["leg_upper_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_right">
    <!-- Hip overlap cap (tucks under vest hem) -->
    <circle cx="565" cy="930" r="48" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Thigh body -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M515 920 L530 1150 L642 1150 L625 920 Z" />
    <path fill="{PANTS_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M518 920 L535 1150 L630 1150 L612 920 Z" />
    <!-- Knee hem covering lower leg cap -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" d="M525 1145 Q585 1158 645 1145" />
  </g>
</svg>"""

    # 21. leg_lower_right (calf right from knee to ankle, with cuff)
    # Knee at (585, 1150), Ankle at (600, 1370)
    layers["leg_lower_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_lower_right">
    <!-- Knee overlap cap (tucks under thigh hem) -->
    <circle cx="585" cy="1150" r="44" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Calf body -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M530 1150 L535 1370 L655 1370 L642 1150 Z" />
    <path fill="{PANTS_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M535 1150 L538 1370 L640 1370 L630 1150 Z" />
    <!-- Pants cuff at ankle (covers shoe joint cap) -->
    <rect x="530" y="1360" width="135" height="52" rx="8" fill="{PANTS_CUFF}" stroke="{STROKE_MAIN}" stroke-width="6" />
  </g>
</svg>"""

    # 22. shoe_right (authentic 3/4 perspective sneaker matching girl_a vest palette)
    # Ankle at (600, 1370), Cuff ends at 1412
    layers["shoe_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_right">
    <!-- Ankle joint cap (tucks under pants cuff at (600, 1370)) -->
    <circle cx="600" cy="1370" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" />
    
    <!-- Bare skin on medial side (inner ankle) -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" d="M582 1406 L556 1406 L556 1426 L582 1426 Z" />
    
    <!-- Sneaker Tongue (purple rounded top sticking out above collar) -->
    <path fill="{SHOE_BASE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M634 1410 C626 1402 590 1402 582 1410 L582 1426 L634 1426 Z" />
    
    <!-- Throat / Instep Underlay (dark purple canvas) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M634 1426 L582 1426 L606 1474 L658 1456 Z" />
    
    <!-- 3 White Laces Bars across instep -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="2.5" stroke-linejoin="round" d="M635 1429 C620 1432 600 1432 586 1429 L589 1437 C603 1440 622 1440 638 1437 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="2.5" stroke-linejoin="round" d="M645 1441 C629 1445 609 1445 595 1441 L598 1449 C612 1453 632 1453 648 1449 Z" />
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="2.5" stroke-linejoin="round" d="M654 1453 C638 1457 618 1457 604 1453 L607 1461 C621 1465 641 1465 657 1461 Z" />

    <!-- Lateral purple canvas quarter (heel counter) -->
    <path fill="{SHOE_BASE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M582 1424 L554 1432 C546 1446 544 1460 546 1471 L606 1475 L582 1424 Z" />
    <!-- Heel shadow accent -->
    <path fill="{SHOE_SHADOW}" d="M562 1431 C554 1445 550 1458 550 1471 L560 1472 C560 1458 566 1444 574 1432 Z" />

    <!-- Rubber Toe Cap (Rounded 3D dome matching girl_a_body.png) -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M658 1456 C676 1460 688 1466 688 1474 C688 1478 678 1481 650 1479 L606 1475 L606 1466 Z" />
    <!-- Toe highlight -->
    <path fill="#fbf8fc" d="M660 1459 C674 1463 684 1468 684 1474 L652 1473 L610 1470 L612 1464 Z" />

    <!-- Thick Rubber Sole (continuous, max y = 1490, NO CLIPPING) -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M688 1474 C689 1480 682 1488 652 1490 L552 1487 C545 1484 544 1476 546 1471 L606 1475 C640 1478 674 1478 688 1474 Z" />
    <!-- Sole shadow contour -->
    <path fill="{SHOE_SOLE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="2" stroke-linejoin="round" d="M686 1480 C672 1483 642 1484 602 1482 L548 1478 L550 1483 C556 1486 585 1488 642 1488 C672 1488 684 1484 686 1480 Z" />
  </g>
</svg>"""

    # 23. torso_back (single solid purple back panel across dark t-shirt back and short sleeves, crew collar)
    layers["torso_back"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_torso_back">
    <!-- Neck skin base connection under collar -->
    <path fill="{SKIN_BASE}" stroke="none" d="M465 500 L465 522 Q500 538 535 522 L535 500 Z" />

    <!-- Dark under-shirt body back -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M412 518 L360 670 L366 885 L634 885 L640 670 L588 518 Z" />

    <!-- Crew-neck back collar band -->
    <path fill="#221622" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M455 515 Q500 536 545 515 L542 530 Q500 546 458 530 Z" />

    <!-- Solid Purple Vest Back (single solid back panel across dark shirt and short sleeves) -->
    <path fill="{VEST_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M408 522 L372 670 C366 730 364 800 366 860 L368 900 C375 940 435 956 500 956 C565 956 625 940 632 900 L634 860 C636 800 634 730 628 670 L592 522 Q500 536 408 522 Z" />
    <path fill="{VEST_BASE}" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M414 525 L378 670 C372 730 370 800 372 860 L374 895 C380 932 438 948 500 948 C562 948 620 932 626 895 L628 860 C630 800 628 730 622 670 L586 525 Q500 536 414 525 Z" />

    <!-- Center vertical vest back stitch -->
    <path fill="none" stroke="#7b3a82" stroke-width="3" stroke-linecap="round" d="M500 538 L500 946" />
  </g>
</svg>"""

    # 24. shoe_back_left (rear view of left sneaker: heel counter, purple pull tab, rubber sole)
    layers["shoe_back_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_back_left">
    <!-- Ankle joint cap tucks under jeans cuff at (400, 1380) -->
    <circle cx="400" cy="1380" r="34" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" />
    <!-- Heel counter (purple canvas rear cup) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M356 1395 L444 1395 L452 1450 L348 1450 Z" />
    <path fill="{SHOE_BASE}" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M362 1397 L438 1397 L446 1448 L354 1448 Z" />
    
    <!-- Vertical Purple Heel Pull Tab -->
    <path fill="{SHOE_BASE}" stroke="{STROKE_MAIN}" stroke-width="3.5" stroke-linecap="round" d="M394 1390 Q400 1378 406 1390" />
    <rect x="394" y="1388" width="12" height="60" rx="3" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="3" />
    <rect x="396" y="1390" width="8" height="56" rx="2" fill="{SHOE_BASE}" />
    
    <!-- White / Lilac Rubber Sole -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M345 1450 L455 1450 L455 1468 L345 1468 Z" />
    <rect x="345" y="1462" width="110" height="6" fill="{SHOE_SOLE_SHADOW}" />
  </g>
</svg>"""

    # 25. shoe_back_right (rear view of right sneaker: heel counter, purple pull tab, rubber sole)
    layers["shoe_back_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_back_right">
    <!-- Ankle joint cap tucks under jeans cuff at (600, 1380) -->
    <circle cx="600" cy="1380" r="34" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" />
    <!-- Heel counter (purple canvas rear cup) -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M556 1395 L644 1395 L652 1450 L548 1450 Z" />
    <path fill="{SHOE_BASE}" stroke="{STROKE_INNER}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M562 1397 L638 1397 L646 1448 L554 1448 Z" />
    
    <!-- Vertical Purple Heel Pull Tab -->
    <path fill="{SHOE_BASE}" stroke="{STROKE_MAIN}" stroke-width="3.5" stroke-linecap="round" d="M594 1390 Q600 1378 606 1390" />
    <rect x="594" y="1388" width="12" height="60" rx="3" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="3" />
    <rect x="596" y="1390" width="8" height="56" rx="2" fill="{SHOE_BASE}" />
    
    <!-- White / Lilac Rubber Sole -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_MAIN}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" d="M545 1450 L655 1450 L655 1468 L545 1468 Z" />
    <rect x="545" y="1462" width="110" height="6" fill="{SHOE_SOLE_SHADOW}" />
  </g>
</svg>"""

    # 26. leg_upper_back_left (left thigh back with rear pocket and seam)
    layers["leg_upper_back_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_back_left">
    <circle cx="435" cy="930" r="46" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M390 930 L370 1160 L465 1160 L485 930 Z" />
    <path fill="{PANTS_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M400 930 L380 1160 L460 1160 L480 930 Z" />
    <!-- Rear pocket left -->
    <polygon points="405,960 460,960 455,1015 432,1028 410,1015" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linejoin="round" />
    <path fill="none" stroke="#253549" stroke-width="2.5" d="M414 980 Q432 995 450 980" />
    <!-- Inseam -->
    <line x1="485" y1="930" x2="465" y2="1160" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linecap="round" />
    <!-- Knee hem -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" d="M365 1155 Q420 1168 470 1155" />
  </g>
</svg>"""

    # 27. leg_upper_back_right (right thigh back with rear pocket and seam)
    layers["leg_upper_back_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_leg_upper_back_right">
    <circle cx="565" cy="930" r="46" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M515 930 L535 1160 L630 1160 L610 930 Z" />
    <path fill="{PANTS_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M520 930 L540 1160 L620 1160 L600 930 Z" />
    <!-- Rear pocket right -->
    <polygon points="540,960 595,960 590,1015 568,1028 545,1015" fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linejoin="round" />
    <path fill="none" stroke="#253549" stroke-width="2.5" d="M550 980 Q568 995 586 980" />
    <!-- Inseam -->
    <line x1="515" y1="930" x2="535" y2="1160" stroke="{STROKE_MAIN}" stroke-width="4" stroke-linecap="round" />
    <!-- Knee hem -->
    <path fill="{PANTS_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" d="M530 1155 Q580 1168 635 1155" />
  </g>
</svg>"""

    return layers


def build_manifest_and_character_json(char_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Builds manifest.json and character.json metadata for character pack."""
    is_boy = char_id == "boy_b"
    name = "Boy B" if is_boy else "Girl A"
    default_slot = "right" if is_boy else "left"

    pivots = {
        "neck": [500, 500 if is_boy else 520],
        "head": [500, 500 if is_boy else 520],
        "shoulder_left": [415, 525],
        "shoulder_right": [585, 525],
        "elbow_left": [390, 660] if is_boy else [345, 705],
        "elbow_right": [610, 660] if is_boy else [655, 705],
        "hip_left": [435, 870 if is_boy else 930],
        "hip_right": [565, 870 if is_boy else 930],
        "knee_left": [425, 1100] if is_boy else [415, 1150],
        "knee_right": [575, 1100] if is_boy else [585, 1150],
        "ankle_left": [420, 1345] if is_boy else [400, 1380],
        "ankle_right": [580, 1345] if is_boy else [600, 1380],
    }

    manifest = {
        "id": char_id,
        "name": name,
        "kind": "vector",
        "type": "layered",
        "svg_file": "character.svg",
        "viewBox": "0 0 1000 1500",
        "default_eyes": "open",
        "default_mouth": "closed",
        "default_slot": default_slot,
        "scale": 1.0,
        "head_position": [500, 350],
        "pivots": pivots,
        "anchors": {
            "head": [500, 350],
            "neck": pivots["neck"],
            "mouth": [500, 410 if is_boy else 428],
            "eyes": [500, 336 if is_boy else 360],
            "ground": [500, 1540],
        },
        "safe_bounding_box": {
            "min_x": 180,
            "min_y": 40,
            "max_x": 820,
            "max_y": 1550,
        },
        "layers": [
            "head_back",
            "shoe_right",
            "shoe_back_right",
            "leg_lower_right",
            "leg_upper_right",
            "leg_upper_back_right",
            "arm_lower_right",
            "arm_upper_right",
            "shoe_left",
            "shoe_back_left",
            "leg_lower_left",
            "leg_upper_left",
            "leg_upper_back_left",
            "torso",
            "torso_back",
            "head_base",
            "arm_upper_left",
            "arm_lower_left",
            "eyes_open",
            "eyes_blink",
            "eyes_look_left",
            "eyes_look_right",
            "mouth_closed",
            "mouth_slightly_open",
            "mouth_wide_open",
            "mouth_round_o",
            "mouth_open_smile",
        ],
        "layer_paths": {
            lname: f"layers/{lname}.svg"
            for lname in [
                "head_back",
                "shoe_right",
                "shoe_back_right",
                "leg_lower_right",
                "leg_upper_right",
                "leg_upper_back_right",
                "arm_lower_right",
                "arm_upper_right",
                "shoe_left",
                "shoe_back_left",
                "leg_lower_left",
                "leg_upper_left",
                "leg_upper_back_left",
                "torso",
                "torso_back",
                "head_base",
                "arm_upper_left",
                "arm_lower_left",
                "eyes_open",
                "eyes_blink",
                "eyes_look_left",
                "eyes_look_right",
                "mouth_closed",
                "mouth_slightly_open",
                "mouth_wide_open",
                "mouth_round_o",
                "mouth_open_smile",
            ]
        },
        "layer_files": {
            lname: f"layers/{lname}.svg"
            for lname in [
                "head_back",
                "shoe_right",
                "shoe_back_right",
                "leg_lower_right",
                "leg_upper_right",
                "leg_upper_back_right",
                "arm_lower_right",
                "arm_upper_right",
                "shoe_left",
                "shoe_back_left",
                "leg_lower_left",
                "leg_upper_left",
                "leg_upper_back_left",
                "torso",
                "torso_back",
                "head_base",
                "arm_upper_left",
                "arm_lower_left",
                "eyes_open",
                "eyes_blink",
                "eyes_look_left",
                "eyes_look_right",
                "mouth_closed",
                "mouth_slightly_open",
                "mouth_wide_open",
                "mouth_round_o",
                "mouth_open_smile",
            ]
        },
        "z_order": {
            "head_back": 0,
            "shoe_right": 1,
            "shoe_back_right": 1,
            "leg_lower_right": 1,
            "leg_upper_right": 1,
            "leg_upper_back_right": 1,
            "arm_lower_right": 3,
            "arm_upper_right": 3,
            "shoe_left": 2,
            "shoe_back_left": 2,
            "leg_lower_left": 2,
            "leg_upper_left": 2,
            "leg_upper_back_left": 2,
            "torso": 4,
            "torso_back": 4,
            "head_base": 5,
            "arm_upper_left": 6,
            "arm_lower_left": 6,
            "eyes": 7,
            "mouth": 7,
        },
        "eye_states": ["open", "blink", "look_left", "look_right"],
        "mouth_states": ["closed", "slightly_open", "wide_open", "round_o", "open_smile"],
        "allowed_gestures": ["idle", "walk", "wave", "point", "explain"],
    }

    character_json = {
        "name": char_id,
        "slots": {
            "hair": None,
            "hat": None,
            "torso": "torso",
            "legs": "leg_upper_left",
            "shoes": "shoe_left",
            "hands": None,
        },
        "active_expression": "neutral",
        "active_hand_left": "open_palm",
        "active_hand_right": "open_palm",
        "parts": {
            "torso": {
                "name": "torso",
                "image": "layers/torso.svg",
                "pivot": pivots["hip_left"],
                "parent": None,
                "parent_joint": None,
                "slot": None,
                "z_index": 4,
                "base_rotation": 0.0,
                "joints": {
                    "neck": pivots["neck"],
                    "shoulder_left": pivots["shoulder_left"],
                    "shoulder_right": pivots["shoulder_right"],
                    "hip_left": pivots["hip_left"],
                    "hip_right": pivots["hip_right"],
                },
            },
            "arm_upper_left": {
                "name": "arm_upper_left",
                "image": "layers/arm_upper_left.svg",
                "pivot": pivots["shoulder_left"],
                "parent": "torso",
                "parent_joint": "shoulder_left",
                "slot": None,
                "z_index": 6,
                "base_rotation": 0.0,
                "joints": {
                    "elbow": pivots["elbow_left"],
                },
            },
            "arm_lower_left": {
                "name": "arm_lower_left",
                "image": "layers/arm_lower_left.svg",
                "pivot": pivots["elbow_left"],
                "parent": "arm_upper_left",
                "parent_joint": "elbow",
                "slot": None,
                "z_index": 6,
                "base_rotation": 0.0,
                "joints": {},
            },
            "arm_upper_right": {
                "name": "arm_upper_right",
                "image": "layers/arm_upper_right.svg",
                "pivot": pivots["shoulder_right"],
                "parent": "torso",
                "parent_joint": "shoulder_right",
                "slot": None,
                "z_index": 3,
                "base_rotation": 0.0,
                "joints": {
                    "elbow": pivots["elbow_right"],
                },
            },
            "arm_lower_right": {
                "name": "arm_lower_right",
                "image": "layers/arm_lower_right.svg",
                "pivot": pivots["elbow_right"],
                "parent": "arm_upper_right",
                "parent_joint": "elbow",
                "slot": None,
                "z_index": 3,
                "base_rotation": 0.0,
                "joints": {},
            },
            "leg_upper_left": {
                "name": "leg_upper_left",
                "image": "layers/leg_upper_left.svg",
                "pivot": pivots["hip_left"],
                "parent": "torso",
                "parent_joint": "hip_left",
                "slot": None,
                "z_index": 2,
                "base_rotation": 0.0,
                "joints": {
                    "knee": pivots["knee_left"],
                },
            },
            "leg_lower_left": {
                "name": "leg_lower_left",
                "image": "layers/leg_lower_left.svg",
                "pivot": pivots["knee_left"],
                "parent": "leg_upper_left",
                "parent_joint": "knee",
                "slot": None,
                "z_index": 2,
                "base_rotation": 0.0,
                "joints": {
                    "ankle": pivots["ankle_left"],
                },
            },
            "shoe_left": {
                "name": "shoe_left",
                "image": "layers/shoe_left.svg",
                "pivot": pivots["ankle_left"],
                "parent": "leg_lower_left",
                "parent_joint": "ankle",
                "slot": None,
                "z_index": 2,
                "base_rotation": 0.0,
                "joints": {},
            },
            "leg_upper_right": {
                "name": "leg_upper_right",
                "image": "layers/leg_upper_right.svg",
                "pivot": pivots["hip_right"],
                "parent": "torso",
                "parent_joint": "hip_right",
                "slot": None,
                "z_index": 1,
                "base_rotation": 0.0,
                "joints": {
                    "knee": pivots["knee_right"],
                },
            },
            "leg_lower_right": {
                "name": "leg_lower_right",
                "image": "layers/leg_lower_right.svg",
                "pivot": pivots["knee_right"],
                "parent": "leg_upper_right",
                "parent_joint": "knee",
                "slot": None,
                "z_index": 1,
                "base_rotation": 0.0,
                "joints": {
                    "ankle": pivots["ankle_right"],
                },
            },
            "shoe_right": {
                "name": "shoe_right",
                "image": "layers/shoe_right.svg",
                "pivot": pivots["ankle_right"],
                "parent": "leg_lower_right",
                "parent_joint": "ankle",
                "slot": None,
                "z_index": 1,
                "base_rotation": 0.0,
                "joints": {},
            },
            "head": {
                "name": "head",
                "image": "layers/head_base.svg",
                "pivot": pivots["head"],
                "parent": "torso",
                "parent_joint": "neck",
                "slot": None,
                "z_index": 5,
                "base_rotation": 0.0,
                "joints": {
                    "face": [500, 360],
                    "hair": [500, 60],
                },
            },
            "torso_back": {
                "name": "torso_back",
                "image": "layers/torso_back.svg",
                "pivot": pivots["hip_left"],
                "parent": None,
                "parent_joint": None,
                "slot": None,
                "z_index": 4,
                "base_rotation": 0.0,
                "joints": {
                    "neck": pivots["neck"],
                    "shoulder_left": pivots["shoulder_left"],
                    "shoulder_right": pivots["shoulder_right"],
                    "hip_left": pivots["hip_left"],
                    "hip_right": pivots["hip_right"],
                },
            },
            "leg_upper_back_left": {
                "name": "leg_upper_back_left",
                "image": "layers/leg_upper_back_left.svg",
                "pivot": pivots["hip_left"],
                "parent": "torso",
                "parent_joint": "hip_left",
                "slot": None,
                "z_index": 2,
                "base_rotation": 0.0,
                "joints": {
                    "knee": pivots["knee_left"],
                },
            },
            "shoe_back_left": {
                "name": "shoe_back_left",
                "image": "layers/shoe_back_left.svg",
                "pivot": pivots["ankle_left"],
                "parent": "leg_lower_left",
                "parent_joint": "ankle",
                "slot": None,
                "z_index": 2,
                "base_rotation": 0.0,
                "joints": {},
            },
            "leg_upper_back_right": {
                "name": "leg_upper_back_right",
                "image": "layers/leg_upper_back_right.svg",
                "pivot": pivots["hip_right"],
                "parent": "torso",
                "parent_joint": "hip_right",
                "slot": None,
                "z_index": 1,
                "base_rotation": 0.0,
                "joints": {
                    "knee": pivots["knee_right"],
                },
            },
            "shoe_back_right": {
                "name": "shoe_back_right",
                "image": "layers/shoe_back_right.svg",
                "pivot": pivots["ankle_right"],
                "parent": "leg_lower_right",
                "parent_joint": "ankle",
                "slot": None,
                "z_index": 1,
                "base_rotation": 0.0,
                "joints": {},
            },
        },
        "expressions": {
            "neutral": "layers/head_base.svg",
        },
    }

    return manifest, character_json


def extract_svg_inner(svg_str: str) -> str:
    """Extracts contents between <svg ...> and </svg>."""
    start = svg_str.find(">")
    end = svg_str.rfind("</svg>")
    if start != -1 and end != -1:
        return svg_str[start + 1:end].strip()
    return svg_str


def assemble_svg_pose(
    char_id: str,
    layers: Dict[str, str],
    angles: Dict[str, float] = None,
    eye_state: str = "open",
    mouth_state: str = "closed",
    is_back_view: bool = False,
    view_width: int = 1000,
    view_height: int = 1500,
) -> str:
    """Assembles layered SVG with FK rotation transforms for each body part."""
    angles = angles or {}
    manifest, _ = build_manifest_and_character_json(char_id)
    piv = manifest["pivots"]

    sh_l = piv["shoulder_left"]
    el_l = piv["elbow_left"]
    sh_r = piv["shoulder_right"]
    el_r = piv["elbow_right"]
    hip_l = piv["hip_left"]
    kn_l = piv["knee_left"]
    ak_l = piv["ankle_left"]
    hip_r = piv["hip_right"]
    kn_r = piv["knee_right"]
    ak_r = piv["ankle_right"]
    neck = piv["neck"]

    ang_sh_l = angles.get("arm_upper_left", 0.0)
    ang_el_l = angles.get("arm_lower_left", 0.0)
    ang_sh_r = angles.get("arm_upper_right", 0.0)
    ang_el_r = angles.get("arm_lower_right", 0.0)
    ang_hip_l = angles.get("leg_upper_left", 0.0)
    ang_kn_l = angles.get("leg_lower_left", 0.0)
    ang_ak_l = angles.get("shoe_left", 0.0)
    ang_hip_r = angles.get("leg_upper_right", 0.0)
    ang_kn_r = angles.get("leg_lower_right", 0.0)
    ang_ak_r = angles.get("shoe_right", 0.0)
    ang_neck = angles.get("head", 0.0)

    # In back view, head_base, eyes, and mouth are omitted, head_back is dominant
    inner_head_back = extract_svg_inner(layers["head_back"])
    inner_head_base = extract_svg_inner(layers["head_base"])
    inner_torso = extract_svg_inner(layers["torso"])
    inner_torso_back = extract_svg_inner(layers.get("torso_back", layers["torso"]))

    inner_ua_l = extract_svg_inner(layers["arm_upper_left"])
    inner_la_l = extract_svg_inner(layers["arm_lower_left"])
    inner_ua_r = extract_svg_inner(layers["arm_upper_right"])
    inner_la_r = extract_svg_inner(layers["arm_lower_right"])

    inner_ul_l = extract_svg_inner(layers["leg_upper_left"])
    inner_ul_l_back = extract_svg_inner(layers.get("leg_upper_back_left", layers["leg_upper_left"]))
    inner_ll_l = extract_svg_inner(layers["leg_lower_left"])
    inner_sh_l = extract_svg_inner(layers["shoe_left"])
    inner_sh_l_back = extract_svg_inner(layers.get("shoe_back_left", layers["shoe_left"]))

    inner_ul_r = extract_svg_inner(layers["leg_upper_right"])
    inner_ul_r_back = extract_svg_inner(layers.get("leg_upper_back_right", layers["leg_upper_right"]))
    inner_ll_r = extract_svg_inner(layers["leg_lower_right"])
    inner_sh_r = extract_svg_inner(layers["shoe_right"])
    inner_sh_r_back = extract_svg_inner(layers.get("shoe_back_right", layers["shoe_right"]))

    eye_layer_key = f"eyes_{eye_state}"
    inner_eyes = extract_svg_inner(layers.get(eye_layer_key, layers["eyes_open"]))

    mouth_layer_key = f"mouth_{mouth_state}"
    inner_mouth = extract_svg_inner(layers.get(mouth_layer_key, layers["mouth_closed"]))

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_width} {view_height}" width="{view_width}" height="{view_height}">',
        f'  <rect width="{view_width}" height="{view_height}" fill="none" />',
        '  <g id="character_root">',
    ]

    if is_back_view:
        # z=0: legs & shoes (using dedicated rear layers: heel counters, tabs, back jeans pockets/seams)
        # Right leg FK hierarchy
        svg_parts.append(f'    <g id="fk_leg_r" transform="rotate({ang_hip_r}, {hip_r[0]}, {hip_r[1]})">')
        svg_parts.append(f'      {inner_ul_r_back}')
        svg_parts.append(f'      <g id="fk_leg_lower_r" transform="rotate({ang_kn_r}, {kn_r[0]}, {kn_r[1]})">')
        svg_parts.append(f'        {inner_ll_r}')
        svg_parts.append(f'        <g id="fk_shoe_r" transform="rotate({ang_ak_r}, {ak_r[0]}, {ak_r[1]})">')
        svg_parts.append(f'          {inner_sh_r_back}')
        svg_parts.append('        </g>')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')
        # Left leg FK hierarchy
        svg_parts.append(f'    <g id="fk_leg_l" transform="rotate({ang_hip_l}, {hip_l[0]}, {hip_l[1]})">')
        svg_parts.append(f'      {inner_ul_l_back}')
        svg_parts.append(f'      <g id="fk_leg_lower_l" transform="rotate({ang_kn_l}, {kn_l[0]}, {kn_l[1]})">')
        svg_parts.append(f'        {inner_ll_l}')
        svg_parts.append(f'        <g id="fk_shoe_l" transform="rotate({ang_ak_l}, {ak_l[0]}, {ak_l[1]})">')
        svg_parts.append(f'          {inner_sh_l_back}')
        svg_parts.append('        </g>')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')
        # Arms behind torso in back view
        svg_parts.append(f'    <g id="fk_arm_r" transform="rotate({ang_sh_r}, {sh_r[0]}, {sh_r[1]})">')
        svg_parts.append(f'      {inner_ua_r}')
        svg_parts.append(f'      <g id="fk_arm_lower_r" transform="rotate({ang_el_r}, {el_r[0]}, {el_r[1]})">')
        svg_parts.append(f'        {inner_la_r}')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')
        svg_parts.append(f'    <g id="fk_arm_l" transform="rotate({ang_sh_l}, {sh_l[0]}, {sh_l[1]})">')
        svg_parts.append(f'      {inner_ua_l}')
        svg_parts.append(f'      <g id="fk_arm_lower_l" transform="rotate({ang_el_l}, {el_l[0]}, {el_l[1]})">')
        svg_parts.append(f'        {inner_la_l}')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')
        # Dedicated Torso Back (draped hood / solid back vest)
        svg_parts.append(f'    {inner_torso_back}')
        # Head back covers the whole back of head
        svg_parts.append(f'    <g id="fk_head" transform="rotate({ang_neck}, {neck[0]}, {neck[1]})">')
        svg_parts.append(f'      {inner_head_back}')
        svg_parts.append('    </g>')
    else:
        # z=0: head_back
        svg_parts.append(f'    <g id="fk_head_back" transform="rotate({ang_neck}, {neck[0]}, {neck[1]})">')
        svg_parts.append(f'      {inner_head_back}')
        svg_parts.append('    </g>')

        # z=1: Right leg FK hierarchy
        svg_parts.append(f'    <g id="fk_leg_r" transform="rotate({ang_hip_r}, {hip_r[0]}, {hip_r[1]})">')
        svg_parts.append(f'      {inner_ul_r}')
        svg_parts.append(f'      <g id="fk_leg_lower_r" transform="rotate({ang_kn_r}, {kn_r[0]}, {kn_r[1]})">')
        svg_parts.append(f'        {inner_ll_r}')
        svg_parts.append(f'        <g id="fk_shoe_r" transform="rotate({ang_ak_r}, {ak_r[0]}, {ak_r[1]})">')
        svg_parts.append(f'          {inner_sh_r}')
        svg_parts.append('        </g>')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')

        # z=2: Left leg FK hierarchy
        svg_parts.append(f'    <g id="fk_leg_l" transform="rotate({ang_hip_l}, {hip_l[0]}, {hip_l[1]})">')
        svg_parts.append(f'      {inner_ul_l}')
        svg_parts.append(f'      <g id="fk_leg_lower_l" transform="rotate({ang_kn_l}, {kn_l[0]}, {kn_l[1]})">')
        svg_parts.append(f'        {inner_ll_l}')
        svg_parts.append(f'        <g id="fk_shoe_l" transform="rotate({ang_ak_l}, {ak_l[0]}, {ak_l[1]})">')
        svg_parts.append(f'          {inner_sh_l}')
        svg_parts.append('        </g>')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')

        # z=3: Right arm FK hierarchy (behind torso)
        svg_parts.append(f'    <g id="fk_arm_r" transform="rotate({ang_sh_r}, {sh_r[0]}, {sh_r[1]})">')
        svg_parts.append(f'      {inner_ua_r}')
        svg_parts.append(f'      <g id="fk_arm_lower_r" transform="rotate({ang_el_r}, {el_r[0]}, {el_r[1]})">')
        svg_parts.append(f'        {inner_la_r}')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')

        # z=4: Torso (covers hips & right arm shoulder)
        svg_parts.append(f'    {inner_torso}')

        # z=5: Head Base (neck tucks under torso collar)
        svg_parts.append(f'    <g id="fk_head_base" transform="rotate({ang_neck}, {neck[0]}, {neck[1]})">')
        svg_parts.append(f'      {inner_head_base}')
        # z=7: Eyes & Mouth inside head group so they rotate with head
        svg_parts.append(f'      {inner_eyes}')
        svg_parts.append(f'      {inner_mouth}')
        svg_parts.append('    </g>')

        # z=6: Left arm FK hierarchy (in front of torso)
        svg_parts.append(f'    <g id="fk_arm_l" transform="rotate({ang_sh_l}, {sh_l[0]}, {sh_l[1]})">')
        svg_parts.append(f'      {inner_ua_l}')
        svg_parts.append(f'      <g id="fk_arm_lower_l" transform="rotate({ang_el_l}, {el_l[0]}, {el_l[1]})">')
        svg_parts.append(f'        {inner_la_l}')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')

    svg_parts.append('  </g>')
    svg_parts.append('</svg>')

    return "\n".join(svg_parts)


def render_svg_to_image(page, svg_content: str, width: int = 1000, height: int = 1500) -> Image.Image:
    """Renders SVG content to a PIL RGBA Image via Playwright page."""
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; padding: 0; width: {width}px; height: {height}px; background: transparent; overflow: hidden; }}
  svg {{ display: block; width: {width}px; height: {height}px; }}
</style>
</head>
<body>
{svg_content}
</body>
</html>"""
    page.set_viewport_size({"width": width, "height": height})
    page.set_content(html)
    png_bytes = page.screenshot(omit_background=True)
    import io
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


def build_and_verify_character(char_id: str):
    """Executes full generation, schema validation, joint rotation verification, and preview rendering."""
    print(f"\n==================================================")
    print(f"  Building Vector Character Pack: {char_id}")
    print(f"==================================================")

    vector_dir = paths.CHARACTERS_2D_DIR / char_id / "vector"
    layers_dir = vector_dir / "layers"
    staging_dir = vector_dir / "staging"
    layers_dir.mkdir(parents=True, exist_ok=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Layers
    layers = get_boy_b_layers() if char_id == "boy_b" else get_girl_a_layers()

    print(f"1. Validating and writing {len(layers)} SVG layers...")
    for lname, svg_data in layers.items():
        # Security validation
        sec_errors = validate_svg_security(svg_data)
        if sec_errors:
            raise ValueError(f"Security validation failed on {char_id}/{lname}.svg: {sec_errors}")
        layer_file = layers_dir / f"{lname}.svg"
        layer_file.write_text(svg_data, encoding="utf-8")

    print(f"   Successfully wrote {len(layers)} SVG layers to {layers_dir.relative_to(paths.PROJECT_ROOT)}")

    # 2. Manifest and character.json
    print(f"2. Validating and writing manifest.json & character.json...")
    manifest, char_json = build_manifest_and_character_json(char_id)

    manifest_errors = validate_manifest_schema(manifest)
    if manifest_errors:
        raise ValueError(f"Manifest schema validation failed for {char_id}: {manifest_errors}")

    (vector_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (vector_dir / "character.json").write_text(json.dumps(char_json, indent=2), encoding="utf-8")
    print(f"   Manifest and character.json written successfully.")

    # 3. Playwright Rendering Engine
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # 4. Render 11 Required Preview Poses
        print(f"3. Rendering 11 verification poses...")
        preview_poses = [
            ("pose_01_front_standing", {}, "open", "closed", False),
            ("pose_02_mouth_slightly_open", {}, "open", "slightly_open", False),
            ("pose_03_mouth_wide_open", {}, "open", "wide_open", False),
            ("pose_04_mouth_round_o", {}, "open", "round_o", False),
            ("pose_05_mouth_open_smile", {}, "open", "open_smile", False),
            ("pose_06_eyes_blink", {}, "blink", "closed", False),
            ("pose_07_eyes_look_left", {}, "look_left", "closed", False),
            ("pose_08_eyes_look_right", {}, "look_right", "closed", False),
            ("pose_09_arm_raised", {"arm_upper_right": -115.0, "arm_lower_right": -35.0}, "open", "open_smile", False),
            (
                "pose_10_walking_swing",
                {
                    "leg_upper_left": 26.0,
                    "leg_lower_left": 15.0,
                    "leg_upper_right": -26.0,
                    "leg_lower_right": 25.0,
                    "arm_upper_left": -22.0,
                    "arm_lower_left": -10.0,
                    "arm_upper_right": 22.0,
                    "arm_lower_right": 10.0,
                },
                "open",
                "slightly_open",
                False,
            ),
            ("pose_11_back_view", {}, "open", "closed", True),
        ]

        rendered_pose_images = []
        for pname, ang, eye, mouth, is_back in preview_poses:
            pose_svg = assemble_svg_pose(
                char_id=char_id,
                layers=layers,
                angles=ang,
                eye_state=eye,
                mouth_state=mouth,
                is_back_view=is_back,
            )
            # Save SVG pose
            (staging_dir / f"{pname}.svg").write_text(pose_svg, encoding="utf-8")
            if pname == "pose_01_front_standing":
                (vector_dir / "character.svg").write_text(pose_svg, encoding="utf-8")
            # Render PNG at 1000x1500
            pose_img = render_svg_to_image(page, pose_svg, width=1000, height=1500)
            pose_img.save(staging_dir / f"{pname}.png")
            rendered_pose_images.append((pname, pose_img))
            print(f"   Rendered {pname}.png")

        # 5. Composite Preview Sheet (3 rows x 4 columns)
        print(f"4. Generating {char_id}_preview_sheet.png...")
        cell_w, cell_h = 300, 450
        sheet_cols, sheet_rows = 4, 3
        sheet_w = sheet_cols * cell_w
        sheet_h = sheet_rows * cell_h

        preview_sheet = Image.new("RGBA", (sheet_w, sheet_h), (250, 248, 245, 255))
        sdraw = ImageDraw.Draw(preview_sheet)

        for idx, (pname, pimg) in enumerate(rendered_pose_images):
            col = idx % sheet_cols
            row = idx // sheet_cols
            x = col * cell_w
            y = row * cell_h

            thumb = pimg.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            preview_sheet.alpha_composite(thumb, (x, y))

            label = pname.replace("pose_", "").replace("_", " ").title()
            sdraw.rectangle([x + 10, y + cell_h - 30, x + cell_w - 10, y + cell_h - 8], fill=(30, 41, 59, 220))
            sdraw.text((x + 16, y + cell_h - 26), label, fill=(248, 250, 252, 255))

        preview_sheet_p = staging_dir / f"{char_id}_preview_sheet.png"
        preview_sheet.save(preview_sheet_p)
        print(f"   Saved {preview_sheet_p.name}")

        # 6. Source Comparison Sheet (Side-by-side standing pose vs source image)
        print(f"5. Generating {char_id}_source_comparison.png...")
        src_path = paths.ASSETS_SOURCES_DIR / f"{char_id}_front_large.png"
        if not src_path.exists():
            src_path = paths.ASSETS_SOURCES_DIR / f"{char_id}_body.png"

        src_im = Image.open(src_path).convert("RGBA")
        standing_img = rendered_pose_images[0][1]

        # Crop standing vector bounding box
        bbox = standing_img.getbbox()
        if bbox:
            standing_cropped = standing_img.crop(bbox)
        else:
            standing_cropped = standing_img

        # Crop source bounding box
        import numpy as np
        src_arr = np.array(src_im)
        non_bg = (src_arr[:, :, 3] > 100) & ~((src_arr[:, :, 0] > 240) & (src_arr[:, :, 1] > 240) & (src_arr[:, :, 2] > 240))
        ys, xs = np.where(non_bg)
        if len(xs) > 0:
            src_cropped = src_im.crop((xs.min(), ys.min(), xs.max(), ys.max()))
        else:
            src_cropped = src_im

        comp_h = 900
        sw_scale = comp_h / max(1, src_cropped.height)
        vw_scale = comp_h / max(1, standing_cropped.height)

        src_thumb = src_cropped.resize((int(round(src_cropped.width * sw_scale)), comp_h), Image.Resampling.LANCZOS)
        vec_thumb = standing_cropped.resize((int(round(standing_cropped.width * vw_scale)), comp_h), Image.Resampling.LANCZOS)

        cmp_w = src_thumb.width + vec_thumb.width + 120
        cmp_sheet = Image.new("RGBA", (cmp_w, comp_h + 80), (255, 255, 255, 255))
        cdraw = ImageDraw.Draw(cmp_sheet)

        cmp_sheet.alpha_composite(src_thumb, (40, 60))
        cmp_sheet.alpha_composite(vec_thumb, (src_thumb.width + 80, 60))

        cdraw.text((40, 20), f"ORIGINAL SOURCE ({src_path.name})", fill=(30, 41, 59, 255))
        cdraw.text((src_thumb.width + 80, 20), f"CLEAN VECTOR PACK ({char_id})", fill=(30, 41, 59, 255))

        cmp_p = staging_dir / f"{char_id}_source_comparison.png"
        cmp_sheet.save(cmp_p)
        print(f"   Saved {cmp_p.name}")

        # 7. Joint Gap Rotation Tests (+/- 45 degrees check)
        print(f"6. Verifying gapless joint rotation (+/- 45 degrees on every joint)...")
        joints_to_test = [
            ("shoulder_left", "arm_upper_left"),
            ("elbow_left", "arm_lower_left"),
            ("shoulder_right", "arm_upper_right"),
            ("elbow_right", "arm_lower_right"),
            ("hip_left", "leg_upper_left"),
            ("knee_left", "leg_lower_left"),
            ("ankle_left", "shoe_left"),
            ("hip_right", "leg_upper_right"),
            ("knee_right", "leg_lower_right"),
            ("ankle_right", "shoe_right"),
        ]

        for jname, param in joints_to_test:
            for angle in [-45.0, 45.0]:
                test_svg = assemble_svg_pose(char_id=char_id, layers=layers, angles={param: angle})
                im = render_svg_to_image(page, test_svg, width=1000, height=1500)
                # Verify that around joint pivot, there are solid pixels (no disconnected gap)
                pivot = manifest["pivots"][jname]
                px, py = int(pivot[0]), int(pivot[1])
                # Check 20x20 area around pivot
                arr = np.array(im)
                region = arr[max(0, py - 10) : min(1500, py + 10), max(0, px - 10) : min(1000, px + 10), 3]
                solid_count = np.sum(region > 200)
                assert solid_count > 100, f"Discontinuity/gap detected at {char_id} joint {jname} at {angle} deg! Solid pixels: {solid_count}"
        print(f"   All 10 joints passed +/-45 deg gapless rotation verification!")

        # 8. Resolution Multiplier Test (1x, 2x, 4x)
        print(f"7. Rendering multi-resolution sharpness verification (1x, 2x, 4x)...")
        standing_svg = assemble_svg_pose(char_id=char_id, layers=layers)
        for scale, label in [(0.5, "1x"), (1.0, "2x"), (2.0, "4x")]:
            w = int(1000 * scale)
            h = int(1500 * scale)
            scaled_img = render_svg_to_image(page, standing_svg, width=w, height=h)
            out_p = staging_dir / f"{char_id}_standing_{label}.png"
            scaled_img.save(out_p)
            print(f"   Rendered {out_p.name} at {w}x{h}")

        browser.close()

    print(f"Completed character pack build for {char_id} successfully!\n")


if __name__ == "__main__":
    for cid in ["boy_b", "girl_a"]:
        build_and_verify_character(cid)
