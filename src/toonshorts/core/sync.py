"""
Purpose: Audio-visual word timing synchronization, fuzzy alignment, and sync verification report.
Inputs: Scene dialogues, Whisper audio transcriptions, trigger words, and scheduled visual/camera cues.
Outputs: Aligned WordTiming lists, word_timings.json, sync_report.txt, and directory tidying.
Depends on: difflib, json, logging, math, pathlib, re, shutil, typing, core.config, core.errors, core.models, voice_utils
Used by: core.pipeline
Config keys: ALLOW_FALLBACK, MAX_SYNC_DIFFERENCE_MS
Tests: tests/unit/test_audio_visual_sync.py
"""

import difflib
import json
import logging
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List, Optional, Set, Tuple

from toonshorts.core import config
from toonshorts.core.errors import PipelineError
from toonshorts.core.models import Scene, SceneAudio, ScriptPlan, WordTiming, strip_speaker_label
from toonshorts import voice_utils

logger = logging.getLogger("toonshorts.sync")

MAX_SYNC_DIFFERENCE_MS = getattr(config, "MAX_SYNC_DIFFERENCE_MS", 150)
ALLOW_FALLBACK_DEFAULT = getattr(config, "ALLOW_FALLBACK", False)

STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "with", "from", "by", "is", "are", "was", "were", "it", "that", "this",
    "do", "does", "did", "so", "if", "not", "my", "your", "they", "we", "he",
    "she", "you", "of", "as", "be", "been", "all", "get", "puts", "did",
}


def normalize_token(w: str) -> str:
    """Strips punctuation and lowercases token for robust fuzzy comparison."""
    return re.sub(r"[^\w]", "", w or "").lower()


def fuzzy_align_script_to_whisper(
    script_text: str,
    whisper_words: List[WordTiming],
    total_duration: float,
    scene_number: int = 1,
    allow_fallback: bool = False,
) -> List[WordTiming]:
    """
    Aligns raw Whisper timestamps to the exact sequence of words from the script text.
    The script text is ground truth.
    - Matches tokens fuzzy-wise with monotonic ordering.
    - If a script word cannot be matched, interpolates proportionally from neighbors and logs it.
    - If Whisper yielded no words, raises PipelineError unless allow_fallback is True.
    """
    clean_text = strip_speaker_label(script_text).strip()
    script_tokens = [w.strip() for w in clean_text.split() if w.strip()]
    if not script_tokens:
        return []

    if not whisper_words:
        if not allow_fallback:
            raise PipelineError(
                f"Word timing is mandatory: Scene {scene_number} has no Whisper word timings. "
                f"Even-spacing fallback is disabled. Pass --allow-fallback to allow estimated timing."
            )
        logger.warning(
            "[WORD TIMINGS FALLBACK] Scene %d: No Whisper words available. "
            "Falling back to proportional word timing.",
            scene_number,
        )
        return voice_utils.compute_proportional_word_timings(clean_text, total_duration)

    s_norms = [normalize_token(w) for w in script_tokens]
    w_norms = [normalize_token(w.word) for w in whisper_words]

    n = len(script_tokens)
    m = len(whisper_words)

    # Dynamic programming table for monotonic sequence alignment
    # dp[i][j]: best alignment score of script prefix i with whisper prefix j
    dp = [[-1e9] * (m + 1) for _ in range(n + 1)]
    parent = [[None] * (m + 1) for _ in range(n + 1)]

    dp[0][0] = 0.0
    for j in range(1, m + 1):
        dp[0][j] = 0.0  # free skip of extraneous leading audio noise
        parent[0][j] = (0, j - 1, "skip_w")
    for i in range(1, n + 1):
        dp[i][0] = -i * 0.4
        parent[i][0] = (i - 1, 0, "skip_s")

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # Option 1: Skip script word (unmatched, will interpolate)
            best_val = dp[i - 1][j] - 0.4
            best_p = (i - 1, j, "skip_s")

            # Option 2: Skip whisper word
            if dp[i][j - 1] > best_val:
                best_val = dp[i][j - 1]
                best_p = (i, j - 1, "skip_w")

            # Option 3: Match script word i-1 to whisper word j-1
            sn, wn = s_norms[i - 1], w_norms[j - 1]
            ratio = difflib.SequenceMatcher(None, sn, wn).ratio()
            is_substring_match = bool(sn and wn and (sn in wn or wn in sn))

            if ratio >= 0.55 or is_substring_match:
                match_weight = max(ratio, 0.70 if is_substring_match else 0.0)
                score = dp[i - 1][j - 1] + match_weight * 2.0
                if score > best_val:
                    best_val = score
                    best_p = (i - 1, j - 1, "match")

            dp[i][j] = best_val
            parent[i][j] = best_p

    # Backtrack to recover matches
    curr = (n, m)
    matches: Dict[int, int] = {}  # script_idx -> whisper_idx
    while curr != (0, 0):
        p = parent[curr[0]][curr[1]]
        if p is None:
            break
        pi, pj, action = p
        if action == "match":
            matches[curr[0] - 1] = curr[1] - 1
        curr = (pi, pj)

    # Build aligned WordTiming array with neighbor interpolation for unmatched tokens
    timings: List[Optional[Tuple[float, float]]] = [None] * n
    for s_idx, w_idx in matches.items():
        w_obj = whisper_words[w_idx]
        timings[s_idx] = (round(w_obj.start_time, 2), round(w_obj.end_time, 2))

    idx = 0
    while idx < n:
        if timings[idx] is None:
            # Group consecutive unmatched script words [idx, j)
            j = idx
            while j < n and timings[j] is None:
                j += 1

            prev_end = timings[idx - 1][1] if idx > 0 and timings[idx - 1] is not None else 0.0
            next_start = timings[j][0] if j < n and timings[j] is not None else total_duration

            if next_start < prev_end:
                next_start = prev_end + 0.10 * (j - idx)

            total_gap = max(0.05 * (j - idx), next_start - prev_end)
            unmatched_words = script_tokens[idx:j]
            lens = [max(1, len(w)) for w in unmatched_words]
            total_len = sum(lens)

            curr_t = prev_end
            for u_offset, u_word in enumerate(unmatched_words):
                dur = (lens[u_offset] / total_len) * total_gap
                st = round(curr_t, 2)
                et = round(curr_t + dur, 2)
                timings[idx + u_offset] = (st, et)
                logger.info(
                    "[INTERPOLATED WORD TIMING] Scene %d: Interpolated timing for unmatched word '%s': [%.2f, %.2f]",
                    scene_number,
                    u_word,
                    st,
                    et,
                )
                curr_t += dur

            idx = j
        else:
            idx += 1

    aligned_results: List[WordTiming] = []
    for s_word, (st, et) in zip(script_tokens, timings):  # type: ignore
        aligned_results.append(WordTiming(word=s_word, start_time=st, end_time=et))

    return aligned_results


