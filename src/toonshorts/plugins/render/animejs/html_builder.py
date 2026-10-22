"""
Purpose: Template assembly and HTML document generation for whiteboard scenes.
Inputs: Scene metadata, character SVG rigs, timing cues, and annotations.
Outputs: Self-contained HTML5 string embedding local script engines and CSS.
Depends on: core.config, core.models, html, json, pathlib, plugins.render.animejs.cast, plugins.render.animejs.gestures, plugins.render.animejs.layout, typing
Used by: plugins.render.animejs, plugins.render.animejs.capture, plugins.render.animejs.plugin
Config keys: ANIME_JS_PATH, ROUGH_JS_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py
"""

import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from toonshorts.core import config
from toonshorts.core.models import Scene
from toonshorts.plugins.render.animejs.cast import build_characters_data
from toonshorts.plugins.render.animejs.gestures import sanitize_gesture
from toonshorts.plugins.render.animejs.layout import generate_scene_decorations

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def generate_whiteboard_html(
    title: str,
    words: List[Dict[str, Any]],
    duration_sec: float,
    mouth_cues: Optional[List[bool]] = None,
    gesture: str = "idle",
    fps: int = config.VIDEO_FPS,
    width: int = config.VIDEO_WIDTH,
    height: int = config.VIDEO_HEIGHT,
    scene_number: int = 1,
    annotations: Optional[List[Dict[str, Any]]] = None,
    characters_data: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generates a high-contrast HTML5/SVG composition with Anime.js whiteboard animation,
    Rough.js progressive stroke-by-stroke drawing (underlines, circles around keywords,
    prominent inter-card arrows), 7-layer character head redesign, physically attached hands,
    and a 100% constant studio set. Loaded strictly from local bundled scripts (no CDNs).
    """
    anime_js_path = config.ANIME_JS_PATH
    if not anime_js_path.is_file():
        raise FileNotFoundError(f"Local Anime.js bundle not found at {anime_js_path}")

    rough_js_path = config.ROUGH_JS_PATH
    if not rough_js_path.is_file():
        raise FileNotFoundError(f"Local Rough.js bundle not found at {rough_js_path}")

    anime_js = anime_js_path.read_text(encoding="utf-8")
    rough_js = rough_js_path.read_text(encoding="utf-8")

    clean_gesture = sanitize_gesture(gesture)
    safe_title = html.escape(title)

    total_duration_ms = int(duration_sec * 1000)
    title_start_ms = 100
    title_duration_ms = 420

    # Build fallback annotations if not provided
    if annotations is None:
        annotations = [{
            "id": "rough-title-underline",
            "type": "underline",
            "start_ms": 100,
            "duration_ms": 380,
        }]
        for idx, w in enumerate(words):
            s_ms = int(w.get("start_ms", title_start_ms + title_duration_ms + idx * 580))
            annotations.append({
                "id": f"rough-circle-{idx+1}",
                "type": "circle",
                "card_index": idx,
                "start_ms": s_ms,
                "duration_ms": 420,
            })
            if idx < len(words) - 1:
                next_s = int(words[idx+1].get("start_ms", s_ms + 580))
                arr_ms = (s_ms + next_s) // 2
                annotations.append({
                    "id": f"rough-arrow-{idx+1}",
                    "type": "arrow",
                    "card_from": idx,
                    "card_to": idx + 1,
                    "start_ms": arr_ms,
                    "duration_ms": 400,
                })

    # Anime.js timeline for title and cards entry
    timeline_steps = [
        f"""    .add({{
      targets: '#wb-title',
      opacity: [0, 1],
      translateY: [-28, 0],
      duration: {title_duration_ms},
      easing: 'easeOutBack'
    }}, {title_start_ms})"""
    ]

    card_colors = [
        ("#2563eb", "#eff6ff"),  # Vibrant Royal Blue
        ("#059669", "#ecfdf5"),  # Emerald Green
        ("#d97706", "#fffbeb"),  # Warm Amber
        ("#7c3aed", "#f5f3ff"),  # Deep Violet
        ("#db2777", "#fdf2f8"),  # Rose Pink
    ]

    word_cards_html = []
    card_timing_info = []

    for i, w_info in enumerate(words):
        word_text = html.escape(str(w_info.get("text", f"Point {i+1}")))
        start_ms = int(w_info.get("start_ms", (title_start_ms + title_duration_ms + i * 580)))
        dur_ms = int(w_info.get("duration_ms", 420))
        border_col, bg_col = card_colors[i % len(card_colors)]

        card_id = f"word-card-{i+1}"
        card_timing_info.append({
            "id": card_id,
            "start_ms": start_ms,
            "end_ms": 0,
        })

        word_cards_html.append(
            f"""      <div class="word-card" id="{card_id}" style="border-left-color: {border_col}; background-color: {bg_col};">
        <span class="word-num" style="color: {border_col};">{i+1}.</span>
        <span class="word-text-wrapper"><span class="word-text">{word_text}</span></span>
      </div>"""
        )

        timeline_steps.append(
            f"""    .add({{
      targets: '#{card_id}',
      opacity: [0, 1],
      translateX: [-35, 0],
      duration: {dur_ms},
      easing: 'easeOutBack'
    }}, {start_ms})"""
        )

    for i in range(len(card_timing_info)):
        if i + 1 < len(card_timing_info):
            card_timing_info[i]["end_ms"] = card_timing_info[i + 1]["start_ms"]
        else:
            card_timing_info[i]["end_ms"] = total_duration_ms

    cards_markup = "\n".join(word_cards_html)
    card_timing_json = json.dumps(card_timing_info)

    # Clean annotations for JS serializing (remove non-JSON objects)
    serializable_annotations = []
    for a in annotations:
        serializable_annotations.append({
            "id": a["id"],
            "type": a.get("type", ""),
            "start_ms": int(a.get("start_ms", 0)),
            "duration_ms": int(a.get("duration_ms", 400)),
        })
    annotations_json = json.dumps(serializable_annotations)

    # Determine meaningful gesture trigger moment
    if clean_gesture == "wave":
        gesture_trigger_ms = 350
    elif words and len(words) > 0:
        gesture_trigger_ms = int(words[0].get("start_ms", 600))
    else:
        gesture_trigger_ms = 600

    # Build character slots markup and styles
    if not characters_data:
        dummy_scene = Scene(
            scene_number=scene_number,
            speaker="Host",
            dialogue_line=safe_title,
            action="Whiteboard action",
            gesture=gesture if gesture != "idle" else None,
        )
        characters_data = build_characters_data(["presenter"], scene=dummy_scene, style_preset=None)
        if clean_gesture != "idle" and characters_data:
            characters_data[0]["gesture"] = clean_gesture

    speaker_slot_id = "character-rig"
    listener_slot_id = ""
    speaker_gesture = "idle"
    chars_html_list = []
    chars_css_rules = []

    for cdata in characters_data:
        slot = cdata["slot"]
        slot_id = "character-rig" if slot == "left" else "character-rig-right"
        if cdata["is_speaker"]:
            speaker_slot_id = slot_id
            speaker_gesture = cdata["gesture"]
        else:
            listener_slot_id = slot_id

        gest = cdata["gesture"]
        chars_css_rules.append(f"    #{slot_id} .arm-gesture {{ display: none; }}")
        chars_css_rules.append(f"    #{slot_id} #arm-gesture-{gest} {{ display: inline !important; }}")

        c_svg = cdata["svg"]
        c_slot_class = "char-slot-left" if slot == "left" else "char-slot-right"
        chars_html_list.append(f'  <div id="{slot_id}" class="{c_slot_class}">\n{c_svg}\n  </div>')

    characters_html = "\n".join(chars_html_list)
    characters_dynamic_css = "\n".join(chars_css_rules)

    timeline_chain = "\n".join(timeline_steps)
    mouth_cues_json = json.dumps(mouth_cues or [])
    shelf_decor_html, desk_props_html = generate_scene_decorations(scene_number)

    # Load templates from disk
    template_html = (TEMPLATES_DIR / "whiteboard.html").read_text(encoding="utf-8")
    style_css = (TEMPLATES_DIR / "style.css").read_text(encoding="utf-8")
    script_js = (TEMPLATES_DIR / "script.js").read_text(encoding="utf-8")

    # Format CSS
    formatted_css = style_css.replace("{{WIDTH}}", str(width)).replace("{{HEIGHT}}", str(height))

    # Replace placeholders in HTML template
    result = template_html
    result = result.replace("{{WIDTH}}", str(width))
    result = result.replace("{{HEIGHT}}", str(height))
    result = result.replace("{{TITLE}}", safe_title)
    result = result.replace("{{STYLE_CSS}}", formatted_css)
    result = result.replace("{{DYNAMIC_CSS}}", characters_dynamic_css)
    result = result.replace("{{ANIME_JS}}", anime_js)
    result = result.replace("{{ROUGH_JS}}", rough_js)
    result = result.replace("{{SHELF_DECOR}}", shelf_decor_html)
    result = result.replace("{{CARDS_MARKUP}}", cards_markup)
    result = result.replace("{{CHARACTERS_HTML}}", characters_html)
    result = result.replace("{{DESK_PROPS}}", desk_props_html)
    result = result.replace("{{FPS}}", str(fps))
    result = result.replace("{{MOUTH_CUES_JSON}}", mouth_cues_json)
    result = result.replace("{{CARD_TIMING_JSON}}", card_timing_json)
    result = result.replace("{{ANNOTATIONS_JSON}}", annotations_json)
    result = result.replace("{{GESTURE_TRIGGER_MS}}", str(gesture_trigger_ms))
    result = result.replace("{{SPEAKER_GESTURE}}", speaker_gesture)
    result = result.replace("{{SPEAKER_SLOT_ID}}", speaker_slot_id)
    result = result.replace("{{LISTENER_SLOT_ID}}", listener_slot_id)
    result = result.replace("{{TOTAL_DURATION_MS}}", str(total_duration_ms))
    result = result.replace("{{TIMELINE_CHAIN}}", timeline_chain)
    result = result.replace("{{SCRIPT_JS}}", script_js)

    return result
