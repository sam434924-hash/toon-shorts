"""
Purpose: Visual template rendering, Whisper trigger-word timing alignment, and Rough.js stage animations.
Inputs: Scene visuals list, Whisper word timings, scene duration, and board dimensions.
Outputs: HTML stage elements, CSS styling rules, and deterministic animation definitions.
Depends on: core.models, core.visuals, html, json, logging, re, typing
Used by: plugins.render.animejs, plugins.render.animejs.html_builder
Config keys: None
Tests: tests/unit/test_visual_templates.py, tests/unit/test_animejs.py
"""

import html
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from toonshorts.core.models import Visual, WordTiming
from toonshorts.core.visuals import (
    ALLOWED_PALETTES,
    get_visual_dimensions,
    sanitize_text,
)

logger = logging.getLogger("visual_renderer")


def resolve_visual_timings(
    visuals: List[Visual],
    word_timings: List[WordTiming],
    duration_sec: float,
    scene_number: int,
) -> List[Dict[str, Any]]:
    """
    Aligns each visual to the Whisper start time of its trigger_word.
    If the word is not found in word_timings, logs a clear warning and distributes evenly.
    """
    resolved = []
    total_duration_ms = int(duration_sec * 1000)
    norm_timings = []
    for wt in (word_timings or []):
        clean_w = re.sub(r"[^\w]", "", wt.word or "").lower()
        if clean_w:
            norm_timings.append((clean_w, wt.start_time, wt.end_time))

    matched_indices = set()

    for idx, vis in enumerate(visuals):
        target_raw = vis.trigger_word or ""
        target_clean = re.sub(r"[^\w]", "", target_raw).lower()

        found_time: Optional[float] = None
        for t_idx, (w, s_time, e_time) in enumerate(norm_timings):
            if t_idx not in matched_indices and (target_clean == w or target_clean in w or w in target_clean):
                found_time = s_time
                matched_indices.add(t_idx)
                break

        if found_time is not None and found_time >= 0.0:
            start_ms = int(found_time * 1000)
        else:
            # Not found: log a clear warning and place at even spacing
            logger.warning(
                "Scene %d: Trigger word '%s' not found in word timings; using even spacing.",
                scene_number,
                target_raw,
            )
            # Even spacing across scene
            step = total_duration_ms / (len(visuals) + 1)
            start_ms = int((idx + 1) * step)

        # Clamping start_ms safely within scene
        start_ms = max(100, min(start_ms, max(100, total_duration_ms - 800)))
        anim_duration_ms = min(1500, max(600, int((total_duration_ms - start_ms) * 0.75)))

        resolved.append({
            "index": idx,
            "type": vis.type,
            "trigger_word": target_raw,
            "params": vis.params or {},
            "start_ms": start_ms,
            "duration_ms": anim_duration_ms,
        })

    return resolved