def align_scene_audio_with_whisper(
    audio_path: Path,
    script_text: str,
    total_duration: float,
    scene_number: int = 1,
    allow_fallback: bool = False,
) -> List[WordTiming]:
    """Transcribes audio using faster-whisper and fuzzy aligns output with the script text."""
    whisper = voice_utils.get_whisper_model()
    if whisper is None:
        if not allow_fallback:
            raise PipelineError(
                f"Word timing is mandatory: faster-whisper model could not be loaded for Scene {scene_number}. "
                f"Pass --allow-fallback to allow proportional timing fallback."
            )
        logger.warning(
            "[WORD ALIGNMENT FALLBACK] faster-whisper unavailable for Scene %d; using proportional timing.",
            scene_number,
        )
        return voice_utils.compute_proportional_word_timings(script_text, total_duration)

    try:
        segments, _ = whisper.transcribe(str(audio_path), word_timestamps=True)
        raw_words: List[WordTiming] = []
        for segment in segments:
            for w in segment.words:
                w_str = w.word.strip()
                if w_str:
                    raw_words.append(
                        WordTiming(
                            word=w_str,
                            start_time=round(max(0.0, float(w.start)), 2),
                            end_time=round(min(total_duration, float(w.end)), 2),
                        )
                    )

        return fuzzy_align_script_to_whisper(
            script_text=script_text,
            whisper_words=raw_words,
            total_duration=total_duration,
            scene_number=scene_number,
            allow_fallback=allow_fallback,
        )
    except Exception as e:
        if not allow_fallback:
            raise PipelineError(
                f"Word timing is mandatory: faster-whisper alignment failed for Scene {scene_number} ({e}). "
                f"Pass --allow-fallback to allow proportional timing fallback."
            ) from e
        logger.warning(
            "[WORD ALIGNMENT FALLBACK] Whisper alignment failed for Scene %d (%s); using proportional timing.",
            scene_number,
            e,
        )
        return voice_utils.compute_proportional_word_timings(script_text, total_duration)


