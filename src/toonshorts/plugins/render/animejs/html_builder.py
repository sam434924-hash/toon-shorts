"""
Purpose: Template assembly and HTML document generation for whiteboard scenes.
Inputs: Scene metadata, character SVG rigs, timing cues, annotations, and stage visuals.
Outputs: Self-contained HTML5 string embedding local script engines and CSS.
Depends on: core.board_objects, core.camera, core.config, core.layout_planner, core.models, html, json, pathlib, plugins.render.animejs.cast, plugins.render.animejs.gestures, plugins.render.animejs.layout, plugins.render.animejs.visual_renderer, typing
Used by: plugins.render.animejs, plugins.render.animejs.capture, plugins.render.animejs.plugin
Config keys: ANIME_JS_PATH, ENABLE_BOARD_OBJECTS, ENABLE_PARALLAX_BACKGROUND, ENABLE_PURPOSEFUL_CAMERA, ENABLE_SPLIT_CAMERA_ZONES, ROUGH_JS_PATH, VIDEO_FPS, VIDEO_HEIGHT, VIDEO_WIDTH
Tests: tests/unit/test_animejs.py, tests/unit/test_board_objects.py, tests/unit/test_split_camera_zones.py, tests/unit/test_word_annotations_security.py
"""

import html
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from toonshorts.core import config
from toonshorts.core.board_objects import (
    convert_visuals_to_board_objects,
    resolve_board_objects_for_scene,
)
from toonshorts.core.camera import (
    format_camera_timeline,
    load_camera_config_for_style,
    plan_scene_camera_shots,
    plan_split_camera_shots,
    save_camera_timelines,
)
from toonshorts.core.models import Scene
from toonshorts.plugins.render.animejs.cast import build_characters_data
from toonshorts.plugins.render.animejs.gestures import sanitize_gesture
from toonshorts.plugins.render.animejs.layout import (
    build_parallax_background_layers,
    compute_character_camera_framing,
    generate_scene_decorations,
)
from toonshorts.plugins.render.animejs.visual_renderer import (
    build_stage_elements,
    resolve_visual_timings,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def build_board_slots_markup(
    layout: Any,
    style_preset: Optional[Dict[str, Any]] = None,
) -> str:
    """Builds HTML markup for board slots based on the active layout template."""
    from toonshorts.core.layout_planner import (
        DEFAULT_LAYOUT_TEMPLATES,
        canvas_to_board_relative_box,
        load_layout_templates,
    )

    templates = load_layout_templates(style_preset)
    tmpl_name = "hero"
    if isinstance(layout, dict):
        tmpl_name = layout.get("template", "hero")
    elif isinstance(layout, str) and layout in templates:
        tmpl_name = layout

    tmpl = templates.get(tmpl_name, DEFAULT_LAYOUT_TEMPLATES.get("hero", {}))
    padding = tmpl.get("padding", 16)
    slots = tmpl.get("slots", {})

    slot_divs = []
    generated_slot_ids = set()

    for s_name, s_box in slots.items():
        rel = canvas_to_board_relative_box(s_box)
        slot_id = f"board-slot-{s_name}"
        generated_slot_ids.add(slot_id)
        slot_divs.append(
            f'            <div class="board-slot slot-{s_name}" id="{slot_id}" data-slot="{s_name}" '
            f'style="position: absolute; left: {rel["left"]}px; top: {rel["top"]}px; '
            f'width: {rel["width"]}px; height: {rel["height"]}px; padding: {padding}px; '
            f'box-sizing: border-box; display: flex; align-items: center; justify-content: center; overflow: hidden;"></div>'
        )

    # Legacy fallback slots for backward compatibility
    legacy = [("top", "slot-top"), ("mid", "slot-mid"), ("bottom", "slot-bottom"), ("center", "slot-center")]
    for s_key, s_cls in legacy:
        s_id = f"board-slot-{s_key}"
        if s_id not in generated_slot_ids:
            slot_divs.append(f'            <div class="board-slot {s_cls}" id="{s_id}"></div>')

    return "\n".join(slot_divs)


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
    board_objects: Optional[List[Dict[str, Any]]] = None,
    style_profile: Optional[Dict[str, Any]] = None,
    bg_layer_images: Optional[Dict[str, str]] = None,
    enable_split_camera_zones: Optional[bool] = None,
    subtitle_text: Optional[str] = None,
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
    safe_subtitle = html.escape(subtitle_text) if subtitle_text is not None else safe_title

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
        ann_item = {
            "id": a["id"],
            "type": a.get("type", ""),
            "start_ms": int(a.get("start_ms", 0)),
            "duration_ms": int(a.get("duration_ms", 400)),
        }
        if "tied_word" in a and a["tied_word"]:
            ann_item["tied_word"] = str(a["tied_word"])
        if "card_index" in a:
            ann_item["card_index"] = a["card_index"]
        serializable_annotations.append(ann_item)
    annotations_json = json.dumps(serializable_annotations)

    # Determine layout mode content (cards vs stage)
    stage_visuals_json = "[]"
    extra_stage_css = ""
    is_stage_mode = (layout == "stage") or isinstance(layout, dict)
    if is_stage_mode and visuals:
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

    ALLOWED_SLOT_IDS = frozenset({"character-rig", "character-rig-right"})
    speaker_slot_id = "character-rig"
    listener_slot_id = ""
    speaker_gesture = "idle"
    chars_html_list = []
    chars_css_rules = []

    for cdata in characters_data:
        slot = cdata["slot"]
        raw_slot_id = "character-rig" if slot == "left" else "character-rig-right"
        slot_id = raw_slot_id if raw_slot_id in ALLOWED_SLOT_IDS else "character-rig"
        if cdata["is_speaker"]:
            speaker_slot_id = slot_id
            speaker_gesture = sanitize_gesture(cdata.get("gesture"))
        else:
            listener_slot_id = slot_id

        gest = sanitize_gesture(cdata.get("gesture"))
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
        if bg_layer_images and "far" in bg_layer_images:
            bg_far_content = f'<img src="{bg_layer_images["far"]}" class="bg-vector-svg" width="1680" height="2520" style="position: absolute; top:0; left:0; width:100%; height:100%; object-fit:fill;" />'
            bg_mid_content = f'<img src="{bg_layer_images["mid"]}" class="bg-vector-svg" width="1680" height="2520" style="position: absolute; top:0; left:0; width:100%; height:100%; object-fit:fill;" />'
            bg_near_content = f'<img src="{bg_layer_images["near"]}" class="bg-vector-svg" width="1680" height="2520" style="position: absolute; top:0; left:0; width:100%; height:100%; object-fit:fill;" />'
        else:
            bg_layers = build_parallax_background_layers(theme=theme, style_profile=None)
            bg_far_content = bg_layers.get("far", "")
            bg_mid_content = bg_layers.get("mid", "")
            bg_near_content = bg_layers.get("near", "")
    else:
        bg_far_content = ""
        bg_mid_content = ""
        bg_near_content = ""

    resolved_cam_cfg = camera_config or load_camera_config_for_style(theme)

    if enable_split_camera_zones is None:
        is_split_zones = getattr(config, "ENABLE_SPLIT_CAMERA_ZONES", False)
    else:
        is_split_zones = bool(enable_split_camera_zones)

    if is_split_zones:
        left_framing = compute_character_camera_framing(
            "left",
            gesture=speaker_gesture if speaker_slot_id == "character-rig" else "idle",
            requested_zoom=getattr(config, "CAMERA_ZOOM_SPEAKER", 1.18),
        )
        right_framing = compute_character_camera_framing(
            "right",
            gesture=speaker_gesture if speaker_slot_id == "character-rig-right" else "idle",
            requested_zoom=getattr(config, "CAMERA_ZOOM_SPEAKER", 1.18),
        )
        split_camera_framing = {
            "speaker_left": {"x": left_framing["pan_x"], "y": left_framing["pan_y"], "zoom": left_framing["zoom"]},
            "speaker_right": {"x": right_framing["pan_x"], "y": right_framing["pan_y"], "zoom": right_framing["zoom"]},
            "speaker_boy_close": {"x": left_framing["pan_x"], "y": left_framing["pan_y"], "zoom": left_framing["zoom"]},
            "speaker_girl_close": {"x": right_framing["pan_x"], "y": right_framing["pan_y"], "zoom": right_framing["zoom"]},
            "speaker_character-rig": {"x": left_framing["pan_x"], "y": left_framing["pan_y"], "zoom": left_framing["zoom"]},
            "speaker_character-rig-right": {"x": right_framing["pan_x"], "y": right_framing["pan_y"], "zoom": right_framing["zoom"]},
        }
        for cdata in (characters_data or []):
            cid = cdata.get("id")
            c_slot = cdata.get("slot")
            c_framing = right_framing if c_slot == "right" else left_framing
            if cid:
                split_camera_framing[f"speaker_{cid}"] = {
                    "x": c_framing["pan_x"], "y": c_framing["pan_y"], "zoom": c_framing["zoom"]
                }
        split_shots_dict = plan_split_camera_shots(
            duration_sec=duration_sec,
            word_timings=word_timings,
            visuals=visuals,
            speaker_id=speaker_slot_id,
            camera_config=resolved_cam_cfg,
            speaker_slot="right" if speaker_slot_id == "character-rig-right" else "left",
            scene_number=scene_number,
            gesture=speaker_gesture,
        )
        split_char_shots = split_shots_dict["character"]
        split_board_shots = split_shots_dict["board"]
    else:
        split_camera_framing = {}
        split_char_shots = []
        split_board_shots = []

    # Multiplane Camera Motion & Depth Configuration from central config
    camera_parallax_json = json.dumps(getattr(config, "CAMERA_PARALLAX_FACTORS", {
        "foreground": 2.0, "subject": 1.0, "board": 0.5, "deep_bg": 0.12
    }))
    camera_presets_json = json.dumps(getattr(config, "CAMERA_PRESETS", {
        "wide": {"x": 0.0, "y": 0.0, "zoom": 1.0, "focus": "subject"},
        "boy_close": {"x": -130.0, "y": -45.0, "zoom": 1.18, "focus": "subject"},
        "girl_close": {"x": 130.0, "y": -45.0, "zoom": 1.18, "focus": "subject"},
        "board_close": {"x": 0.0, "y": 90.0, "zoom": 1.25, "focus": "board"},
    }))
    enable_purposeful = getattr(config, "ENABLE_PURPOSEFUL_CAMERA", True)

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

    enable_board_objects = getattr(config, "ENABLE_BOARD_OBJECTS", True)
    if enable_board_objects:
        if board_objects:
            resolved_bo = resolve_board_objects_for_scene(
                board_objects,
                scene_number=scene_number,
                duration_sec=duration_sec,
                word_timings=word_timings,
                style_profile=style_profile,
            )
        elif visuals and (layout == "stage" or isinstance(layout, dict)):
            resolved_bo = convert_visuals_to_board_objects(
                visuals,
                scene_number=scene_number,
                duration_sec=duration_sec,
                word_timings=word_timings,
                style_profile=style_profile,
            )
        else:
            resolved_bo = []
    else:
        resolved_bo = []

    board_objects_json = json.dumps(resolved_bo)
    board_objects_payload_json = (
        json.dumps(resolved_bo)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    # Level 2 JavaScript Effects script generation
    level2_blocks = ["window.__level2Effects = window.__level2Effects || {};"]
    for bo in resolved_bo:
        if bo.get("type") == "custom" and (bo.get("data") or {}).get("level") == 2:
            bo_id = bo["id"]
            js_code = (bo.get("data") or {}).get("js_code", "")
            if js_code:
                level2_blocks.append(f"""(function() {{
  try {{
    var effect = ({js_code});
    if (typeof effect === 'function') {{
      window.__level2Effects[{json.dumps(bo_id)}] = effect;
    }}
  }} catch(e) {{
    console.error("Error defining Level 2 effect for " + {json.dumps(bo_id)}, e);
  }}
}})();""")
    level2_effects_script = "\n".join(level2_blocks)

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
    board_slots_html = build_board_slots_markup(layout, style_profile)

    if is_split_zones:
        main_content_layers = """    <!-- BOARD ZONE (Upper Area, Clipped) -->
    <div id="zone-board" class="zone-container zone-board">
      <div id="board-camera-content" class="zone-camera-content">
        <div id="layer-board" class="whiteboard-outer" data-depth-factor="0.5">
          <div class="panel-backdrop-dim" style="{{PANEL_BACKDROP_STYLE}}"></div>
          <svg id="rough-canvas" width="900" height="520"></svg>
          <div class="title-badge" id="wb-title">{{TITLE}}</div>
{{BOARD_CONTENT}}
          <!-- Board Objects Layer (Phase 4B-4) -->
          <div id="board-objects-container" class="board-objects-container">
{{BOARD_SLOTS_HTML}}
          </div>
          <div class="marker-tray">
            <div class="marker black"></div>
            <div class="marker blue"></div>
            <div class="marker red"></div>
            <div class="marker eraser"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- CHARACTER ZONE (Lower Area, Clipped) -->
    <div id="zone-character" class="zone-container zone-character">
      <div id="character-camera-content" class="zone-camera-content">
        <div id="layer-subject" class="character-slots-container" data-depth-factor="1.0">
{{CHARACTERS_HTML}}
        </div>
        <!-- Foreground Desk Props -->
        <div id="layer-foreground" class="desk-props" data-depth-factor="2.0">
          <svg viewBox="0 0 1080 130" width="1080" height="130">
{{DESK_PROPS}}
          </svg>
        </div>
        <!-- Desk Surface -->
        <div class="desk-container">
          <div class="desk-bevel"></div>
          <div class="desk-top"></div>
          <div class="desk-body"></div>
        </div>
      </div>
    </div>

    <!-- SUBTITLES (Separate Top Layer, Outside Camera Zones) -->
    <div id="zone-subtitles" class="zone-container zone-subtitles">
      <div id="subtitles-content" class="subtitles-content">
        <span id="subtitles-text">{{SUBTITLE_PREVIEW_TEXT}}</span>
      </div>
    </div>"""
    else:
        main_content_layers = """    <!-- Layer 3: Board (The board panel and its graphics) -->
    <div id="layer-board" class="depth-layer layer-board" data-depth-factor="0.5">
      <div class="whiteboard-outer">
        <div class="panel-backdrop-dim" style="{{PANEL_BACKDROP_STYLE}}"></div>
        <svg id="rough-canvas" width="900" height="980"></svg>
        <div class="title-badge" id="wb-title">{{TITLE}}</div>
{{BOARD_CONTENT}}
        <!-- Board Objects Layer (Phase 4B-4) -->
        <div id="board-objects-container" class="board-objects-container">
{{BOARD_SLOTS_HTML}}
        </div>
        <div class="marker-tray">
          <div class="marker black"></div>
          <div class="marker blue"></div>
          <div class="marker red"></div>
          <div class="marker eraser"></div>
        </div>
      </div>
    </div>

    <!-- Layer 2: Subject (The two characters) -->
    <div id="layer-subject" class="depth-layer layer-subject" data-depth-factor="1.0">
      <!-- Character Slots (Left and Right) -->
{{CHARACTERS_HTML}}
    </div>

    <!-- Layer 1: Foreground (Desk edge, lamp, mug, small card / laptop) -->
    <div id="layer-foreground" class="depth-layer layer-foreground" data-depth-factor="2.0">
      <!-- Foreground Desk Props (Constant Across All Scenes) -->
      <div class="desk-props">
        <svg viewBox="0 0 1080 130" width="1080" height="130">
{{DESK_PROPS}}
        </svg>
      </div>

      <!-- Desk Surface -->
      <div class="desk-container">
        <div class="desk-bevel"></div>
        <div class="desk-top"></div>
        <div class="desk-body"></div>
      </div>
    </div>"""

    main_content_layers = main_content_layers.replace("{{BOARD_SLOTS_HTML}}", board_slots_html)

    # Replace placeholders in HTML template
    result = template_html
    result = result.replace("{{MAIN_CONTENT_LAYERS}}", main_content_layers)
    result = result.replace("{{SPLIT_ZONES_CLASS}}", " split-zones-active" if is_split_zones else "")
    result = result.replace("{{ENABLE_SPLIT_CAMERA_ZONES}}", "true" if is_split_zones else "false")
    result = result.replace("{{SPLIT_CAMERA_FRAMING_JSON}}", json.dumps(split_camera_framing))
    result = result.replace("{{SPLIT_CHAR_SHOTS_JSON}}", json.dumps(split_char_shots))
    result = result.replace("{{SPLIT_BOARD_SHOTS_JSON}}", json.dumps(split_board_shots))
    result = result.replace("{{SUBTITLE_PREVIEW_TEXT}}", safe_subtitle)
    result = result.replace("{{THEME_NAME}}", theme)
    result = result.replace("{{PARALLAX_CLASS}}", " parallax-bg-enabled" if enable_parallax_bg else "")
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
    clean_speaker_slot = speaker_slot_id if speaker_slot_id in ALLOWED_SLOT_IDS else "character-rig"
    clean_listener_slot = listener_slot_id if listener_slot_id in ALLOWED_SLOT_IDS else "character-rig-right"
    clean_speaker_gesture = sanitize_gesture(speaker_gesture)

    result = result.replace("{{GESTURE_TRIGGER_MS_JSON}}", json.dumps(gesture_trigger_ms))
    result = result.replace("{{SPEAKER_GESTURE_JSON}}", json.dumps(clean_speaker_gesture))
    result = result.replace("{{SPEAKER_SLOT_ID_JSON}}", json.dumps(clean_speaker_slot))
    result = result.replace("{{LISTENER_SLOT_ID_JSON}}", json.dumps(clean_listener_slot))

    result = result.replace("{{GESTURE_TRIGGER_MS}}", str(gesture_trigger_ms))
    result = result.replace("{{SPEAKER_GESTURE}}", clean_speaker_gesture)
    result = result.replace("{{SPEAKER_SLOT_ID}}", clean_speaker_slot)
    result = result.replace("{{LISTENER_SLOT_ID}}", clean_listener_slot)
    result = result.replace("{{CAMERA_PARALLAX_JSON}}", camera_parallax_json)
    result = result.replace("{{CAMERA_PRESETS_JSON}}", camera_presets_json)
    result = result.replace("{{CAMERA_CONFIG_JSON}}", camera_config_json)
    result = result.replace("{{CAMERA_SHOT_LIST_JSON}}", camera_shot_list_json)
    result = result.replace("{{ENABLE_PURPOSEFUL_CAMERA}}", "true" if enable_purposeful else "false")
    result = result.replace("{{WORD_TIMINGS_JSON}}", word_timings_json)
    result = result.replace("{{ROUGH_SEED}}", str(rough_seed))
    result = result.replace("{{IS_FAST}}", "true" if fast else "false")
    result = result.replace("{{ENABLE_BOARD_OBJECTS}}", "true" if enable_board_objects else "false")
    result = result.replace("{{BOARD_OBJECTS_JSON}}", board_objects_json)
    result = result.replace("{{BOARD_OBJECTS_PAYLOAD_JSON}}", board_objects_payload_json).replace("{{LEVEL2_EFFECTS_SCRIPT}}", level2_effects_script)
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
