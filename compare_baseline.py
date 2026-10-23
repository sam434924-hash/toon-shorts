"""
Baseline comparison script for ToonShorts.
Renders standard test video, extracts reference frames, and compares
duration, frame count, and per-frame image differences against baseline.
"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent
BASELINE_DIR = PROJECT_ROOT / "baseline"
BRIEF_PATH = PROJECT_ROOT / "briefs" / "octopus_facts_v2.json"
DEFAULT_TEST_DIR = PROJECT_ROOT / "temp" / "baseline_compare_run"

REFERENCE_TIMESTAMPS = [
    (1.5, "frame_1_arm_gesture.png", "Arm gesture (explain)"),
    (3.5, "frame_2_punch_in.png", "Camera punch-in (1.16x)"),
    (4.2, "frame_3_annotation_hearts.png", "Annotation (hearts_pop)"),
    (6.0, "frame_4_reaction_gesture.png", "Arm gesture (open_hand)"),
    (12.0, "frame_5_visual_vector.png", "Annotation (octopus_vector)"),
    (20.0, "frame_6_blue_blood.png", "Visual (blue_blood_drop)"),
]


def extract_frame(video_path: Path, timestamp_sec: float, output_path: Path):
    """Extracts a single frame from video at timestamp using ffmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp_sec:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed at {timestamp_sec}s: {res.stderr}")


