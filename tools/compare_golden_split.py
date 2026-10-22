"""
Renders the split animejs package against golden baseline and calculates pixel differences.
"""

from pathlib import Path
import numpy as np
from PIL import Image

from tools.render_golden_baseline import run_baseline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = PROJECT_ROOT / "output" / "pack_tests" / "golden"
SPLIT_DIR = PROJECT_ROOT / "output" / "pack_tests" / "split_test"


def compare_frames():
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    print("Rendering split test frames...")
    run_baseline(SPLIT_DIR)

    frame_names = [
        "test2_s1_start.png",
        "test2_s1_mid.png",
        "test2_s1_end.png",
        "test2_s2_start.png",
        "test2_s2_mid.png",
        "test2_s2_end.png",
    ]

    all_matched = True
    print("\n--- Golden vs Split Frame Comparison ---")
    for name in frame_names:
        g_path = GOLDEN_DIR / name
        s_path = SPLIT_DIR / name

        if not g_path.exists() or not s_path.exists():
            print(f"FAILED: Missing frame {name}")
            all_matched = False
            continue

        with Image.open(g_path) as g_img, Image.open(s_path) as s_img:
            g_arr = np.array(g_img.convert("RGBA"), dtype=np.float32)
            s_arr = np.array(s_img.convert("RGBA"), dtype=np.float32)

            if g_arr.shape != s_arr.shape:
                print(f"FAILED {name}: Dimension mismatch {g_arr.shape} vs {s_arr.shape}")
                all_matched = False
                continue

            diff = np.abs(g_arr - s_arr)
            max_diff = float(np.max(diff))
            mean_diff = float(np.mean(diff))

            print(f"Frame {name:20s}: Max Diff = {max_diff:.1f}, Mean Diff = {mean_diff:.4f}")
            # Max difference should be tiny (video compression / anti-aliasing tolerance < 5.0)
            if mean_diff > 1.0:
                all_matched = False

    if all_matched:
        print("\nSUCCESS: All 6 frames match golden baseline within tolerance!")
    else:
        print("\nWARNING: Some frames exceeded mismatch tolerance.")


if __name__ == "__main__":
    compare_frames()
