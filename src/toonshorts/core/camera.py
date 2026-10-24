"""
Purpose: Purposeful camera shot planning, easing, validation, and timeline formatting.
Inputs: Scene duration, word timings, visual cues, and camera configuration.
Outputs: Deterministic shot list transitions, formatted timelines, and validated configs.
Depends on: json, logging, math, pathlib, typing
Used by: core, core.pipeline, plugins.render.animejs.html_builder
Config keys: ENABLE_PURPOSEFUL_CAMERA, ENABLE_SPLIT_CAMERA_ZONES
Tests: tests/unit/test_camera_shot_planner.py, tests/unit/test_split_camera_zones.py
"""

import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("toonshorts.camera")

ALLOWED_EASING = ("easeInOutCubic", "easeInOutQuad", "smootherstep", "easeInOutSine")
ALLOWED_CONFIG_KEYS = {
    "mode",
    "continuous_drift",
    "transition_duration_ms",
    "easing",
    "lead_ms",
    "min_hold_ms",
    "target_move_interval_s",
}

DEFAULT_CAMERA_CONFIG: Dict[str, Any] = {
    "mode": "purposeful_only",
    "continuous_drift": False,
    "transition_duration_ms": 350,
    "easing": "easeInOutCubic",
    "lead_ms": 130,
    "min_hold_ms": 1000,
    "target_move_interval_s": [3, 6],
}


def ease_in_out_cubic(t: float) -> float:
    """Pure mathematical ease-in-out cubic interpolation without overshoot."""
    c = max(0.0, min(1.0, float(t)))
    if c < 0.5:
        return 4.0 * c * c * c
    return 1.0 - math.pow(-2.0 * c + 2.0, 3) / 2.0