def get_video_metadata(video_path: Path) -> dict:
    """Reads duration, frame count, fps, width, height using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames:format=duration",
        "-of", "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
    data = json.loads(res.stdout)
    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})

    r_fps = stream.get("r_frame_rate", "30/1")
    if "/" in r_fps:
        num, den = map(int, r_fps.split("/"))
        fps = round(num / den)
    else:
        fps = int(float(r_fps))

    duration = float(fmt.get("duration", 0.0))
    nb_frames_str = stream.get("nb_frames")
    if nb_frames_str and nb_frames_str.isdigit():
        nb_frames = int(nb_frames_str)
    else:
        nb_frames = round(duration * fps)

    return {
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "fps": fps,
        "duration": duration,
        "nb_frames": nb_frames,
    }


def render_test_video(output_dir: Path, workers: int | None = None, fast: bool = False) -> tuple[Path, float]:
    """Runs the full pipeline on standard test brief and returns (video_path, elapsed_seconds)."""
    from toonshorts.core.pipeline import run_pipeline_from_brief
    from toonshorts.brief import load_brief

    output_dir.mkdir(parents=True, exist_ok=True)
    brief = load_brief(BRIEF_PATH)

    start_t = time.time()
    result = run_pipeline_from_brief(
        brief_source=brief,
        output_dir=output_dir,
        auto_confirm=True,
        keep_temp=False,
        fast=fast,
        workers=workers,
    )
    elapsed = time.time() - start_t
    video_path = result.get("video")
    if not video_path or not Path(video_path).is_file():
        raise RuntimeError(f"Pipeline did not produce valid video: {video_path}")
    return Path(video_path), elapsed


def create_baseline(baseline_dir: Path = BASELINE_DIR):
    """Renders test video and initializes the baseline folder."""
    baseline_dir.mkdir(parents=True, exist_ok=True)
    print(f"[Baseline] Rendering standard test video to {baseline_dir}...")
    video_path, elapsed = render_test_video(baseline_dir)

    target_video = baseline_dir / "baseline.mp4"
    if video_path != target_video:
        shutil.copy2(video_path, target_video)

    meta = get_video_metadata(target_video)
    meta["render_time_seconds"] = round(elapsed, 2)

    meta_file = baseline_dir / "baseline_metadata.json"
    meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[Baseline] Render time: {elapsed:.2f}s | Duration: {meta['duration']:.2f}s | Frames: {meta['nb_frames']}")

    # Extract reference frames
    print("[Baseline] Extracting reference frames...")
    frames_dir = baseline_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for ts, fname, desc in REFERENCE_TIMESTAMPS:
        out_f = frames_dir / fname
        extract_frame(target_video, ts, out_f)
        print(f"  - Extracted {fname} at {ts:.2f}s ({desc})")

    print(f"[Baseline] Baseline created successfully in {baseline_dir}!")


def compare_against_baseline(
    test_video_path: Path,
    baseline_dir: Path = BASELINE_DIR,
    max_mean_diff_threshold: float = 2.0,
) -> bool:
    """Compares test video against baseline frames, duration, and frame count."""
    meta_file = baseline_dir / "baseline_metadata.json"
    if not meta_file.exists():
        print(f"ERROR: Baseline metadata not found at {meta_file}. Run with --init-baseline first.")
        return False

    baseline_meta = json.loads(meta_file.read_text(encoding="utf-8"))
    test_meta = get_video_metadata(test_video_path)

    print("=======================================================")
    print("             BASELINE COMPARISON REPORT                ")
    print("=======================================================")
    print(f"Baseline: Duration={baseline_meta['duration']:.2f}s, Frames={baseline_meta['nb_frames']}, RenderTime={baseline_meta.get('render_time_seconds', 'N/A')}s")
    print(f"Current:  Duration={test_meta['duration']:.2f}s, Frames={test_meta['nb_frames']}")

    passed = True

    # 1. Duration check (within 0.1s tolerance)
    dur_diff = abs(test_meta["duration"] - baseline_meta["duration"])
    if dur_diff > 0.15:
        print(f"[FAIL] Duration mismatch: {test_meta['duration']:.2f}s vs baseline {baseline_meta['duration']:.2f}s (diff: {dur_diff:.3f}s)")
        passed = False
    else:
        print(f"[PASS] Duration match (diff: {dur_diff:.3f}s)")

    # 2. Frame count check (within 2 frames)
    frame_diff = abs(test_meta["nb_frames"] - baseline_meta["nb_frames"])
    if frame_diff > 2:
        print(f"[FAIL] Frame count mismatch: {test_meta['nb_frames']} vs baseline {baseline_meta['nb_frames']} (diff: {frame_diff})")
        passed = False
    else:
        print(f"[PASS] Frame count match: {test_meta['nb_frames']} vs baseline {baseline_meta['nb_frames']}")

    # 3. Reference frame pixel comparisons
    temp_frames_dir = test_video_path.parent / "extracted_frames"
    temp_frames_dir.mkdir(parents=True, exist_ok=True)
    baseline_frames_dir = baseline_dir / "frames"

    print("\n--- Per-Frame Image Difference ---")
    for ts, fname, desc in REFERENCE_TIMESTAMPS:
        base_frame_path = baseline_frames_dir / fname
        if not base_frame_path.exists():
            print(f"[FAIL] Missing baseline reference frame: {fname}")
            passed = False
            continue

        test_frame_path = temp_frames_dir / fname
        extract_frame(test_video_path, ts, test_frame_path)

        with Image.open(base_frame_path) as b_img, Image.open(test_frame_path) as t_img:
            b_arr = np.array(b_img.convert("RGBA"), dtype=np.float32)
            t_arr = np.array(t_img.convert("RGBA"), dtype=np.float32)

            if b_arr.shape != t_arr.shape:
                print(f"[FAIL] {fname} ({desc}): Shape mismatch {t_arr.shape} vs {b_arr.shape}")
                passed = False
                continue

            diff = np.abs(b_arr - t_arr)
            max_d = float(np.max(diff))
            mean_d = float(np.mean(diff))

            status = "PASS" if mean_d <= max_mean_diff_threshold else "FAIL"
            if status == "FAIL":
                passed = False
            print(f"[{status}] {fname:30s} ({desc}): MeanDiff={mean_d:.3f}, MaxDiff={max_d:.1f}")

    print("=======================================================")
    if passed:
        print("OVERALL RESULT: PASS")
    else:
        print("OVERALL RESULT: FAIL")
    print("=======================================================")
    return passed


def main():
    parser = argparse.ArgumentParser(description="ToonShorts Baseline Comparison")
    parser.add_argument("--init-baseline", action="store_true", help="Render and store initial baseline")
    parser.add_argument("--video", type=str, default=None, help="Existing video path to compare against baseline")
    parser.add_argument("--workers", type=int, default=None, help="Number of render workers")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_TEST_DIR), help="Output dir for rendered video")
    parser.add_argument("--max-diff", type=float, default=2.0, help="Max allowed mean pixel diff")
    args = parser.parse_args()

    if args.init_baseline:
        create_baseline()
        sys.exit(0)

    if args.video:
        video_path = Path(args.video)
    else:
        print(f"Rendering standard test video into {args.output_dir} (workers={args.workers})...")
        video_path, elapsed = render_test_video(Path(args.output_dir), workers=args.workers)
        print(f"Render completed in {elapsed:.2f}s: {video_path}")

    ok = compare_against_baseline(video_path, max_mean_diff_threshold=args.max_diff)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
