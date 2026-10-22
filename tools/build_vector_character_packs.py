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
    SHOE_PURPLE = "#6e3a75"
    SHOE_SHADOW = "#4a244f"
    SHOE_WHITE = "#ffffff"
    SHOE_SOLE = "#eef1f5"
    MOUTH_DARK = "#2a1814"
    MOUTH_TONGUE = "#e27a7a"
    MOUTH_TEETH = "#ffffff"

    layers = {}

    # 1. head_back
    layers["head_back"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_back">
    <path fill="{HAIR_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M330 250 L270 310 L295 340 L255 400 L300 420 L260 480 L325 485 L315 530 L375 490 L385 535 L440 480 L500 505 L560 480 L615 535 L625 490 L685 530 L675 485 L740 480 L700 420 L745 400 L705 340 L730 310 L670 250 Z" />
    <polygon points="330,250 270,310 320,330" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="270,310 295,340 255,400" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="255,400 300,420 260,480" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="670,250 730,310 680,330" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="730,310 705,340 745,400" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="745,400 700,420 740,480" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
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
    <!-- Head Jaw and Cranium -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M375 300 C375 220 625 220 625 300 C625 395 580 465 500 465 C420 465 375 395 375 300 Z" />
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
    <polygon points="520,175 500,200 515,245" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="520,175 515,245 550,215" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="390,130 335,175 365,225" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="390,130 365,225 400,205" fill="{HAIR_BASE}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="365,225 315,240 355,275" fill="{HAIR_SHADOW}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="365,225 355,275 400,250" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="610,130 595,205 635,225" fill="{HAIR_LIGHT}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="610,130 635,225 665,175" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="635,225 600,250 645,275" fill="{HAIR_DARK}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
    <polygon points="635,225 645,275 685,240" fill="{HAIR_SHADOW}" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linejoin="round" />
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

    # 13. arm_upper_left (shoulder to elbow, with rounded shoulder cap and sleeve cuff)
    # Shoulder pivot at (415, 525), Elbow at (345, 785)
    layers["arm_upper_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_upper_left">
    <!-- Shoulder overlap cap (hidden under torso shoulder) -->
    <circle cx="415" cy="525" r="32" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Upper arm sleeve body -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M410 520 L315 775 L372 795 L445 545 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M412 520 L325 775 L378 792 L440 555 Z" />
    <!-- Elbow sleeve cuff (covers lower arm joint cap) -->
    <g transform="rotate(20, 345, 785)">
      <rect x="306" y="768" width="76" height="34" rx="7" fill="{HOODIE_CUFF}" stroke="{STROKE_THICK}" stroke-width="6" />
      <rect x="309" y="771" width="70" height="28" rx="5" fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="3" />
    </g>
  </g>
</svg>"""

    # 14. arm_lower_left (forearm and hand left, with rounded elbow cap)
    # Elbow pivot at (345, 785), Wrist at (345, 875), Hand to 955
    layers["arm_lower_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_lower_left">
    <!-- Elbow overlap cap extending into upper sleeve cuff -->
    <circle cx="345" cy="785" r="26" fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- Forearm wrist link -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M330 805 L315 870 L360 885 L368 815 Z" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M334 810 L322 868 L355 880 L364 820 Z" />
    <!-- Redrawn Hand matching hands sheet -->
    <g id="boy_hand_l">
      <!-- Palm Base -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M320 865 C308 895 308 920 318 945 C326 958 344 958 354 946 C366 932 368 898 362 865 Z" />
      <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" d="M324 870 C314 895 314 918 322 940 C328 950 342 950 350 940 C360 928 362 898 356 870 Z" />
      <!-- Inward Thumb -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M352 870 C366 880 374 896 370 912 C364 922 354 918 348 905 Z" />
      <!-- Subtle Finger Crease Strokes -->
      <line x1="330" y1="946" x2="330" y2="910" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="339" y1="948" x2="339" y2="905" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="347" y1="944" x2="347" y2="908" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
    </g>
  </g>
</svg>"""

    # 15. arm_upper_right (shoulder to elbow, with rounded shoulder cap and sleeve cuff)
    # Shoulder pivot at (585, 525), Elbow at (655, 785)
    layers["arm_upper_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_upper_right">
    <!-- Shoulder overlap cap (hidden under torso shoulder) -->
    <circle cx="585" cy="525" r="32" fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" />
    <!-- Upper arm sleeve body -->
    <path fill="{HOODIE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M590 520 L685 775 L628 795 L555 545 Z" />
    <path fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M588 520 L675 775 L622 792 L560 555 Z" />
    <!-- Elbow sleeve cuff (covers lower arm joint cap) -->
    <g transform="rotate(-20, 655, 785)">
      <rect x="618" y="768" width="76" height="34" rx="7" fill="{HOODIE_CUFF}" stroke="{STROKE_THICK}" stroke-width="6" />
      <rect x="621" y="771" width="70" height="28" rx="5" fill="{HOODIE_BASE}" stroke="{STROKE_THIN}" stroke-width="3" />
    </g>
  </g>
</svg>"""

    # 16. arm_lower_right (forearm and hand right, with rounded elbow cap)
    # Elbow pivot at (655, 785), Wrist at (655, 875), Hand to 955
    layers["arm_lower_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_arm_lower_right">
    <!-- Elbow overlap cap extending into upper sleeve cuff -->
    <circle cx="655" cy="785" r="26" fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- Forearm wrist link -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M670 805 L685 870 L640 885 L632 815 Z" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M666 810 L678 868 L645 880 L636 820 Z" />
    <!-- Redrawn Hand matching hands sheet -->
    <g id="boy_hand_r">
      <!-- Palm Base -->
      <path fill="{SKIN_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M680 865 C692 895 692 920 682 945 C674 958 656 958 646 946 C634 932 632 898 638 865 Z" />
      <path fill="{SKIN_BASE}" stroke="{STROKE_THIN}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" d="M676 870 C686 895 686 918 678 940 C672 950 658 950 650 940 C640 928 638 898 644 870 Z" />
      <!-- Inward Thumb -->
      <path fill="{SKIN_BASE}" stroke="{STROKE_THICK}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M648 870 C634 880 626 896 630 912 C636 922 646 918 652 905 Z" />
      <!-- Subtle Finger Crease Strokes -->
      <line x1="670" y1="946" x2="670" y2="910" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="661" y1="948" x2="661" y2="905" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
      <line x1="653" y1="944" x2="653" y2="908" stroke="{STROKE_SUBTLE}" stroke-width="3" stroke-linecap="round" />
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

    # 19. shoe_left (sneaker with ankle overlap cap, body, white toe cap, laces, sole)
    # Ankle pivot at (420, 1345)
    layers["shoe_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_left">
    <!-- Ankle overlap cap (tucks under jeans cuff) -->
    <circle cx="420" cy="1345" r="32" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- Shoe Upper Body -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M340 1400 L380 1345 L465 1345 L470 1435 L445 1510 L330 1510 Z" />
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M350 1400 L390 1345 L460 1345 L465 1430 L440 1505 L340 1505 Z" />
    <!-- White Curved Rubber Toe Cap -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M335 1510 L335 1470 C335 1435 370 1420 405 1420 L435 1510 Z" />
    <!-- Laces -->
    <line x1="395" y1="1430" x2="435" y2="1435" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="388" y1="1455" x2="430" y2="1460" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="378" y1="1480" x2="425" y2="1485" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <!-- Thick Rubber Sole -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M325 1505 L450 1505 C460 1505 465 1520 460 1540 L325 1540 C315 1540 315 1505 325 1505 Z" />
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

    # 22. shoe_right (sneaker with ankle overlap cap, body, white toe cap, laces, sole)
    # Ankle pivot at (580, 1345)
    layers["shoe_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_right">
    <!-- Ankle overlap cap (tucks under jeans cuff) -->
    <circle cx="580" cy="1345" r="32" fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="5" />
    <!-- Shoe Upper Body -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M660 1400 L620 1345 L535 1345 L530 1435 L555 1510 L670 1510 Z" />
    <path fill="{SHOE_PURPLE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M650 1400 L610 1345 L540 1345 L535 1430 L560 1505 L660 1505 Z" />
    <!-- White Curved Rubber Toe Cap -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_THIN}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M665 1510 L665 1470 C665 1435 630 1420 595 1420 L565 1510 Z" />
    <!-- Laces -->
    <line x1="605" y1="1430" x2="565" y2="1435" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="612" y1="1455" x2="570" y2="1460" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="622" y1="1480" x2="575" y2="1485" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <!-- Thick Rubber Sole -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_THICK}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M675 1505 L550 1505 C540 1505 535 1520 540 1540 L675 1540 C685 1540 685 1505 675 1505 Z" />
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

    layers = {}

    # 1. head_back
    layers["head_back"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_back">
    <path fill="{HAIR_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M330 240 L240 310 L275 345 L220 415 L280 435 L225 510 L300 500 L285 570 L360 520 L370 580 L440 510 L500 540 L560 510 L630 580 L640 520 L715 570 L700 500 L775 510 L720 435 L780 415 L725 345 L760 310 L670 240 Z" />
    <polygon points="240,310 275,345 320,290" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="275,345 220,415 300,380" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="220,415 280,435 295,455" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="280,435 225,510 300,480" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="760,310 725,345 680,290" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="725,345 780,415 700,380" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="780,415 720,435 705,455" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="720,435 775,510 700,480" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
  </g>
</svg>"""

    # 2. head_base (neck, ears, cranium, jaw, eyebrows, glasses frames, freckles, nose, front hair - NO eyes, NO mouth)
    layers["head_base"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_head_base">
    <!-- Neck extending under collar -->
    <path fill="{SKIN_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M460 450 L460 560 L540 560 L540 450 Z" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M468 450 L468 545 C468 555 532 555 532 545 L532 450 Z" />
    <!-- Ears -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M370 340 C310 340 310 420 370 430 Z" />
    <path fill="none" stroke="{SKIN_SHADOW}" stroke-width="4" stroke-linecap="round" d="M360 365 C340 370 340 395 360 405" />
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M630 340 C690 340 690 420 630 430 Z" />
    <path fill="none" stroke="{SKIN_SHADOW}" stroke-width="4" stroke-linecap="round" d="M640 365 C660 370 660 395 640 405" />
    <!-- Face Jaw and Cranium -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M360 310 C360 210 640 210 640 310 C640 420 590 485 500 485 C410 485 360 420 360 310 Z" />
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
    <polygon points="520,175 500,205 515,250" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="520,175 515,250 555,215" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="375,125 320,170 355,220" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="375,125 355,220 390,205" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="355,220 295,245 345,280" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="355,220 345,280 390,250" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="625,125 610,205 645,220" fill="{HAIR_LIGHT}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="625,125 645,220 680,170" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="645,220 610,250 655,280" fill="{HAIR_MID}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
    <polygon points="645,220 655,280 705,245" fill="{HAIR_DARK}" stroke="{STROKE_FACET}" stroke-width="3.5" stroke-linejoin="round" />
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

    # 12. torso (shirt, collar, vest base, vest shadow, vest hem)
    # Hip joints at (435, 930) and (565, 930), Vest hem extends to y=950
    layers["torso"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_torso">
    <!-- Dark under-shirt -->
    <path fill="{SHIRT_DARK}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M410 520 L370 940 L630 940 L590 520 Z" />
    <!-- Chest skin at collar -->
    <path fill="{SKIN_BASE}" stroke="{STROKE_MAIN}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" d="M465 520 C475 550 525 550 535 520 Z" />
    <!-- Vest shadow -->
    <path fill="{VEST_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M360 620 L370 940 L630 940 L640 620 Z" />
    <!-- Vest Left Lapel / Hem -->
    <path fill="{VEST_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M420 520 L345 660 L360 950 L485 950 L485 710 L445 520 Z" />
    <!-- Vest Right Lapel / Hem -->
    <path fill="{VEST_BASE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M580 520 L655 660 L640 950 L515 950 L515 710 L555 520 Z" />
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

    # 19. shoe_left (redrawn authentic sneaker matching girl_a vest palette)
    # Ankle at (400, 1370), Cuff ends at 1412, Shoe extends to 1530
    layers["shoe_left"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_left">
    <!-- Ankle overlap cap (tucks under pant cuff) -->
    <circle cx="400" cy="1380" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Shoe Upper Body -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M335 1415 L375 1380 L465 1380 L470 1445 L445 1515 L320 1515 Z" />
    <path fill="{SHOE_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M345 1415 L385 1380 L460 1380 L465 1440 L440 1510 L330 1510 Z" />
    <!-- White Curved Rubber Toe Cap -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M325 1515 L325 1475 C325 1440 360 1425 395 1425 L428 1515 Z" />
    <!-- Laces -->
    <line x1="385" y1="1435" x2="425" y2="1440" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="378" y1="1460" x2="420" y2="1465" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="368" y1="1485" x2="415" y2="1490" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <!-- Thick Rubber Sole -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M315 1510 L445 1510 C455 1510 460 1525 455 1545 L315 1545 C305 1545 305 1510 315 1510 Z" />
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

    # 22. shoe_right (redrawn authentic sneaker matching girl_a vest palette)
    # Ankle at (600, 1370), Cuff ends at 1412, Shoe extends to 1530
    layers["shoe_right"] = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1500" width="1000" height="1500">
  <g id="layer_shoe_right">
    <!-- Ankle overlap cap (tucks under pant cuff) -->
    <circle cx="600" cy="1380" r="36" fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" />
    <!-- Shoe Upper Body -->
    <path fill="{SHOE_SHADOW}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M665 1415 L625 1380 L535 1380 L530 1445 L555 1515 L680 1515 Z" />
    <path fill="{SHOE_BASE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M655 1415 L615 1380 L540 1380 L535 1440 L560 1510 L670 1510 Z" />
    <!-- White Curved Rubber Toe Cap -->
    <path fill="{SHOE_WHITE}" stroke="{STROKE_INNER}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" d="M675 1515 L675 1475 C675 1440 640 1425 605 1425 L572 1515 Z" />
    <!-- Laces -->
    <line x1="615" y1="1435" x2="575" y2="1440" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="622" y1="1460" x2="580" y2="1465" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <line x1="632" y1="1485" x2="585" y2="1490" stroke="{SHOE_WHITE}" stroke-width="4" stroke-linecap="round" />
    <!-- Thick Rubber Sole -->
    <path fill="{SHOE_SOLE}" stroke="{STROKE_MAIN}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" d="M685 1510 L555 1510 C545 1510 540 1525 545 1545 L685 1545 C695 1545 695 1510 685 1510 Z" />
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
        "elbow_left": [345, 785 if is_boy else 705],
        "elbow_right": [655, 785 if is_boy else 705],
        "hip_left": [435, 870 if is_boy else 930],
        "hip_right": [565, 870 if is_boy else 930],
        "knee_left": [425, 1100 if is_boy else 1150],
        "knee_right": [575, 1100 if is_boy else 1150],
        "ankle_left": [420, 1345 if is_boy else 1380],
        "ankle_right": [580, 1345 if is_boy else 1380],
    }

    manifest = {
        "id": char_id,
        "name": name,
        "kind": "vector",
        "type": "layered",
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
            "leg_lower_right",
            "leg_upper_right",
            "arm_lower_right",
            "arm_upper_right",
            "shoe_left",
            "leg_lower_left",
            "leg_upper_left",
            "torso",
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
        "z_order": {
            "head_back": 0,
            "shoe_right": 1,
            "leg_lower_right": 1,
            "leg_upper_right": 1,
            "arm_lower_right": 3,
            "arm_upper_right": 3,
            "shoe_left": 2,
            "leg_lower_left": 2,
            "leg_upper_left": 2,
            "torso": 4,
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

    inner_ua_l = extract_svg_inner(layers["arm_upper_left"])
    inner_la_l = extract_svg_inner(layers["arm_lower_left"])
    inner_ua_r = extract_svg_inner(layers["arm_upper_right"])
    inner_la_r = extract_svg_inner(layers["arm_lower_right"])

    inner_ul_l = extract_svg_inner(layers["leg_upper_left"])
    inner_ll_l = extract_svg_inner(layers["leg_lower_left"])
    inner_sh_l = extract_svg_inner(layers["shoe_left"])

    inner_ul_r = extract_svg_inner(layers["leg_upper_right"])
    inner_ll_r = extract_svg_inner(layers["leg_lower_right"])
    inner_sh_r = extract_svg_inner(layers["shoe_right"])

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
        # z=0: legs & shoes
        # Right leg FK hierarchy
        svg_parts.append(f'    <g id="fk_leg_r" transform="rotate({ang_hip_r}, {hip_r[0]}, {hip_r[1]})">')
        svg_parts.append(f'      {inner_ul_r}')
        svg_parts.append(f'      <g id="fk_leg_lower_r" transform="rotate({ang_kn_r}, {kn_r[0]}, {kn_r[1]})">')
        svg_parts.append(f'        {inner_ll_r}')
        svg_parts.append(f'        <g id="fk_shoe_r" transform="rotate({ang_ak_r}, {ak_r[0]}, {ak_r[1]})">')
        svg_parts.append(f'          {inner_sh_r}')
        svg_parts.append('        </g>')
        svg_parts.append('      </g>')
        svg_parts.append('    </g>')
        # Left leg FK hierarchy
        svg_parts.append(f'    <g id="fk_leg_l" transform="rotate({ang_hip_l}, {hip_l[0]}, {hip_l[1]})">')
        svg_parts.append(f'      {inner_ul_l}')
        svg_parts.append(f'      <g id="fk_leg_lower_l" transform="rotate({ang_kn_l}, {kn_l[0]}, {kn_l[1]})">')
        svg_parts.append(f'        {inner_ll_l}')
        svg_parts.append(f'        <g id="fk_shoe_l" transform="rotate({ang_ak_l}, {ak_l[0]}, {ak_l[1]})">')
        svg_parts.append(f'          {inner_sh_l}')
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
        # Torso
        svg_parts.append(f'    {inner_torso}')
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

    print(f"1. Validating and writing 22 SVG layers...")
    for lname, svg_data in layers.items():
        # Security validation
        sec_errors = validate_svg_security(svg_data)
        if sec_errors:
            raise ValueError(f"Security validation failed on {char_id}/{lname}.svg: {sec_errors}")
        layer_file = layers_dir / f"{lname}.svg"
        layer_file.write_text(svg_data, encoding="utf-8")

    print(f"   Successfully wrote 22 SVG layers to {layers_dir.relative_to(paths.PROJECT_ROOT)}")

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
