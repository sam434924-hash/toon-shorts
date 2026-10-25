"""
Purpose: Camera shot language for toon-shorts (CHARACTER ZONE ONLY).
Inputs: Shot specifications, scene durations, presets, and evaluation frame indexes.
Outputs: Pure deterministic data model, shot presets, easing, per-frame camera evaluation, cut timing, and timeline validation.
Depends on: dataclasses, math, typing
Used by: core.camera
Config keys: None
Tests: tests/unit/test_camera_shots.py
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

CANVAS_W = 1080
CANVAS_H = 1920
FPS = 30
MAX_ZOOM_DEFAULT = 1.9   # character zone cap; raise only after a sharpness test
SNAP_FRAMES = 7          # snap-zoom length (6 to 8 frames)

SPEAKERS = ("A", "B", "BOTH", "REACTION")
MOTIONS = ("HOLD", "CREEP_IN", "PULL_BACK", "SNAP_ZOOM")
ENTRIES = ("CUT", "CONTINUE")
EYE_TARGETS = ("PARTNER", "BOARD", "CAMERA", "DOWN")

# Cut this many frames BEFORE the first spoken frame of the line.
CUT_LEAD_FRAMES = {"SPEAKER_CHANGE": 3, "REACTION": 12, "INTERRUPT": 2}

# Parallax factor per depth plane (character zone only; the board is not a plane here).
DEFAULT_PLANES: Dict[str, float] = {
    "bg_far": 0.25,
    "set_dressing": 0.65,
    "subjects": 1.00,
    "fg_edge": 1.35,
}


@dataclass(frozen=True)
class ShotPreset:
    code: str
    lens_mm: int
    zoom_min: float
    zoom_max: float
    center: Tuple[float, float]  # normalized (cx, cy)
    eye_line_y: int              # px from top on the 1920 canvas
    bg_blur_px: float
    use: str


PRESETS: Dict[str, ShotPreset] = {
    p.code: p
    for p in (
        ShotPreset("CAM_01_WIDE_2SHOT", 35, 1.00, 1.08, (0.50, 0.52), 760, 2.0,
                   "Opening hook and full two-person context"),
        ShotPreset("CAM_02_MED_BOARD", 50, 1.24, 1.36, (0.46, 0.48), 700, 4.5,
                   "Explaining while the board changes"),
        ShotPreset("CAM_03_OTS_SPEAKER_A", 58, 1.40, 1.48, (0.36, 0.50), 680, 8.0,
                   "Over the shoulder on speaker A"),
        ShotPreset("CAM_04_CU_SPEAKER_B", 85, 1.72, 1.80, (0.68, 0.44), 640, 14.0,
                   "Questions, challenges, deadpan reactions"),
        ShotPreset("CAM_05_CU_SPEAKER_A", 85, 1.80, 1.90, (0.30, 0.54), 660, 14.0,
                   "Hesitation or a realization"),
        # ECU needs zoom above MAX_ZOOM_DEFAULT: only after a sharpness test.
        ShotPreset("CAM_06_ECU_REACTION", 105, 2.15, 2.35, (0.68, 0.38), 610, 18.0,
                   "Punchline eyes or a macro detail"),
    )
}


@dataclass
class CameraShot:
    start_sec: float
    end_sec: float
    speaker: str
    preset: str
    zoom_start: float
    zoom_end: float
    center_start: Tuple[float, float]
    center_end: Tuple[float, float]
    motion: str = "HOLD"        # what happens INSIDE the shot
    entry: str = "CUT"          # how the shot begins: hard cut, or continue the last one
    eye_target: str = "PARTNER"

    def duration(self) -> float:
        return self.end_sec - self.start_sec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_sec": round(self.start_sec, 4),
            "end_sec": round(self.end_sec, 4),
            "speaker": self.speaker,
            "preset": self.preset,
            "zoom_start": round(self.zoom_start, 4),
            "zoom_end": round(self.zoom_end, 4),
            "center_start": [round(self.center_start[0], 4), round(self.center_start[1], 4)],
            "center_end": [round(self.center_end[0], 4), round(self.center_end[1], 4)],
            "motion": self.motion,
            "entry": self.entry,
            "eye_target": self.eye_target,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CameraShot:
        c_start = data.get("center_start", [0.5, 0.5])
        c_end = data.get("center_end", [0.5, 0.5])
        return cls(
            start_sec=float(data["start_sec"]),
            end_sec=float(data["end_sec"]),
            speaker=str(data["speaker"]),
            preset=str(data["preset"]),
            zoom_start=float(data["zoom_start"]),
            zoom_end=float(data["zoom_end"]),
            center_start=(float(c_start[0]), float(c_start[1])),
            center_end=(float(c_end[0]), float(c_end[1])),
            motion=str(data.get("motion", "HOLD")),
            entry=str(data.get("entry", "CUT")),
            eye_target=str(data.get("eye_target", "PARTNER")),
        )

    def problems(self, max_zoom: float = MAX_ZOOM_DEFAULT) -> List[str]:
        out: List[str] = []
        if not self.end_sec > self.start_sec:
            out.append("end_sec must be greater than start_sec")
        if self.speaker not in SPEAKERS:
            out.append(f"unknown speaker {self.speaker!r}")
        if self.preset not in PRESETS:
            out.append(f"unknown preset {self.preset!r}")
        if self.motion not in MOTIONS:
            out.append(f"unknown motion {self.motion!r}")
        if self.entry not in ENTRIES:
            out.append(f"unknown entry {self.entry!r}")
        if self.eye_target not in EYE_TARGETS:
            out.append(f"unknown eye_target {self.eye_target!r}")
        for name, z in (("zoom_start", self.zoom_start), ("zoom_end", self.zoom_end)):
            if not 1.0 <= z <= max_zoom:
                out.append(f"{name} {z} outside 1.0..{max_zoom}")
        for name, c in (("center_start", self.center_start), ("center_end", self.center_end)):
            if not (0.0 <= c[0] <= 1.0 and 0.0 <= c[1] <= 1.0):
                out.append(f"{name} {c} must be inside 0..1")
        dz = self.zoom_end - self.zoom_start
        if self.motion == "HOLD" and abs(dz) > 1e-6:
            out.append("HOLD must not change zoom")
        if self.motion in ("CREEP_IN", "SNAP_ZOOM") and dz <= 0:
            out.append(f"{self.motion} needs zoom_end > zoom_start")
        if self.motion == "PULL_BACK" and dz >= 0:
            out.append("PULL_BACK needs zoom_end < zoom_start")
        if self.motion in ("CREEP_IN", "PULL_BACK") and abs(dz) > 0.12:
            out.append(f"{self.motion} should stay subtle (change at most 0.12)")
        return out


@dataclass(frozen=True)
class Handheld:
    """Optional camera breathing. Off unless a theme turns it on."""
    amp_x: float = 3.5
    amp_y: float = 2.5
    amp_rot_deg: float = 0.18


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def ease_sine(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * _clamp(u))


def ease_cubic_out(u: float) -> float:
    u = _clamp(u)
    return 1.0 - (1.0 - u) ** 3


def bg_blur_for_zoom(zoom: float, wide: float = 2.0, close: float = 14.0,
                     z_wide: float = 1.0, z_close: float = 1.8) -> float:
    """Background blur grows as the camera pushes in."""
    u = _clamp((zoom - z_wide) / (z_close - z_wide))
    return round(wide + (close - wide) * u, 2)


def _motion_ease(shot: CameraShot, t_in_shot: float, fps: int) -> float:
    if shot.motion == "HOLD":
        return 0.0
    if shot.motion == "SNAP_ZOOM":
        snap = min(shot.duration(), SNAP_FRAMES / fps)
        return ease_cubic_out(t_in_shot / snap)
    return ease_sine(t_in_shot / shot.duration())  # CREEP_IN / PULL_BACK


def evaluate_camera(shot: CameraShot, frame_idx: int, fps: int = FPS,
                    handheld: Optional[Handheld] = None,
                    planes: Optional[Dict[str, float]] = None) -> dict:
    """Exact camera state for one frame. Same input always gives the same output."""
    planes = planes or DEFAULT_PLANES
    t = frame_idx / float(fps)
    t_in = _clamp(t - shot.start_sec, 0.0, shot.duration())
    e = _motion_ease(shot, t_in, fps)

    zoom = shot.zoom_start + (shot.zoom_end - shot.zoom_start) * e
    cx = shot.center_start[0] + (shot.center_end[0] - shot.center_start[0]) * e
    cy = shot.center_start[1] + (shot.center_end[1] - shot.center_start[1]) * e

    drift_x = drift_y = drift_rot = 0.0
    if handheld is not None:
        damp = 1.0 / (zoom ** 0.85)
        drift_x = handheld.amp_x * damp * (
            math.sin(2 * math.pi * 0.42 * t) + 0.5 * math.cos(2 * math.pi * 0.91 * t))
        drift_y = handheld.amp_y * damp * (
            math.cos(2 * math.pi * 0.37 * t) + 0.5 * math.sin(2 * math.pi * 0.78 * t))
        drift_rot = handheld.amp_rot_deg * damp * math.sin(2 * math.pi * 0.29 * t)

    plane_out = {}
    for name, p in planes.items():
        plane_out[name] = {
            "scale": round(1.0 + p * (zoom - 1.0), 4),
            "offset_px": (
                round((0.5 - cx) * CANVAS_W * p * zoom + drift_x * p, 2),
                round((0.5 - cy) * CANVAS_H * p * zoom + drift_y * p, 2),
            ),
        }
    return {
        "frame": frame_idx,
        "time_sec": round(t, 4),
        "preset": shot.preset,
        "speaker": shot.speaker,
        "zoom": round(zoom, 4),
        "center": (round(cx, 4), round(cy, 4)),
        "rotation_deg": round(drift_rot, 4),
        "bg_blur_px": bg_blur_for_zoom(zoom),
        "eye_target": shot.eye_target,
        "planes": plane_out,
    }


def cut_time_for_line(speech_start_sec: float, kind: str = "SPEAKER_CHANGE",
                      fps: int = FPS) -> float:
    """When to cut so the new shot is already there as the line begins."""
    if kind not in CUT_LEAD_FRAMES:
        raise ValueError(f"unknown cut kind {kind!r}")
    return max(0.0, speech_start_sec - CUT_LEAD_FRAMES[kind] / float(fps))


def shot_from_preset(code: str, start_sec: float, end_sec: float, speaker: str,
                     motion: str = "HOLD", entry: str = "CUT",
                     eye_target: str = "PARTNER", amount: float = 0.04) -> CameraShot:
    """Build a valid shot from a preset with sensible zoom and centre."""
    p = PRESETS[code]
    z0 = p.zoom_min
    if motion == "CREEP_IN":
        z1 = z0 + amount
    elif motion == "SNAP_ZOOM":
        z1 = z0 + 2 * amount
    elif motion == "PULL_BACK":
        z0, z1 = z0 + amount, z0
    else:
        z1 = z0
    return CameraShot(start_sec, end_sec, speaker, code, z0, z1,
                      p.center, p.center, motion, entry, eye_target)


def timeline_problems(shots: List[CameraShot], total_sec: Optional[float] = None,
                      fps: int = FPS, max_zoom: float = MAX_ZOOM_DEFAULT,
                      min_shot_sec: float = 0.4, max_shot_sec: float = 8.0) -> List[str]:
    """Every problem found; an empty list means the timeline is valid."""
    if not shots:
        return ["timeline has no shots"]
    tol = 1.0 / fps + 1e-9
    ordered = sorted(shots, key=lambda s: s.start_sec)
    out: List[str] = []
    for i, s in enumerate(ordered):
        out += [f"shot {i}: {p}" for p in s.problems(max_zoom)]
        d = s.duration()
        if d < min_shot_sec:
            out.append(f"shot {i}: shorter than {min_shot_sec}s")
        if d > max_shot_sec:
            out.append(f"shot {i}: longer than {max_shot_sec}s (something must change)")
        if i > 0:
            prev = ordered[i - 1]
            if abs(s.start_sec - prev.end_sec) > tol:
                out.append(f"shot {i}: gap or overlap with the previous shot")
            if s.entry == "CONTINUE" and abs(s.zoom_start - prev.zoom_end) > 0.02:
                out.append(f"shot {i}: CONTINUE must start at the previous zoom")
    if total_sec is not None:
        if abs(ordered[0].start_sec) > tol:
            out.append("first shot must start at 0")
        if abs(ordered[-1].end_sec - total_sec) > tol:
            out.append("last shot must end at the video length")
    return out


def _selftest() -> None:
    wide = shot_from_preset("CAM_01_WIDE_2SHOT", 0.0, 3.0, "BOTH", "CREEP_IN")
    med = CameraShot(3.0, 5.0, "A", "CAM_02_MED_BOARD", 1.28, 1.32,
                     (0.46, 0.48), (0.46, 0.48), "CREEP_IN", "CUT", "BOARD")
    snap = CameraShot(5.0, 7.0, "B", "CAM_02_MED_BOARD", 1.28, 1.36,
                      (0.48, 0.48), (0.48, 0.48), "SNAP_ZOOM", "CUT", "BOARD")
    cu = shot_from_preset("CAM_04_CU_SPEAKER_B", 7.0, 9.0, "B", "HOLD")
    shots = [wide, med, snap, cu]

    assert timeline_problems(shots, total_sec=9.0) == [], timeline_problems(shots, 9.0)

    # same input, same output (deterministic)
    assert evaluate_camera(med, 120) == evaluate_camera(med, 120)

    # creep rises smoothly; snap reaches its end zoom within the snap window
    zs = [evaluate_camera(wide, f)["zoom"] for f in range(0, 90, 10)]
    assert zs == sorted(zs) and zs[-1] > zs[0]
    assert evaluate_camera(snap, int(5.0 * FPS) + SNAP_FRAMES)["zoom"] >= 1.35

    # blur grows with zoom; planes exist; handheld off by default
    assert bg_blur_for_zoom(1.0) == 2.0 and bg_blur_for_zoom(1.8) == 14.0
    st = evaluate_camera(cu, 8 * FPS)
    assert set(st["planes"]) == set(DEFAULT_PLANES) and st["rotation_deg"] == 0.0
    hh = evaluate_camera(cu, 8 * FPS, handheld=Handheld())
    assert hh["rotation_deg"] != 0.0

    # cut timing
    assert abs(cut_time_for_line(10.0, "REACTION") - (10.0 - 12 / FPS)) < 1e-9
    assert cut_time_for_line(0.05, "REACTION") == 0.0

    # bad shots are caught with clear messages
    bad = CameraShot(0.0, 2.0, "X", "NOPE", 0.9, 2.5, (1.2, 0.5), (0.5, 0.5), "HOLD")
    msgs = bad.problems()
    assert any("speaker" in m for m in msgs) and any("preset" in m for m in msgs)
    assert any("zoom_start" in m for m in msgs) and any("zoom_end" in m for m in msgs)
    assert any("center_start" in m for m in msgs)
    gap = [wide, CameraShot(3.5, 5.0, "A", "CAM_02_MED_BOARD", 1.28, 1.28,
                            (0.46, 0.48), (0.46, 0.48))]
    assert any("gap" in m for m in timeline_problems(gap))
    print("camera_shots selftest OK")


if __name__ == "__main__":
    _selftest()
