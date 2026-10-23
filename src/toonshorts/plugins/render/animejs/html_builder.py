"""
Purpose: Template assembly and HTML document generation for whiteboard scenes.
Inputs: Scene metadata, character SVG rigs, timing cues, annotations, and stage visuals.
Outputs: Self-contained HTML5 string embedding local script engines and CSS.
Depends on: core.camera, core.config, core.models, html, json, pathlib, plugins.render.animejs.cast, plugins.render.animejs.gestures, plugins.render.animejs.layout, plugins.render.animejs.visual_renderer, typing
Used by: plugins.render.animejs, plugins.render.animejs.capture, plugins.render.animejs.plugin
Config keys: ANIME_JS_PATH, ENABLE_PARALLAX_BACKGROUND, ENABLE_PURPOSEFUL_CAMERA, ROUGH_JS_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py, tests/unit/test_word_annotations_security.py
"""

import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from toonshorts.core import config
from toonshorts.core.camera import (
    format_camera_timeline,
    load_camera_config_for_style,
    plan_scene_camera_shots,
    save_camera_timelines,
)
from toonshorts.core.models import Scene
from toonshorts.plugins.render.animejs.cast import build_characters_data
from toonshorts.plugins.render.animejs.gestures import sanitize_gesture
from toonshorts.plugins.render.animejs.layout import (
    build_parallax_background_layers,
    generate_scene_decorations,
)
from toonshorts.plugins.render.animejs.visual_renderer import (
    build_stage_elements,
    resolve_visual_timings,
)

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
    layout: str = "cards",
    visuals: Optional[List[Any]] = None,
    word_timings: Optional[List[Any]] = None,
    theme: str = "whiteboard",
    rough_seed: int = 1000,
    fast: bool = False,
    camera_config: Optional[Dict[str, Any]] = None,
    camera_shots: Optional[List[Dict[str, Any]]] = None,
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

    # Determine layout mode content (cards vs stage)
    stage_visuals_json = "[]"
    extra_stage_css = ""
    if layout == "stage" and visuals:
        resolved_vis = resolve_visual_timings(visuals, word_timings or [], duration_sec, scene_number)
        stage_markup, stage_css, stage_descriptors = build_stage_elements(resolved_vis, scene_number)
        board_content = stage_markup
        stage_visuals_json = json.dumps(stage_descriptors)
        extra_stage_css = stage_css
    else:
        board_content = f'    <div class="word-list">\n{cards_markup}\n    </div>'

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
    if extra_stage_css:
        characters_dynamic_css = characters_dynamic_css + "\n" + extra_stage_css

    timeline_chain = "\n".join(timeline_steps)
    mouth_cues_json = json.dumps(mouth_cues or [])
    shelf_decor_html, desk_props_html = generate_scene_decorations(scene_number, theme=theme)

    enable_parallax_bg = getattr(config, "ENABLE_PARALLAX_BACKGROUND", True)
    if enable_parallax_bg:
        bg_layers = build_parallax_background_layers(theme=theme, style_profile=None)
        bg_far_content = bg_layers.get("far", "")
        bg_mid_content = bg_layers.get("mid", "")
        bg_near_content = bg_layers.get("near", "")
    else:
        bg_far_content = ""
        bg_mid_content = ""
        bg_near_content = ""

    # Multiplane Camera Motion & Depth Configuration from central config
    camera_parallax_json = json.dumps(getattr(config, "CAMERA_PARALLAX_FACTORS", {
        "foreground": 2.0, "subject": 1.0, "board": 0.5, "deep_bg": 0.12
    }))
    camera_presets_json = json.dumps(getattr(config, "CAMERA_PRESETS", {
        "wide": {"x": 0.0, "y": 0.0, "zoom": 1.0, "focus": "subject"},
        "boy_close": {"x": 130.0, "y": -45.0, "zoom": 1.18, "focus": "subject"},
        "girl_close": {"x": -130.0, "y": -45.0, "zoom": 1.18, "focus": "subject"},
        "board_close": {"x": 0.0, "y": 90.0, "zoom": 1.25, "focus": "board"},
    }))
    enable_purposeful = getattr(config, "ENABLE_PURPOSEFUL_CAMERA", True)
    resolved_cam_cfg = camera_config or load_camera_config_for_style(theme)

    if resolved_cam_cfg and enable_purposeful:
        if camera_shots is not None:
            resolved_shots = camera_shots
        else:
            resolved_shots = plan_scene_camera_shots(
                duration_sec=duration_sec,
                word_timings=word_timings,
                visuals=visuals,
                speaker_id=speaker_slot_id,
                camera_config=resolved_cam_cfg,
                speaker_slot="right" if speaker_slot_id == "character-rig-right" else "left",
                scene_number=scene_number,
            )
        timeline_txt = format_camera_timeline(resolved_shots, duration_sec, scene_number=scene_number)
        save_camera_timelines({scene_number: timeline_txt})
        camera_shot_list_json = json.dumps(resolved_shots)
        camera_config_json = json.dumps(resolved_cam_cfg)
    else:
        camera_shot_list_json = "[]"
        camera_config_json = json.dumps({
            "transition_sec": getattr(config, "CAMERA_TRANSITION_SEC", 0.80),
            "drift_rot_max": getattr(config, "CAMERA_DRIFT_ROT_MAX", 0.35),
            "punch_in_zoom": getattr(config, "CAMERA_PUNCH_IN_ZOOM", 1.16),
            "punch_in_shake": getattr(config, "CAMERA_PUNCH_IN_SHAKE_PX", 1.5),
            "rack_focus": getattr(config, "CAMERA_RACK_FOCUS_BLUR", {
                "sharp": 0.0, "near_defocus": 2.2, "far_defocus": 3.8, "transition_frames": 10
            }),
        })
    raw_wts = []
    if word_timings:
        for wt in word_timings:
            w_str = getattr(wt, "word", None) or (wt.get("word") if isinstance(wt, dict) else "")
            s_t = getattr(wt, "start_time", None) if hasattr(wt, "start_time") else (wt.get("start_time", wt.get("start", 0.0)) if isinstance(wt, dict) else 0.0)
            e_t = getattr(wt, "end_time", None) if hasattr(wt, "end_time") else (wt.get("end_time", wt.get("end", s_t + 0.3)) if isinstance(wt, dict) else s_t + 0.3)
            raw_wts.append({
                "word": str(w_str),
                "start_ms": int(float(s_t) * 1000),
                "end_ms": int(float(e_t) * 1000),
            })
    word_timings_json = json.dumps(raw_wts)

    panel_backdrop_style = ""
    if theme == "night_studio":
        # Check code_editor_monitor.png backdrop inside board panel
        backdrop_path = config.PROJECT_ROOT / "assets" / "stitch_tests" / "code_editor_monitor.png"
        if backdrop_path.is_file():
            import base64
            b64_img = base64.b64encode(backdrop_path.read_bytes()).decode("utf-8")
            panel_backdrop_style = f"background-image: url('data:image/png;base64,{b64_img}');"

    # Load templates from disk
    template_html = (TEMPLATES_DIR / "whiteboard.html").read_text(encoding="utf-8")
    style_css = (TEMPLATES_DIR / "style.css").read_text(encoding="utf-8")

    # Load modular template scripts in fixed order from disk
    module_definitions = [
        ("rough_draw.js", "{{ROUGH_DRAW_JS}}"),
        ("stage_visuals.js", "{{STAGE_VISUALS_JS}}"),
        ("camera_engine.js", "{{CAMERA_ENGINE_JS}}"),
        ("gestures_fk.js", "{{GESTURES_FK_JS}}"),
        ("main.js", "{{MAIN_JS}}"),
    ]
    loaded_scripts = []
    for mod_filename, _ in module_definitions:
        mod_path = TEMPLATES_DIR / mod_filename
        if not mod_path.is_file():
            raise FileNotFoundError(f"Required template module '{mod_filename}' not found at {mod_path}")
        loaded_scripts.append(mod_path.read_text(encoding="utf-8"))

    # Format CSS
    formatted_css = style_css.replace("{{WIDTH}}", str(width)).replace("{{HEIGHT}}", str(height))

    # Replace placeholders in HTML template
    result = template_html
    result = result.replace("{{THEME_NAME}}", theme)
    result = result.replace("{{PANEL_BACKDROP_STYLE}}", panel_backdrop_style)
    result = result.replace("{{WIDTH}}", str(width))
    result = result.replace("{{HEIGHT}}", str(height))
    result = result.replace("{{TITLE}}", safe_title)
    result = result.replace("{{STYLE_CSS}}", formatted_css)
    result = result.replace("{{DYNAMIC_CSS}}", characters_dynamic_css)
    result = result.replace("{{ANIME_JS}}", anime_js)
    result = result.replace("{{ROUGH_JS}}", rough_js)
    result = result.replace("{{SHELF_DECOR}}", shelf_decor_html)
    result = result.replace("{{BG_FAR_CONTENT}}", bg_far_content)
    result = result.replace("{{BG_MID_CONTENT}}", bg_mid_content)
    result = result.replace("{{BG_NEAR_CONTENT}}", bg_near_content)
    result = result.replace("{{BOARD_CONTENT}}", board_content)
    result = result.replace("{{CARDS_MARKUP}}", cards_markup)
    result = result.replace("{{CHARACTERS_HTML}}", characters_html)
    result = result.replace("{{DESK_PROPS}}", desk_props_html)
    result = result.replace("{{FPS}}", str(fps))
    result = result.replace("{{MOUTH_CUES_JSON}}", mouth_cues_json)
    result = result.replace("{{CARD_TIMING_JSON}}", card_timing_json)
    result = result.replace("{{ANNOTATIONS_JSON}}", annotations_json)
    result = result.replace("{{STAGE_VISUALS_JSON}}", stage_visuals_json)
    result = result.replace("{{GESTURE_TRIGGER_MS}}", str(gesture_trigger_ms))
    result = result.replace("{{SPEAKER_GESTURE}}", speaker_gesture)
    result = result.replace("{{SPEAKER_SLOT_ID}}", speaker_slot_id)
    result = result.replace("{{LISTENER_SLOT_ID}}", listener_slot_id)
    result = result.replace("{{CAMERA_PARALLAX_JSON}}", camera_parallax_json)
    result = result.replace("{{CAMERA_PRESETS_JSON}}", camera_presets_json)
    result = result.replace("{{CAMERA_CONFIG_JSON}}", camera_config_json)
    result = result.replace("{{CAMERA_SHOT_LIST_JSON}}", camera_shot_list_json)
    result = result.replace("{{ENABLE_PURPOSEFUL_CAMERA}}", "true" if enable_purposeful else "false")
    result = result.replace("{{WORD_TIMINGS_JSON}}", word_timings_json)
    result = result.replace("{{ROUGH_SEED}}", str(rough_seed))
    result = result.replace("{{IS_FAST}}", "true" if fast else "false")
    safe_text_payload = {
        "title": safe_title,
        "cards": [
            {"id": f"word-card-{i+1}", "text": str(w_info.get("text", ""))}
            for i, w_info in enumerate(words)
        ],
    }
    safe_text_json = (
        json.dumps(safe_text_payload)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    result = result.replace("{{SAFE_TEXT_JSON}}", safe_text_json)
    result = result.replace("{{TOTAL_DURATION_MS}}", str(total_duration_ms))
    result = result.replace("{{TIMELINE_CHAIN}}", timeline_chain)

    for (mod_filename, placeholder), mod_text in zip(module_definitions, loaded_scripts):
        result = result.replace(placeholder, mod_text)


    return result
