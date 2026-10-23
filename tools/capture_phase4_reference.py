"""
Captures fresh reference set of raw browser frames for ALL scenes before Phase 4.
Covering:
- Camera punch-in (start, mid, peak, decay, baseline)
- Arm gestures (anticipation, raise, hold, return, idle)
- Annotations (before, mid-draw, completed)
- Steady-state reference frames outside transition zones
Saves to baseline/raw_reference/ and copies to baseline/raw_reference_backup/.
"""

import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from toonshorts.plugins.render.animejs.capture import derive_scene_seed

BASE_DIR = Path("temp/render_octopus_v2_full_pipeline")
T_DIR = Path("src/toonshorts/plugins/render/animejs/templates")
REF_DIR = Path("baseline/raw_reference")
BACKUP_DIR = Path("baseline/raw_reference_backup")

REF_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

rough_js = (T_DIR / "rough_draw.js").read_text(encoding="utf-8")
stage_js = (T_DIR / "stage_visuals.js").read_text(encoding="utf-8")
cam_js = (T_DIR / "camera_engine.js").read_text(encoding="utf-8")
gest_js = (T_DIR / "gestures_fk.js").read_text(encoding="utf-8")
main_js = (T_DIR / "main.js").read_text(encoding="utf-8")

modular_tags = (
    "  </script>\n"
    "  <script id=\"module-rough-draw\">\n" + rough_js + "\n  </script>\n"
    "  <script id=\"module-stage-visuals\">\n" + stage_js + "\n  </script>\n"
    "  <script id=\"module-camera-engine\">\n" + cam_js + "\n  </script>\n"
    "  <script id=\"module-gestures-fk\">\n" + gest_js + "\n  </script>\n"
    "  <script id=\"module-main\">\n" + main_js + "\n  </script>\n"
    "  <script>\n"
)

# Key timestamps per scene
SCENE_TIMESTAMPS = {
    1: [
        50, 150, 200, 350, 500, 1000, 1400, 1650, 1700, 1900, 2100,
        2280, 2450, 2500, 2600, 2750, 3000, 3380, 3480, 3580, 3780,
        3980, 4200, 4500, 4700
    ],
    2: [
        50, 150, 200, 350, 700, 1060, 1180, 1250, 1280, 1380, 1580,
        1600, 1800, 1900, 2000, 2100, 2300, 2500, 2880, 2920, 3080,
        3150, 3500, 4000, 4500, 5000
    ],
    3: [
        50, 150, 200, 350, 800, 1000, 1500, 1800, 2000, 2920, 3120,
        3340, 3550, 4000, 5000, 5140, 5320, 5340, 5530, 6000, 6880,
        7050
    ],
    4: [
        50, 150, 200, 350, 600, 1000, 1400, 1800, 2040, 2140, 2240,
        2300, 2440, 2500, 2620, 2720, 2820, 2830, 3020, 3200, 3500,
        4080, 4270, 4340, 4540, 4620, 4830, 5200, 5800, 6300
    ],
}

def main():
    print("Capturing Phase 4 reference raw frames from current code...")
    temp_html_dir = Path("temp/phase4_reference_html")
    temp_html_dir.mkdir(parents=True, exist_ok=True)

    manifest = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})

        for s_idx, timestamps in SCENE_TIMESTAMPS.items():
            base_html = (BASE_DIR / f"scene_{s_idx}_tmp" / "whiteboard_scene.html").read_text(encoding="utf-8")
            marker_start = "// Store stroke drawing items for progressive animated line drawing"
            marker_end = "window.seekTo = window.seekAnimation;"
            idx_start = base_html.index(marker_start)
            idx_end = base_html.index(marker_end) + len(marker_end)

            r_seed = derive_scene_seed(s_idx)
            mod_html = (
                base_html[:idx_start]
                + f"window.__roughSeed = {r_seed};\nwindow.__isFast = false;\n"
                + modular_tags
                + base_html[idx_end:]
            )
            html_file = temp_html_dir / f"scene_{s_idx}.html"
            html_file.write_text(mod_html, encoding="utf-8")

            page.goto(html_file.resolve().as_uri())

            for ts in timestamps:
                page.evaluate(f"window.seekTo({ts})")
                frame_bytes = page.screenshot(type="png")
                filename = f"sc{s_idx}_t{ts}ms.png"
                ref_path = REF_DIR / filename
                ref_path.write_bytes(frame_bytes)
                backup_path = BACKUP_DIR / filename
                backup_path.write_bytes(frame_bytes)

            manifest[s_idx] = timestamps
            print(f"Scene {s_idx}: captured {len(timestamps)} frames.")

        browser.close()

    manifest_file = REF_DIR / "timestamps_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (BACKUP_DIR / "timestamps_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    total_frames = sum(len(ts) for ts in SCENE_TIMESTAMPS.values())
    print(f"\nSuccessfully captured {total_frames} reference frames to {REF_DIR} and {BACKUP_DIR}.")

if __name__ == "__main__":
    main()