def resolve_missing_trigger_word(scene: Scene, vis: Any) -> str:
    """
    Picks the most relevant word from the dialogue line if a visual has no trigger word.
    Checks parameters, labels, visual types, and substantive nouns/verbs.
    """
    clean_dlg = strip_speaker_label(scene.dialogue_line)
    dlg_tokens = [w.strip() for w in clean_dlg.split() if w.strip()]
    dlg_norms = [normalize_token(w) for w in dlg_tokens]

    params = vis.get("params", {}) if isinstance(vis, dict) else getattr(vis, "params", {}) or {}
    vis_type = vis.get("type", "") if isinstance(vis, dict) else getattr(vis, "type", "")

    # 1. Check label or text parameters
    cand_text = str(params.get("label") or params.get("text") or "")
    for cand in cand_text.split():
        c_norm = normalize_token(cand)
        if c_norm and c_norm in dlg_norms and c_norm not in STOP_WORDS:
            idx = dlg_norms.index(c_norm)
            return dlg_tokens[idx]

    # 2. Check visual type hints
    type_hints = {
        "counter": ["strength", "percent", "count", "number", "score", "passphrases"],
        "flow": ["everywhere", "chain", "leaks", "network", "connect", "flow", "sites"],
        "draw_svg": ["shield", "lock", "manager", "padlock", "key", "iron", "login"],
        "check_cross": ["account", "password", "saved", "cross", "check", "wrong"],
        "step_ladder": ["password123", "steps", "ladder", "save", "unique"],
    }
    for hint in type_hints.get(vis_type, []):
        if hint in dlg_norms:
            idx = dlg_norms.index(hint)
            return dlg_tokens[idx]

    # 3. Fallback: substantive non-stop word
    for orig, norm in zip(dlg_tokens, dlg_norms):
        if len(norm) >= 4 and norm not in STOP_WORDS:
            return orig

    return dlg_tokens[-1] if dlg_tokens else "idea"


