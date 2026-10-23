"""
Verifies bit-for-bit raw browser frame determinism between pre-split monolithic script and modular split templates.
"""

from pathlib import Path
import subprocess
from io import BytesIO
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

# Load original pre-split monolithic script.js directly from git commit 0192ec7
orig_script_js = subprocess.run(
    ["git", "show", "0192ec7:src/toonshorts/plugins/render/animejs/templates/script.js"],
    capture_output=True,
    text=True,
    check=True,
).stdout

base_dir = Path("temp/render_octopus_v2_full_pipeline")
t_dir = Path("src/toonshorts/plugins/render/animejs/templates")

rough_js = (t_dir / "rough_draw.js").read_text(encoding="utf-8")
stage_js = (t_dir / "stage_visuals.js").read_text(encoding="utf-8")
cam_js = (t_dir / "camera_engine.js").read_text(encoding="utf-8")
gest_js = (t_dir / "gestures_fk.js").read_text(encoding="utf-8")
main_js = (t_dir / "main.js").read_text(encoding="utf-8")

modular_tags = (
    "  </script>\n"
    "  <script id=\"module-rough-draw\">\n"
    + rough_js
    + "\n  </script>\n"
    "  <script id=\"module-stage-visuals\">\n"
    + stage_js
    + "\n  </script>\n"
    "  <script id=\"module-camera-engine\">\n"
    + cam_js
    + "\n  </script>\n"
    "  <script id=\"module-gestures-fk\">\n"
    + gest_js
    + "\n  </script>\n"
    "  <script id=\"module-main\">\n"
    + main_js
    + "\n  </script>\n"
    "  <script>\n"
)

test_points = {
    1: [500, 1500, 2500, 3500, 4500],
    2: [500, 2000, 3500, 5000],
    3: [500, 2000, 3500, 5000, 6000],
    4: [500, 2000, 3500, 5000, 6000],
}

test_dir = Path("temp/verify_split")
test_dir.mkdir(parents=True, exist_ok=True)

total_comparisons = 0
max_overall_diff = 0
sum_overall_diff = 0

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    for s_idx, timestamps in test_points.items():
        base_html = (base_dir / f"scene_{s_idx}_tmp" / "whiteboard_scene.html").read_text(encoding="utf-8")
        marker_start = "// Store stroke drawing items for progressive animated line drawing"
        marker_end = "window.seekTo = window.seekAnimation;"
        idx_start = base_html.index(marker_start)
        idx_end = base_html.index(marker_end) + len(marker_end)

        # Monolithic HTML
        orig_html = base_html[:idx_start] + orig_script_js + base_html[idx_end:]
        orig_file = test_dir / f"scene_{s_idx}_monolithic.html"
        orig_file.write_text(orig_html, encoding="utf-8")

        # Modular HTML
        mod_html = base_html[:idx_start] + modular_tags + base_html[idx_end:]
        mod_file = test_dir / f"scene_{s_idx}_modular.html"
        mod_file.write_text(mod_html, encoding="utf-8")

        p_orig = browser.new_page(viewport={"width": 1080, "height": 1920})
        p_mod = browser.new_page(viewport={"width": 1080, "height": 1920})

        p_orig.goto(orig_file.resolve().as_uri())
        p_mod.goto(mod_file.resolve().as_uri())

        missing = p_mod.evaluate("window.__checkModulesLoaded()")
        assert missing == [], f"Missing modules in scene {s_idx}: {missing}"

        for ts in timestamps:
            p_orig.evaluate(f"window.seekTo({ts})")
            buf_orig = p_orig.screenshot(type="png")

            p_mod.evaluate(f"window.seekTo({ts})")
            buf_mod = p_mod.screenshot(type="png")

            img_orig = Image.open(BytesIO(buf_orig)).convert("RGBA")
            arr_orig = np.array(img_orig, dtype=np.int16)

            img_mod = Image.open(BytesIO(buf_mod)).convert("RGBA")
            arr_mod = np.array(img_mod, dtype=np.int16)

            diff = np.abs(arr_orig - arr_mod)
            max_d = int(diff.max())
            sum_d = int(diff.sum())
            total_comparisons += 1
            max_overall_diff = max(max_overall_diff, max_d)
            sum_overall_diff += sum_d
            print(f"Scene {s_idx} @ {ts}ms diff: max={max_d}, sum={sum_d}")
            assert max_d == 0 and sum_d == 0, f"Difference detected in scene {s_idx} at {ts}ms: max={max_d}, sum={sum_d}"

        p_orig.close()
        p_mod.close()

    browser.close()

print(f"\nALL {total_comparisons} FRAMES ACROSS ALL 4 SCENES COMPARED:")
print(f"Overall Max Diff: {max_overall_diff}")
print(f"Overall Sum Diff: {sum_overall_diff}")
if max_overall_diff == 0 and sum_overall_diff == 0:
    print("VERIFICATION RESULT: BIT-FOR-BIT IDENTICAL (diff max=0, sum=0)")
else:
    raise AssertionError("Modular split differs from monolithic original!")