def load_camera_config_for_style(theme: str, styles_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Loads and validates camera config from a style preset file if available."""
    if styles_dir is None:
        from toonshorts.core import config
        styles_dir = getattr(config, "STYLES_DIR", Path("src/toonshorts/styles"))

    style_file = styles_dir / f"{theme}.json"
    if style_file.is_file():
        try:
            data = json.loads(style_file.read_text(encoding="utf-8"))
            if "camera" in data:
                return validate_camera_config(data["camera"])
        except Exception as e:
            logger.warning("Could not parse camera config from %s: %s", style_file, e)
    return None


def validate_camera_config(cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates the camera configuration dictionary according to strict Phase 4B rules:
    - transition_duration_ms between 150 and 800
    - easing from a fixed allow-list
    - unknown keys rejected
    - continuous_drift only accepted as false for now
    """
    if cfg is None:
        return dict(DEFAULT_CAMERA_CONFIG)

    if not isinstance(cfg, dict):
        raise TypeError(f"Camera config must be a dict, got {type(cfg).__name__}")

    # Check for unknown keys
    unknown_keys = set(cfg.keys()) - ALLOWED_CONFIG_KEYS
    if unknown_keys:
        raise ValueError(
            f"Unknown camera config keys rejected: {sorted(unknown_keys)}. "
            f"Allowed keys: {sorted(ALLOWED_CONFIG_KEYS)}"
        )

    validated = dict(DEFAULT_CAMERA_CONFIG)
    validated.update(cfg)

    # 1. Mode validation
    mode = validated.get("mode")
    if mode != "purposeful_only":
        raise ValueError(f"Unsupported camera mode: '{mode}'. Only 'purposeful_only' is supported.")

    # 2. Continuous drift: only False accepted for now
    continuous_drift = validated.get("continuous_drift")
    if continuous_drift is not False:
        raise ValueError(
            f"continuous_drift must be False for purposeful_only camera, got {continuous_drift}"
        )

    # 3. Transition duration: between 150 and 800 ms
    trans_dur = validated.get("transition_duration_ms")
    if not isinstance(trans_dur, (int, float)) or trans_dur < 150 or trans_dur > 800:
        raise ValueError(
            f"transition_duration_ms must be a number between 150 and 800, got {trans_dur}"
        )
    validated["transition_duration_ms"] = int(trans_dur)

    # 4. Easing allow-list
    easing = validated.get("easing")
    if easing not in ALLOWED_EASING:
        raise ValueError(
            f"Camera easing '{easing}' rejected. Allowed easing functions: {ALLOWED_EASING}"
        )

    # 5. Lead ms & min hold ms
    lead_ms = validated.get("lead_ms")
    if not isinstance(lead_ms, (int, float)) or lead_ms < 0:
        raise ValueError(f"lead_ms must be a non-negative number, got {lead_ms}")
    validated["lead_ms"] = int(lead_ms)

    min_hold = validated.get("min_hold_ms")
    if not isinstance(min_hold, (int, float)) or min_hold < 0:
        raise ValueError(f"min_hold_ms must be a non-negative number, got {min_hold}")
    validated["min_hold_ms"] = int(min_hold)

    # 6. Target move interval
    interval = validated.get("target_move_interval_s")
    if (
        not isinstance(interval, (list, tuple))
        or len(interval) != 2
        or not all(isinstance(v, (int, float)) for v in interval)
        or interval[0] <= 0
        or interval[0] > interval[1]
    ):
        raise ValueError(
            f"target_move_interval_s must be a 2-element sequence [min_s, max_s] with 0 < min_s <= max_s, got {interval}"
        )
    validated["target_move_interval_s"] = [float(interval[0]), float(interval[1])]

    return validated


def plan_scene_camera_shots(
    duration_sec: float,
    word_timings: Optional[List[Any]] = None,
    visuals: Optional[List[Any]] = None,
    speaker_id: Optional[str] = None,
    camera_config: Optional[Dict[str, Any]] = None,
    speaker_slot: str = "left",
    scene_number: int = 1,
) -> List[Dict[str, Any]]:
    """
    Deterministic Camera Shot Planner (Pure Function of Time).
    Builds a deterministic shot list [{t_start, t_end, from_target, to_target}]
    with targets: wide, speaker_<id>, board_close, board_<visual_id>.

    Rules:
    - start a move lead_ms BEFORE the cue
    - hold the new framing at least min_hold_ms
    - skip a move if two cues are too close for the minimum hold
    - clamp to scene bounds
    - scenes with no cues stay on wide, locked
    - aim for a move every 3 to 6 seconds without breaking the hold rule
    """
    cfg = validate_camera_config(camera_config)
    total_duration_ms = max(0, int(round(duration_sec * 1000)))

    lead_ms = cfg["lead_ms"]
    min_hold_ms = cfg["min_hold_ms"]
    trans_dur_ms = cfg["transition_duration_ms"]
    min_interval_ms = int(cfg["target_move_interval_s"][0] * 1000)
    max_interval_ms = int(cfg["target_move_interval_s"][1] * 1000)

    # Format speaker target
    speaker_target = f"speaker_{speaker_id}" if speaker_id else (
        "speaker_right" if speaker_slot == "right" else "speaker_left"
    )

    # Gather raw cues: (cue_time_ms, target_name, cue_type)
    raw_cues: List[Tuple[int, str, str]] = []

    # 1. Speech cues
    norm_wts = []
    if word_timings:
        for wt in word_timings:
            s_time = getattr(wt, "start_time", None) if hasattr(wt, "start_time") else (
                wt.get("start_time", wt.get("start_ms", 0.0) / 1000.0 if "start_ms" in wt else 0.0)
                if isinstance(wt, dict) else 0.0
            )
            e_time = getattr(wt, "end_time", None) if hasattr(wt, "end_time") else (
                wt.get("end_time", wt.get("end_ms", 0.0) / 1000.0 if "end_ms" in wt else s_time + 0.3)
                if isinstance(wt, dict) else s_time + 0.3
            )
            norm_wts.append((int(float(s_time) * 1000), int(float(e_time) * 1000)))

    if norm_wts:
        speech_start_ms = norm_wts[0][0]
        raw_cues.append((speech_start_ms, speaker_target, "speech_start"))

    # 2. Visual cues
    if visuals:
        for idx, vis in enumerate(visuals):
            v_start = vis.get("start_ms") if isinstance(vis, dict) else getattr(vis, "start_ms", None)
            if v_start is None:
                v_start_sec = vis.get("start_time") if isinstance(vis, dict) else getattr(vis, "start_time", None)
                v_start = int(v_start_sec * 1000) if v_start_sec is not None else 0

            v_dur = vis.get("duration_ms") if isinstance(vis, dict) else getattr(vis, "duration_ms", 800)
            v_id = vis.get("dom_id") if isinstance(vis, dict) else getattr(vis, "dom_id", None)
            if not v_id:
                v_id = vis.get("id") if isinstance(vis, dict) else getattr(vis, "id", f"visual_{idx+1}")

            v_target = f"board_{v_id}" if v_id else "board_close"
            raw_cues.append((int(v_start), v_target, "visual_start"))

            # Visual return cue back to speaker/wide
            v_end = int(v_start + (v_dur or 800))
            raw_cues.append((v_end + 300, speaker_target, "visual_end"))

    # If no cues at all: scene stays wide, locked!
    if not raw_cues:
        return []

    # Sort cues chronologically
    raw_cues.sort(key=lambda x: x[0])

    shots: List[Dict[str, Any]] = []
    current_target = "wide"
    last_move_end_ms = 0

    for cue_time_ms, target, cue_type in raw_cues:
        # Avoid redundant move to the same framing
        if target == current_target:
            continue

        # Rule: start a move lead_ms BEFORE the cue
        desired_start_ms = max(0, cue_time_ms - lead_ms)

        # Rule: hold the new framing at least min_hold_ms
        # Rule: skip a move if two cues are too close for the minimum hold
        if shots and (desired_start_ms < last_move_end_ms + min_hold_ms):
            # Cues too close: skip this move to prevent jarring thrashing
            continue

        desired_end_ms = desired_start_ms + trans_dur_ms

        # Rule: clamp to scene bounds
        if desired_start_ms >= total_duration_ms:
            break
        if desired_end_ms > total_duration_ms:
            desired_end_ms = total_duration_ms
        if desired_end_ms <= desired_start_ms:
            continue

        # Pacing check: if a long hold occurs, we can optionally move to wide
        shots.append({
            "t_start": int(desired_start_ms),
            "t_end": int(desired_end_ms),
            "from_target": current_target,
            "to_target": target,
        })
        current_target = target
        last_move_end_ms = desired_end_ms

    # Aim for a move every 3 to 6 seconds without breaking the hold rule
    # If the camera remains locked on a close-up past max_interval_ms before the end,
    # and has satisfied min_hold_ms, return gently to wide.
    if shots:
        remaining_time_ms = total_duration_ms - last_move_end_ms
        if remaining_time_ms >= max_interval_ms and current_target != "wide":
            pacing_start_ms = last_move_end_ms + max_interval_ms - trans_dur_ms
            pacing_end_ms = pacing_start_ms + trans_dur_ms
            if (
                pacing_start_ms >= last_move_end_ms + min_hold_ms
                and pacing_end_ms <= total_duration_ms
            ):
                shots.append({
                    "t_start": int(pacing_start_ms),
                    "t_end": int(pacing_end_ms),
                    "from_target": current_target,
                    "to_target": "wide",
                })
                current_target = "wide"
                last_move_end_ms = pacing_end_ms

    return shots


def format_camera_timeline(
    shots: List[Dict[str, Any]],
    duration_sec: float,
    scene_number: int = 1,
) -> str:
    """
    Generates a readable, human-verifiable text timeline of the shots for a scene.
    Shows locked periods, easing durations, targets, and holds.
    """
    total_duration_ms = int(round(duration_sec * 1000))
    lines: List[str] = [
        f"=== Scene {scene_number} Camera Shot Timeline (Duration: {duration_sec:.3f}s / {total_duration_ms}ms) ==="
    ]

    if not shots:
        lines.append(f"  [ 0.000s - {duration_sec:6.3f}s] ({total_duration_ms}ms) LOCKED on 'wide' (Zero cues: camera fixed)")
        lines.append("  Summary: 0 camera moves | Mode: purposeful_only | Drift: OFF")
        return "\n".join(lines)

    cur_time = 0
    cur_framing = shots[0]["from_target"]

    for idx, shot in enumerate(shots):
        t_s = shot["t_start"]
        t_e = shot["t_end"]
        from_t = shot["from_target"]
        to_t = shot["to_target"]

        # Locked period before move
        if t_s > cur_time:
            hold_ms = t_s - cur_time
            lines.append(
                f"  [{cur_time/1000.0:6.3f}s - {t_s/1000.0:6.3f}s] ({hold_ms:4d}ms) LOCKED on '{cur_framing}'"
            )

        # Move transition
        move_dur = t_e - t_s
        lines.append(
            f"  [{t_s/1000.0:6.3f}s - {t_e/1000.0:6.3f}s] ({move_dur:4d}ms) MOVE: '{from_t}' -> '{to_t}' [easeInOutCubic]"
        )

        cur_time = t_e
        cur_framing = to_t

    # Final locked hold until scene end
    if cur_time < total_duration_ms:
        final_hold_ms = total_duration_ms - cur_time
        lines.append(
            f"  [{cur_time/1000.0:6.3f}s - {duration_sec:6.3f}s] ({final_hold_ms:4d}ms) LOCKED on '{cur_framing}'"
        )

    lines.append(
        f"  Summary: {len(shots)} moves | Mode: purposeful_only | Easing: easeInOutCubic | Drift: OFF"
    )
    return "\n".join(lines)


def save_camera_timelines(
    timelines: Dict[int, str],
    output_dir: Path = Path("baseline/phase4b"),
) -> Path:
    """
    Saves formatted text timelines per scene and a combined summary file to baseline/phase4b/.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    combined_lines = ["# Purposeful Camera Shot Timelines (Phase 4B)\n"]

    for scene_num in sorted(timelines.keys()):
        text = timelines[scene_num]
        combined_lines.append(text)
        combined_lines.append("\n" + ("-" * 70) + "\n")

        scene_file = output_dir / f"scene_{scene_num}_camera_timeline.txt"
        scene_file.write_text(text + "\n", encoding="utf-8")

    summary_file = output_dir / "camera_timelines.txt"
    summary_file.write_text("\n".join(combined_lines), encoding="utf-8")
    return summary_file



def plan_split_camera_shots(
    duration_sec: float,
    word_timings: Optional[List[Any]] = None,
    visuals: Optional[List[Any]] = None,
    speaker_id: Optional[str] = None,
    camera_config: Optional[Dict[str, Any]] = None,
    speaker_slot: str = "left",
    scene_number: int = 1,
    gesture: str = "idle",
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Plans independent camera shot lists for the two zones:
    - Character Camera: Zooms in on the active speaker at speech onset, holds for at least 1.2s, then eases out.
    - Board Camera: Zooms in only on purposeful cues (key words or stage visuals), holds for at least 1.2s, then eases out.
    Both cameras are completely independent: character moves do not affect the board, and board moves do not affect characters.
    """
    from toonshorts.core import config
    cfg = validate_camera_config(camera_config)
    total_duration_ms = max(0, int(round(duration_sec * 1000)))
    lead_ms = cfg["lead_ms"]
    min_hold_ms = max(int(getattr(config, "CAMERA_MIN_HOLD_SEC", 1.2) * 1000), cfg["min_hold_ms"])
    trans_dur_ms = cfg["transition_duration_ms"]

    speaker_target = f"speaker_{speaker_id}" if speaker_id else (
        "speaker_right" if speaker_slot == "right" else "speaker_left"
    )

    # 1. Speech timing for character camera
    char_shots: List[Dict[str, Any]] = []
    norm_wts = []
    if word_timings:
        for wt in word_timings:
            s_time = getattr(wt, "start_time", None) if hasattr(wt, "start_time") else (
                wt.get("start_time", wt.get("start_ms", 0.0) / 1000.0 if "start_ms" in wt else 0.0)
                if isinstance(wt, dict) else 0.0
            )
            e_time = getattr(wt, "end_time", None) if hasattr(wt, "end_time") else (
                wt.get("end_time", wt.get("end_ms", 0.0) / 1000.0 if "end_ms" in wt else s_time + 0.3)
                if isinstance(wt, dict) else s_time + 0.3
            )
            norm_wts.append((int(float(s_time) * 1000), int(float(e_time) * 1000)))

    if norm_wts:
        speech_start_ms = norm_wts[0][0]
        speech_end_ms = norm_wts[-1][1]

        desired_start_ms = max(0, speech_start_ms - lead_ms)
        desired_end_ms = desired_start_ms + trans_dur_ms

        if desired_start_ms < total_duration_ms:
            desired_end_ms = min(total_duration_ms, desired_end_ms)
            if desired_end_ms > desired_start_ms:
                char_shots.append({
                    "t_start": int(desired_start_ms),
                    "t_end": int(desired_end_ms),
                    "from_target": "wide",
                    "to_target": speaker_target,
                })

                # Hold at peak zoom at least min_hold_ms (1.2s)
                min_hold_end_ms = desired_end_ms + min_hold_ms
                return_start_ms = max(min_hold_end_ms, speech_end_ms + 200)

                if return_start_ms + trans_dur_ms <= total_duration_ms:
                    char_shots.append({
                        "t_start": int(return_start_ms),
                        "t_end": int(return_start_ms + trans_dur_ms),
                        "from_target": speaker_target,
                        "to_target": "wide",
                    })

    # 2. Board visual / purposeful cues for board camera
    board_shots: List[Dict[str, Any]] = []
    board_cues: List[Tuple[int, int, str]] = []
    if visuals:
        for idx, vis in enumerate(visuals):
            v_start = vis.get("start_ms") if isinstance(vis, dict) else getattr(vis, "start_ms", None)
            if v_start is None:
                v_start_sec = vis.get("start_time") if isinstance(vis, dict) else getattr(vis, "start_time", None)
                v_start = int(v_start_sec * 1000) if v_start_sec is not None else 0
            v_dur = vis.get("duration_ms") if isinstance(vis, dict) else getattr(vis, "duration_ms", 1000)
            v_id = vis.get("dom_id") if isinstance(vis, dict) else getattr(vis, "dom_id", None)
            if not v_id:
                v_id = vis.get("id") if isinstance(vis, dict) else getattr(vis, "id", f"visual_{idx+1}")
            target_name = f"board_{v_id}" if v_id else "board_close"
            board_cues.append((int(v_start), int(v_dur or 1000), target_name))

    board_cues.sort(key=lambda x: x[0])
    cur_board_target = "wide"
    last_board_end_ms = 0

    for cue_start_ms, cue_dur_ms, b_target in board_cues:
        b_move_start_ms = max(0, cue_start_ms - lead_ms)
        if board_shots and (b_move_start_ms < last_board_end_ms + min_hold_ms):
            continue
        b_move_end_ms = b_move_start_ms + trans_dur_ms
        if b_move_start_ms >= total_duration_ms:
            break
        b_move_end_ms = min(total_duration_ms, b_move_end_ms)
        if b_move_end_ms <= b_move_start_ms:
            continue

        board_shots.append({
            "t_start": int(b_move_start_ms),
            "t_end": int(b_move_end_ms),
            "from_target": cur_board_target,
            "to_target": b_target,
        })
        cur_board_target = b_target
        last_board_end_ms = b_move_end_ms

        cue_exit_ms = cue_start_ms + cue_dur_ms
        b_return_start_ms = max(last_board_end_ms + min_hold_ms, cue_exit_ms + 200)
        b_return_end_ms = b_return_start_ms + trans_dur_ms
        if b_return_end_ms <= total_duration_ms:
            board_shots.append({
                "t_start": int(b_return_start_ms),
                "t_end": int(b_return_end_ms),
                "from_target": cur_board_target,
                "to_target": "wide",
            })
            cur_board_target = "wide"
            last_board_end_ms = b_return_end_ms

    return {
        "character": char_shots,
        "board": board_shots,
    }