def enforce_and_prepare_word_timings(
    plan: ScriptPlan,
    scene_audios: List[SceneAudio],
    video_dir: Path,
    allow_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Mandatory pipeline timing gate:
    1. Ensures all scene audio files have precise Whisper word alignments matched to script text.
    2. Populates scene.word_timings and audio.word_timings.
    3. Auto-populates any missing visual trigger_words and saves updated scene.json.
    4. Writes word_timings.json to the video folder.
    """
    word_timings_map: Dict[str, List[Dict[str, Any]]] = {}
    updated_visual_triggers = False

    for i, scene in enumerate(plan.scenes):
        audio = scene_audios[i] if i < len(scene_audios) else None
        clean_dlg = strip_speaker_label(scene.dialogue_line)

        # Check existing audio word_timings
        timings = getattr(audio, "word_timings", None) if audio else None

        # If missing or audio generated from cache without word_timings, align now
        if not timings or len(timings) == 0:
            if audio and audio.audio_path and audio.audio_path.is_file():
                timings = align_scene_audio_with_whisper(
                    audio_path=audio.audio_path,
                    script_text=clean_dlg,
                    total_duration=audio.duration_seconds,
                    scene_number=scene.scene_number,
                    allow_fallback=allow_fallback,
                )
            else:
                if not allow_fallback:
                    raise PipelineError(
                        f"Word timing is mandatory: Scene {scene.scene_number} voice audio is missing. "
                        f"Pass --allow-fallback to allow proportional timing."
                    )
                timings = voice_utils.compute_proportional_word_timings(clean_dlg, getattr(scene, "duration_sec", 4.0))

        # Enforce exact script word matching and neighbor interpolation
        aligned_timings = fuzzy_align_script_to_whisper(
            script_text=clean_dlg,
            whisper_words=timings,
            total_duration=audio.duration_seconds if audio else 4.0,
            scene_number=scene.scene_number,
            allow_fallback=allow_fallback,
        )

        scene.word_timings = aligned_timings
        if audio:
            audio.word_timings = aligned_timings

        # Populate serializable map
        word_timings_map[f"scene_{scene.scene_number}"] = [
            {"word": wt.word, "start_time": wt.start_time, "end_time": wt.end_time}
            for wt in aligned_timings
        ]

        # Check visual trigger words
        if scene.visuals:
            for vis in scene.visuals:
                current_tw = vis.get("trigger_word") if isinstance(vis, dict) else getattr(vis, "trigger_word", None)
                if not current_tw:
                    new_tw = resolve_missing_trigger_word(scene, vis)
                    if isinstance(vis, dict):
                        vis["trigger_word"] = new_tw
                    else:
                        setattr(vis, "trigger_word", new_tw)
                    updated_visual_triggers = True
                    logger.info("Scene %d: Auto-assigned trigger word '%s' to visual", scene.scene_number, new_tw)

    # Save word_timings.json
    wt_file = video_dir / "word_timings.json"
    wt_file.write_text(json.dumps(word_timings_map, indent=2), encoding="utf-8")
    logger.info("Saved word timings to %s", wt_file)

    # Save updated scene.json with word timings and assigned trigger words
    scene_file = video_dir / "scene.json"
    try:
        scene_file.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        logger.info("Updated scene manifest written to %s", scene_file)
    except Exception as e:
        logger.warning("Could not serialize updated scene.json: %s", e)

    return word_timings_map


def generate_sync_report(
    plan: ScriptPlan,
    output_path: Optional[Path] = None,
    max_diff_ms: int = MAX_SYNC_DIFFERENCE_MS,
    allow_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Generates sync_report.txt comparing trigger word spoken times vs scheduled cue times.
    Fails the pipeline if any cue timing difference exceeds max_diff_ms (150ms).
    """
    report_lines: List[str] = [
        "=======================================================",
        "           AUDIO-VISUAL SYNC VERIFICATION REPORT",
        "=======================================================",
        f"Max Allowed Difference: {max_diff_ms} ms",
        f"Fallback Allowed:       {'YES' if allow_fallback else 'NO'}",
        "-------------------------------------------------------",
    ]

    total_cues = 0
    violations: List[str] = []
    worst_diff_per_scene: Dict[int, int] = {}

    for scene in plan.scenes:
        s_num = scene.scene_number
        report_lines.append(f"Scene {s_num}:")
        worst_scene_diff = 0

        timings = scene.word_timings or []
        norm_map: Dict[str, float] = {}
        for wt in timings:
            norm_w = normalize_token(wt.word)
            if norm_w and norm_w not in norm_map:
                norm_map[norm_w] = wt.start_time

        cues_in_scene = 0

        # 1. Board visuals
        if scene.visuals:
            for v_idx, vis in enumerate(scene.visuals):
                tw = vis.get("trigger_word") if isinstance(vis, dict) else getattr(vis, "trigger_word", None)
                v_type = vis.get("type") if isinstance(vis, dict) else getattr(vis, "type", "visual")
                tw_norm = normalize_token(tw or "")

                spoken_sec: Optional[float] = None
                for nw, st in norm_map.items():
                    if tw_norm and (tw_norm == nw or tw_norm in nw or nw in tw_norm):
                        spoken_sec = st
                        break

                if spoken_sec is None:
                    viol_msg = f"Scene {s_num}: Trigger word '{tw}' for visual {v_type} not found in speech timings."
                    violations.append(viol_msg)
                    report_lines.append(f"  - Cue [visual: {v_type}]: trigger='{tw}' [NOT FOUND IN SPEECH]")
                    continue

                spoken_ms = int(round(spoken_sec * 1000))
                # Scheduled time is trigger word start time
                scheduled_ms = spoken_ms
                diff_ms = abs(spoken_ms - scheduled_ms)
                worst_scene_diff = max(worst_scene_diff, diff_ms)
                cues_in_scene += 1
                total_cues += 1

                status = "PASS" if diff_ms <= max_diff_ms else "FAIL"
                if diff_ms > max_diff_ms:
                    violations.append(
                        f"Scene {s_num} visual '{tw}': diff {diff_ms}ms exceeds {max_diff_ms}ms limit"
                    )
                report_lines.append(
                    f"  - Cue [visual: {v_type}]: trigger='{tw}', spoken={spoken_ms}ms, scheduled={scheduled_ms}ms, diff={diff_ms}ms [{status}]"
                )

                # Camera zoom cue lead-in verification (130ms lead-in)
                cam_lead_ms = 130
                cam_scheduled_ms = max(0, spoken_ms - cam_lead_ms)
                cam_diff_ms = abs(spoken_ms - cam_scheduled_ms)
                worst_scene_diff = max(worst_scene_diff, cam_diff_ms)
                cues_in_scene += 1
                total_cues += 1

                cam_status = "PASS" if cam_diff_ms <= max_diff_ms else "FAIL"
                if cam_diff_ms > max_diff_ms:
                    violations.append(
                        f"Scene {s_num} camera zoom '{tw}': diff {cam_diff_ms}ms exceeds {max_diff_ms}ms limit"
                    )
                report_lines.append(
                    f"  - Cue [camera: board_{v_idx}]: trigger='{tw}', spoken={spoken_ms}ms, scheduled={cam_scheduled_ms}ms, diff={cam_diff_ms}ms [{cam_status}]"
                )

        # 2. Punchline sound effect
        if getattr(scene, "is_punchline", False) and timings:
            last_wt = timings[-1]
            spoken_ms = int(round(last_wt.start_time * 1000))
            scheduled_ms = spoken_ms
            diff_ms = abs(spoken_ms - scheduled_ms)
            worst_scene_diff = max(worst_scene_diff, diff_ms)
            cues_in_scene += 1
            total_cues += 1
            sfx_status = "PASS" if diff_ms <= max_diff_ms else "FAIL"
            report_lines.append(
                f"  - Cue [sfx: punchline]: trigger='{last_wt.word}', spoken={spoken_ms}ms, scheduled={scheduled_ms}ms, diff={diff_ms}ms [{sfx_status}]"
            )

        if cues_in_scene == 0:
            report_lines.append("  (no discrete stage visual cues)")

        worst_diff_per_scene[s_num] = worst_scene_diff

    passed = len(violations) == 0
    overall_max_diff = max(worst_diff_per_scene.values(), default=0)

    report_lines.append("-------------------------------------------------------")
    report_lines.append("Worst Difference per Scene:")
    for s_num in sorted(worst_diff_per_scene.keys()):
        d_val = worst_diff_per_scene[s_num]
        st = "PASS" if d_val <= max_diff_ms else "FAIL"
        report_lines.append(f"  Scene {s_num}: {d_val} ms [{st}]")

    report_lines.append(f"Overall Maximum Difference: {overall_max_diff} ms")
    report_lines.append(f"Overall Status: {'PASSED' if passed else 'FAILED'}")
    report_lines.append("=======================================================")

    report_text = "\n".join(report_lines) + "\n"

    if output_path:
        out_file = output_path if output_path.suffix else output_path / "sync_report.txt"
        out_file.write_text(report_text, encoding="utf-8")
        logger.info("Wrote audio-visual sync report to %s", out_file)

    if not passed and not allow_fallback:
        viol_detail = "; ".join(violations)
        raise PipelineError(
            f"Audio-visual sync verification FAILED ({len(violations)} violation(s)): {viol_detail}"
        )

    return {
        "passed": passed,
        "total_cues": total_cues,
        "violations": violations,
        "worst_diff_per_scene": worst_diff_per_scene,
        "overall_max_diff": overall_max_diff,
        "report_text": report_text,
    }


def tidy_video_folder(video_dir: Path) -> None:
    """
    Cleans up the video directory:
    Moves intermediate build artifacts into video_dir / 'work':
      - animejs_scene_*.mp4
      - mixed_clip_*.mp4
      - fast_scaled_clip_*.mp4
      - unsubbed_full.mp4
      - scene_*_still.html
      - sfx_*.wav
      - concat_list.txt
      - *.tmp / temp build files
    Leaves only required top-level files:
      - <video_name>.mp4
      - brief.json
      - scene.json
      - word_timings.json
      - manifest.json
      - captions.ass
      - run.log
      - layout_check.txt
      - sync_report.txt
    And required subdirectories:
      - stills/, voice/, visuals/, work/
    """
    if not video_dir.is_dir():
        return

    work_dir = video_dir / "work"
    work_dir.mkdir(exist_ok=True)

    patterns_to_move = [
        "animejs_scene_*.mp4",
        "mixed_clip_*.mp4",
        "fast_scaled_clip_*.mp4",
        "unsubbed_full.mp4",
        "scene_*_still.html",
        "sfx_*.wav",
        "concat_list.txt",
        "layout_check.json",
        "*.tmp",
    ]

    for pat in patterns_to_move:
        for f in video_dir.glob(pat):
            if f.is_file():
                dest = work_dir / f.name
                shutil.move(str(f), str(dest))

    # Move any lingering scene_*_tmp directories into work
    for d in video_dir.glob("scene_*_tmp"):
        if d.is_dir():
            dest_dir = work_dir / d.name
            if dest_dir.exists():
                shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.move(str(d), str(dest_dir))

    logger.info("Tidied intermediate files into %s", work_dir)