def build_stage_elements(
    resolved_visuals: List[Dict[str, Any]],
    scene_number: int,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    Builds stage HTML elements, CSS styling, and client-side deterministic animation descriptors.
    """
    html_items = []
    css_rules = []
    js_descriptors = []

    for item in resolved_visuals:
        v_idx = item["index"]
        v_type = item["type"]
        params = item["params"]
        start_ms = item["start_ms"]
        dur_ms = item["duration_ms"]
        palette_name = params.get("color", "default")
        palette = ALLOWED_PALETTES.get(palette_name, ALLOWED_PALETTES["default"])

        w, h = get_visual_dimensions(v_type, params)
        dom_id = f"stage-vis-{scene_number}-{v_idx}"

        descriptor: Dict[str, Any] = {
            "dom_id": dom_id,
            "type": v_type,
            "start_ms": start_ms,
            "duration_ms": dur_ms,
            "palette": palette,
            "seed": 1000 * scene_number + 100 * v_idx + 42,
        }

        if v_type == "flow":
            nodes = params.get("nodes", ["A", "B"])
            descriptor["nodes"] = [sanitize_text(n) for n in nodes]
            node_htmls = []
            for n_idx, node_label in enumerate(nodes):
                safe_label = sanitize_text(node_label)
                node_dom_id = f"{dom_id}-node-{n_idx}"
                node_htmls.append(
                    f'<div class="flow-node-box" id="{node_dom_id}">'
                    f'  <div class="flow-node-badge" style="background:{palette["bg"]}; border-color:{palette["stroke"]};">'
                    f'    <span class="flow-node-text" style="color:{palette["text"]};">{safe_label}</span>'
                    f'  </div>'
                    f'</div>'
                )
                if n_idx < len(nodes) - 1:
                    arrow_dom_id = f"{dom_id}-arrow-{n_idx}"
                    node_htmls.append(
                        f'<div class="flow-arrow-box" id="{arrow_dom_id}">'
                        f'  <svg class="flow-arrow-svg" viewBox="0 0 60 24" width="60" height="24">'
                        f'    <path class="arrow-shaft" d="M 4 12 L 48 12" stroke="{palette["accent"]}" stroke-width="4" stroke-linecap="round" />'
                        f'    <path class="arrow-head" d="M 42 6 L 54 12 L 42 18" fill="none" stroke="{palette["accent"]}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />'
                        f'  </svg>'
                        f'</div>'
                    )

            html_items.append(
                f'<div class="stage-visual flow-visual" id="{dom_id}" style="width:{w}px; height:{h}px;">'
                f'  {"".join(node_htmls)}'
                f'</div>'
            )

        elif v_type == "request_response":
            c_label = sanitize_text(params.get("client_label", "Client"))
            s_label = sanitize_text(params.get("server_label", "Server"))
            req_label = sanitize_text(params.get("request_label", "Request"))
            res_label = sanitize_text(params.get("response_label", "Response"))

            descriptor["client_label"] = c_label
            descriptor["server_label"] = s_label
            descriptor["request_label"] = req_label
            descriptor["response_label"] = res_label

            html_items.append(
                f'<div class="stage-visual rr-visual" id="{dom_id}" style="width:{w}px; height:{h}px;">'
                f'  <div class="rr-box rr-client" style="border-color:{palette["stroke"]}; background:{palette["bg"]};">'
                f'    <div class="rr-box-icon" style="background:{palette["accent"]};"></div>'
                f'    <span class="rr-box-text" style="color:{palette["text"]};">{c_label}</span>'
                f'  </div>'
                f'  <div class="rr-lanes">'
                f'    <div class="rr-lane rr-lane-top">'
                f'      <span class="rr-lane-label" style="color:{palette["accent"]};">{req_label}</span>'
                f'      <svg class="rr-arrow-svg" viewBox="0 0 320 20" width="320" height="20">'
                f'        <path class="arrow-shaft" d="M 10 10 L 305 10" stroke="{palette["accent"]}" stroke-width="3" stroke-linecap="round" />'
                f'        <path class="arrow-head" d="M 298 5 L 310 10 L 298 15" fill="none" stroke="{palette["accent"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />'
                f'      </svg>'
                f'    </div>'
                f'    <div class="rr-packet" id="{dom_id}-packet" style="background:{palette["accent"]};">'
                f'      <div class="packet-core"></div>'
                f'    </div>'
                f'    <div class="rr-lane rr-lane-bottom">'
                f'      <span class="rr-lane-label" style="color:{palette["stroke"]};">{res_label}</span>'
                f'      <svg class="rr-arrow-svg" viewBox="0 0 320 20" width="320" height="20">'
                f'        <path class="arrow-shaft" d="M 310 10 L 15 10" stroke="{palette["stroke"]}" stroke-width="3" stroke-linecap="round" />'
                f'        <path class="arrow-head" d="M 22 5 L 10 10 L 22 15" fill="none" stroke="{palette["stroke"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />'
                f'      </svg>'
                f'    </div>'
                f'  </div>'
                f'  <div class="rr-box rr-server" style="border-color:{palette["stroke"]}; background:{palette["bg"]};">'
                f'    <div class="rr-box-icon" style="background:{palette["stroke"]};"></div>'
                f'    <span class="rr-box-text" style="color:{palette["text"]};">{s_label}</span>'
                f'  </div>'
                f'</div>'
            )

        elif v_type == "typed_code":
            lines = params.get("lines", [])
            lang = sanitize_text(params.get("language", "code"))
            full_text = "\n".join(lines)
            descriptor["full_text"] = full_text
            descriptor["lines"] = lines

            html_items.append(
                f'<div class="stage-visual code-visual" id="{dom_id}" style="width:{w}px; height:{h}px; border-color:{palette["stroke"]};">'
                f'  <div class="code-window-bar" style="background:{palette["stroke"]};">'
                f'    <span class="window-dot dot-red"></span>'
                f'    <span class="window-dot dot-yellow"></span>'
                f'    <span class="window-dot dot-green"></span>'
                f'    <span class="code-window-lang" style="color:#ffffff;">{lang}</span>'
                f'  </div>'
                f'  <pre class="code-pre"><code class="code-body" id="{dom_id}-code"></code><span class="code-cursor" id="{dom_id}-cursor">|</span></pre>'
                f'</div>'
            )

        elif v_type == "step_ladder":
            steps = params.get("steps", [])
            descriptor["steps"] = [sanitize_text(s) for s in steps]
            step_htmls = []
            for s_idx, s_text in enumerate(steps):
                safe_step = sanitize_text(s_text)
                step_dom_id = f"{dom_id}-step-{s_idx}"
                step_htmls.append(
                    f'<div class="ladder-step" id="{step_dom_id}" style="border-color:{palette["stroke"]}; background:{palette["bg"]};">'
                    f'  <span class="ladder-num-badge" style="background:{palette["accent"]}; color:#ffffff;">{s_idx + 1}</span>'
                    f'  <span class="ladder-step-text" style="color:{palette["text"]};">{safe_step}</span>'
                    f'</div>'
                )

            html_items.append(
                f'<div class="stage-visual ladder-visual" id="{dom_id}" style="width:{w}px; height:{h}px;">'
                f'  {"".join(step_htmls)}'
                f'</div>'
            )

        elif v_type == "check_cross":
            icon = params.get("icon", "check")
            lbl = sanitize_text(params.get("label", ""))
            descriptor["icon"] = icon
            descriptor["label"] = lbl

            is_check = (icon == "check")
            icon_col = palette["accent"] if is_check else (palette.get("stroke") or "#dc2626")
            icon_svg = (
                f'<svg class="cc-icon-svg" viewBox="0 0 44 44" width="44" height="44">'
                f'  <path class="cc-stroke-1" d="M 8 22 L 18 34" stroke="{icon_col}" stroke-width="6" stroke-linecap="round" fill="none" />'
                f'  <path class="cc-stroke-2" d="M 18 34 L 38 12" stroke="{icon_col}" stroke-width="6" stroke-linecap="round" fill="none" />'
                f'</svg>'
                if is_check
                else f'<svg class="cc-icon-svg" viewBox="0 0 44 44" width="44" height="44">'
                f'  <path class="cc-stroke-1" d="M 10 10 L 34 34" stroke="{icon_col}" stroke-width="6" stroke-linecap="round" fill="none" />'
                f'  <path class="cc-stroke-2" d="M 34 10 L 10 34" stroke="{icon_col}" stroke-width="6" stroke-linecap="round" fill="none" />'
                f'</svg>'
            )

            html_items.append(
                f'<div class="stage-visual cc-visual" id="{dom_id}" style="width:{w}px; height:{h}px; background:{palette["bg"]}; border-color:{palette["stroke"]};">'
                f'  <div class="cc-icon-badge" id="{dom_id}-icon">{icon_svg}</div>'
                f'  <span class="cc-label-text" style="color:{palette["text"]};">{lbl}</span>'
                f'</div>'
            )

        elif v_type == "counter":
            from_val = params.get("from_val", 0)
            to_val = params.get("to_val", 100)
            lbl = sanitize_text(params.get("label", ""))
            pfx = sanitize_text(params.get("prefix", ""))
            sfx = sanitize_text(params.get("suffix", ""))

            descriptor["from_val"] = from_val
            descriptor["to_val"] = to_val
            descriptor["label"] = lbl
            descriptor["prefix"] = pfx
            descriptor["suffix"] = sfx

            html_items.append(
                f'<div class="stage-visual counter-visual" id="{dom_id}" style="width:{w}px; height:{h}px; background:{palette["bg"]}; border-color:{palette["stroke"]};">'
                f'  <div class="counter-badge" id="{dom_id}-badge" style="background:{palette["accent"]}; color:#ffffff;">'
                f'    <span class="counter-value" id="{dom_id}-val">{pfx}{from_val}{sfx}</span>'
                f'  </div>'
                f'  <span class="counter-label-text" style="color:{palette["text"]};">{lbl}</span>'
                f'</div>'
            )

        elif v_type in ("kinetic_words", "draw_svg", "octopus_vector", "hearts_pop", "blue_blood_drop"):
            try:
                from toonshorts.plugins.graphics import get_graphics_plugin
                plugin_cls = get_graphics_plugin(v_type)
                render_kwargs = dict(params)
                render_kwargs["element_id"] = dom_id
                render_kwargs["start_ms"] = start_ms
                render_kwargs["duration_ms"] = dur_ms
                plugin_out = plugin_cls.render(**render_kwargs)
                html_items.append(plugin_out["html"])
                if plugin_out.get("css"):
                    css_rules.append(plugin_out["css"])
                descriptor.update(plugin_out.get("descriptor", {}))
            except Exception as e:
                logger.warning("Failed to render graphics plugin %s: %s", v_type, e)

        js_descriptors.append(descriptor)

    stage_markup = f'<div class="stage-container" id="stage-container">\n' + "\n".join(html_items) + "\n</div>"
    return stage_markup, "\n".join(css_rules), js_descriptors
