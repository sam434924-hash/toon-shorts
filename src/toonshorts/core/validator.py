"""
Purpose: Screenplay v1/v2 schema validation, directing rules enforcement, and plan adaptation.
Inputs: ScriptPlan objects or raw dictionary representations of script plans.
Outputs: Validated ScriptPlan instances or descriptive one-line validation errors.
Depends on: core.models, core.visuals, re, typing
Used by: core.pipeline, plugins.llm.gemini
Config keys: None
Tests: tests/unit/test_validation.py, tests/unit/test_v2_validation.py, tests/unit/test_visual_templates.py
"""

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from toonshorts.core.models import (
    Character,
    PlanValidationError,
    Scene,
    ScriptPlan,
    Shot,
    Visual,
)
from toonshorts.core.visuals import (
    check_stage_layout_overflow,
    validate_visual_item,
)


def estimate_scene_duration(dialogue_line: str) -> float:
    """Estimates scene duration from spoken dialogue word count (at ~2.5 wps + 1.2s padding)."""
    words = re.findall(r"\w+", dialogue_line or "")
    word_count = len(words)
    return max(2.5, word_count * 0.40 + 1.2)


def adapt_plan_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter ensuring older v1 plans load seamlessly into v2 architecture.
    Preserves exact content while providing default version and scene layouts.
    """
    adapted = dict(data)
    if "version" not in adapted:
        adapted["version"] = 1

    if "scenes" in adapted and isinstance(adapted["scenes"], list):
        new_scenes = []
        for sc in adapted["scenes"]:
            if isinstance(sc, dict):
                sc_copy = dict(sc)
                if "layout" not in sc_copy:
                    sc_copy["layout"] = "cards"
                if "shots" not in sc_copy:
                    sc_copy["shots"] = None
                if "visuals" not in sc_copy:
                    sc_copy["visuals"] = None
                new_scenes.append(sc_copy)
            else:
                new_scenes.append(sc)
        adapted["scenes"] = new_scenes

    return adapted


def validate_shots(
    shots: List[Shot],
    cast: List[str],
    scene_number: int,
    scene_length: float,
    previous_zoom_scene_time: Optional[float] = None,
) -> Tuple[List[str], Optional[float]]:
    """
    Enforces camera and shot limits from the toon-shorts-directing skill:
    - zoom <= 1.35
    - ease times 0.4 to 0.6 s
    - minimum hold 1.2 s
    - at most one zoom per 5 s
    - target must exist in the cast
    - no overlapping shots
    - shots inside the scene length
    """
    errors: List[str] = []
    cast_lower = {c.lower() for c in cast}
    last_zoom_time = previous_zoom_scene_time

    # Sort shots by start time to check ordering and overlaps
    sorted_shots = sorted(shots, key=lambda s: (s.start, s.end))

    for idx, shot in enumerate(sorted_shots):
        # 1. Inside scene length
        if shot.start < 0.0 or shot.end > (scene_length + 1e-4):
            errors.append(
                f"Scene {scene_number}: shots: shot times [{shot.start:.2f}s - {shot.end:.2f}s] must be inside scene length {scene_length:.2f}s"
            )
        if shot.end <= shot.start:
            errors.append(
                f"Scene {scene_number}: shots: end time ({shot.end:.2f}s) must be greater than start time ({shot.start:.2f}s)"
            )

        # 2. Overlap check with previous shot
        if idx > 0:
            prev_shot = sorted_shots[idx - 1]
            if prev_shot.end > shot.start + 1e-4:
                errors.append(
                    f"Scene {scene_number}: shots: overlapping shots between [{prev_shot.start:.2f}s - {prev_shot.end:.2f}s] and [{shot.start:.2f}s - {shot.end:.2f}s]"
                )

        # 3. Zoom limit
        if shot.zoom > 1.35 + 1e-4:
            errors.append(
                f"Scene {scene_number}: shots: zoom ({shot.zoom:.2f}) must be <= 1.35"
            )
        if shot.zoom < 1.0 - 1e-4:
            errors.append(
                f"Scene {scene_number}: shots: zoom ({shot.zoom:.2f}) must be >= 1.0"
            )

        # 4. Ease times
        if not (0.4 - 1e-4 <= shot.ease_in <= 0.6 + 1e-4):
            errors.append(
                f"Scene {scene_number}: shots: ease_in ({shot.ease_in:.2f}s) must be between 0.4 and 0.6 s"
            )
        if not (0.4 - 1e-4 <= shot.ease_out <= 0.6 + 1e-4):
            errors.append(
                f"Scene {scene_number}: shots: ease_out ({shot.ease_out:.2f}s) must be between 0.4 and 0.6 s"
            )

        # 5. Minimum hold 1.2 s
        hold_time = (shot.end - shot.start) - (shot.ease_in + shot.ease_out)
        if shot.type == "close_up" or shot.zoom > 1.0 + 1e-4:
            if hold_time < 1.2 - 1e-4:
                errors.append(
                    f"Scene {scene_number}: shots: minimum hold must be at least 1.2 s (got {hold_time:.2f}s)"
                )
        else:
            duration = shot.end - shot.start
            if duration < 1.2 - 1e-4:
                errors.append(
                    f"Scene {scene_number}: shots: minimum hold must be at least 1.2 s (got {duration:.2f}s)"
                )

        # 6. Target must exist in cast
        if shot.target:
            if shot.target.lower() not in cast_lower:
                errors.append(
                    f"Scene {scene_number}: shots: target '{shot.target}' must exist in scene cast {cast}"
                )

        # 7. At most one zoom per 5 s
        is_zoom = (shot.type == "close_up") or (shot.zoom > 1.0 + 1e-4)
        if is_zoom:
            if last_zoom_time is not None:
                delta = shot.start - last_zoom_time
                if delta < 5.0 - 1e-4:
                    errors.append(
                        f"Scene {scene_number}: shots: at most one zoom per 5 s (previous zoom was {delta:.2f}s prior)"
                    )
            last_zoom_time = shot.start

    return errors, last_zoom_time


def validate_plan(
    plan_or_data: Union[ScriptPlan, Dict[str, Any]],
    scene_lengths: Optional[Dict[int, float]] = None,
) -> ScriptPlan:
    """
    Validates a ScriptPlan against all v1 and v2 rules.
    Raises PlanValidationError with concise one-line error messages on any rule violation.
    """
    # 1. Parse or adapt input
    raw_data: Optional[Dict[str, Any]] = None
    if isinstance(plan_or_data, dict):
        raw_data = plan_or_data
        adapted_data = adapt_plan_v1_to_v2(raw_data)
        try:
            plan = ScriptPlan.model_validate(adapted_data)
        except Exception as exc:
            msg = str(exc)
            first_err = msg.split("\n")[0]
            sc_match = re.search(r"scenes\.(\d+)\.(\w+)", msg)
            if sc_match:
                sc_idx = int(sc_match.group(1)) + 1
                field = sc_match.group(2)
                raise PlanValidationError(
                    f"Scene {sc_idx}: {field}: validation failed: {first_err}",
                    scene_number=sc_idx,
                    field=field,
                ) from exc
            raise PlanValidationError(f"Plan validation failed: {first_err}") from exc
    elif isinstance(plan_or_data, ScriptPlan):
        plan = plan_or_data
    else:
        raise PlanValidationError("Invalid plan input: must be ScriptPlan or dictionary")

    # 2. Check characters and cast
    declared_chars = {c.name.lower(): c.name for c in plan.characters}
    canonical_cast_order: Optional[List[str]] = None

    last_zoom_global_time: Optional[float] = None
    accumulated_time = 0.0

    all_errors: List[str] = []

    for sc in plan.scenes:
        # Determine scene length
        if scene_lengths and sc.scene_number in scene_lengths:
            sc_len = scene_lengths[sc.scene_number]
        else:
            sc_len = estimate_scene_duration(sc.dialogue_line)

        # Cast validation
        scene_cast = sc.cast
        if scene_cast is not None:
            if len(scene_cast) > 2:
                all_errors.append(
                    f"Scene {sc.scene_number}: cast: exceeds maximum of 2 characters (got {len(scene_cast)})"
                )
            for c_name in scene_cast:
                if c_name.lower() not in declared_chars:
                    all_errors.append(
                        f"Scene {sc.scene_number}: cast: character '{c_name}' is not declared in characters list"
                    )

            # Speaker must be in cast
            if scene_cast and sc.speaker.lower() not in {c.lower() for c in scene_cast}:
                all_errors.append(
                    f"Scene {sc.scene_number}: speaker: '{sc.speaker}' must exist in scene cast {scene_cast}"
                )

            # 180-degree rule: Character ordering must not swap
            cleaned_cast = [c.lower() for c in scene_cast if c.lower() in declared_chars]
            if len(cleaned_cast) == 2:
                if canonical_cast_order is None:
                    canonical_cast_order = cleaned_cast
                else:
                    if cleaned_cast != canonical_cast_order and cleaned_cast == list(reversed(canonical_cast_order)):
                        all_errors.append(
                            f"Scene {sc.scene_number}: cast: 180-degree rule violation: characters swapped sides from {canonical_cast_order} to {cleaned_cast}"
                        )
        else:
            scene_cast = [sc.speaker]

        # Layout validation
        if sc.layout not in ("cards", "stage"):
            all_errors.append(
                f"Scene {sc.scene_number}: layout: must be 'cards' or 'stage' (got '{sc.layout}')"
            )

        # Visuals validation
        if sc.visuals:
            if len(sc.visuals) > 3:
                all_errors.append(
                    f"Scene {sc.scene_number}: visuals: at most 3 visuals allowed per scene (got {len(sc.visuals)})"
                )
            for v_idx, vis in enumerate(sc.visuals):
                v_type = vis.type if hasattr(vis, "type") else vis.get("type", "")
                t_word = vis.trigger_word if hasattr(vis, "trigger_word") else vis.get("trigger_word", "")
                params = vis.params if hasattr(vis, "params") else vis.get("params", {})
                v_errs = validate_visual_item(
                    v_type=v_type,
                    trigger_word=t_word,
                    params=params,
                    scene_number=sc.scene_number,
                    visual_index=v_idx,
                )
                all_errors.extend(v_errs)

            if sc.layout == "stage":
                layout_errs = check_stage_layout_overflow(sc.visuals, sc.scene_number)
                all_errors.extend(layout_errs)

        # Shots validation
        if sc.shots:
            prev_zoom_rel = None
            if last_zoom_global_time is not None:
                prev_zoom_rel = last_zoom_global_time - accumulated_time

            shot_errors, new_last_zoom = validate_shots(
                shots=sc.shots,
                cast=scene_cast,
                scene_number=sc.scene_number,
                scene_length=sc_len,
                previous_zoom_scene_time=prev_zoom_rel,
            )
            all_errors.extend(shot_errors)
            if new_last_zoom is not None:
                last_zoom_global_time = accumulated_time + new_last_zoom

        accumulated_time += sc_len

    if all_errors:
        raise PlanValidationError(all_errors[0])

    return plan
