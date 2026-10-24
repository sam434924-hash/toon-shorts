import json
import math
from pathlib import Path
from PIL import Image
import numpy as np
from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.core.models import Scene, Character
from toonshorts.plugins.render.animejs.cast import build_characters_data, resolve_scene_cast
from toonshorts.plugins.render.animejs.annotations import extract_whiteboard_content_and_annotations
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html
from toonshorts.core.camera import plan_scene_camera_shots
from toonshorts.core.pipeline import load_style_preset

def main():
    scene_json_path = Path("briefs/octopus_facts_v2_scene.json")
    with open(scene_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes_raw = data.get("scenes", [])
    characters = [Character(name="boy_b", visual_description="Character boy_b"), Character(name="girl_a", visual_description="Character girl_a")]
    preset = load_style_preset("night_studio")

    output_dir = Path("output/stills")
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})

        for sc_data in scenes_raw:
            scene = Scene.model_validate(sc_data)
            sc_num = scene.scene_number
            wts = scene.word_timings or []
            max_end = max((wt.end_time for wt in wts), default=3.0)
            dur = max_end + 0.5

            shots = plan_scene_camera_shots(
                duration_sec=dur,
                word_timings=wts,
                speaker_id=scene.speaker,
                speaker_slot="right" if scene.speaker == "girl_a" else "left",
                scene_number=sc_num,
            )

            title, words_data, annotations = extract_whiteboard_content_and_annotations(scene, dur)
            scene_cast = resolve_scene_cast(scene, characters)
            chars_data = build_characters_data(scene_cast, scene=scene, style_preset=preset)

            html = generate_whiteboard_html(
                title=title,
                words=words_data,
                duration_sec=dur,
                mouth_cues=[False] * int(dur * config.VIDEO_FPS),
                gesture=scene.gesture or "idle",
                width=config.VIDEO_WIDTH,
                height=config.VIDEO_HEIGHT,
                scene_number=sc_num,
                annotations=annotations,
                characters_data=chars_data,
                layout="cards",
                word_timings=wts,
                theme="night_studio",
                camera_shots=shots,
                fast=True,
            )

            html_path = output_dir / f"test_scene_{sc_num}.html"
            html_path.write_text(html, encoding="utf-8")
            page.goto(html_path.resolve().as_uri())

            # Key test timestamps for transition and hold
            if sc_num in (3, 4):
                test_times = [0, 175, 350, 2000, 3500, 6175, 6350]
            elif sc_num == 2:
                test_times = [0, 175, 350, 1500, 2500, 3500]
            else:
                test_times = [0, 175, 350, 1500, 2500, 4000]

            for t_ms in test_times:
                # 1. Ensure characters visible, seek and take screenshot
                page.evaluate(f"""() => {{
                    document.querySelectorAll('.char-slot-left, .char-slot-right').forEach(el => el.style.visibility = 'visible');
                    window.seekTo({t_ms});
                }}""")
                frame_path = output_dir / f"scene_{sc_num}_frame_{t_ms}ms.png"
                page.screenshot(path=str(frame_path))

                dom_info = page.evaluate("""() => {
                    const boyRoot = document.querySelector('#character-rig #character_root') || document.getElementById('character-rig');
                    const boyArm = document.querySelector('#character-rig #fk_arm_l');
                    const girlRoot = document.querySelector('#character-rig-right #character_root') || document.getElementById('character-rig-right');
                    const girlArm = document.querySelector('#character-rig-right #fk_arm_r');

                    let bLeft = Infinity, bRight = -Infinity;
                    if (boyRoot) {
                        const r = boyRoot.getBoundingClientRect();
                        if (r.width > 0) { bLeft = Math.min(bLeft, r.left); bRight = Math.max(bRight, r.right); }
                    }
                    if (boyArm) {
                        const r = boyArm.getBoundingClientRect();
                        if (r.width > 0) { bLeft = Math.min(bLeft, r.left); bRight = Math.max(bRight, r.right); }
                    }

                    let gLeft = Infinity, gRight = -Infinity;
                    if (girlRoot) {
                        const r = girlRoot.getBoundingClientRect();
                        if (r.width > 0) { gLeft = Math.min(gLeft, r.left); gRight = Math.max(gRight, r.right); }
                    }
                    if (girlArm) {
                        const r = girlArm.getBoundingClientRect();
                        if (r.width > 0) { gLeft = Math.min(gLeft, r.left); gRight = Math.max(gRight, r.right); }
                    }

                    return {
                        boy_bounds: [Math.round(bLeft), Math.round(bRight)],
                        girl_bounds: [Math.round(gLeft), Math.round(gRight)],
                        camState: window.__lastCameraState
                    };
                }""")

                # 2. Hide characters to capture background alone for exact pixel diff
                page.evaluate("""() => {
                    document.querySelectorAll('.char-slot-left, .char-slot-right').forEach(el => el.style.visibility = 'hidden');
                }""")
                bg_path = output_dir / f"temp_bg_{sc_num}_{t_ms}ms.png"
                page.screenshot(path=str(bg_path))

                im_char = np.array(Image.open(frame_path).convert("RGB"))
                im_bg = np.array(Image.open(bg_path).convert("RGB"))
                if bg_path.exists():
                    bg_path.unlink()

                diff = np.abs(im_char.astype(int) - im_bg.astype(int)).max(axis=2)
                char_mask = (diff > 8)

                # Boy is slot left (width 540 initially, but characters can move)
                boy_mask = np.zeros_like(char_mask)
                girl_mask = np.zeros_like(char_mask)

                # Use DOM partition or column threshold
                split_x = int(540 - dom_info["camState"].get("camX", 0))
                boy_mask[:, :split_x] = char_mask[:, :split_x]
                girl_mask[:, split_x:] = char_mask[:, split_x:]

                boy_cols = np.where(boy_mask.any(axis=0))[0]
                girl_cols = np.where(girl_mask.any(axis=0))[0]

                boy_pixel_min = int(boy_cols[0]) if len(boy_cols) > 0 else None
                boy_pixel_max = int(boy_cols[-1]) if len(boy_cols) > 0 else None

                girl_pixel_min = int(girl_cols[0]) if len(girl_cols) > 0 else None
                girl_pixel_max = int(girl_cols[-1]) if len(girl_cols) > 0 else None

                res_entry = {
                    "scene": sc_num,
                    "t_ms": t_ms,
                    "speaker": scene.speaker,
                    "gesture": scene.gesture,
                    "boy_dom": dom_info["boy_bounds"],
                    "girl_dom": dom_info["girl_bounds"],
                    "boy_pixels": [boy_pixel_min, boy_pixel_max],
                    "girl_pixels": [girl_pixel_min, girl_pixel_max],
                    "cam_zoom": dom_info["camState"].get("camZoom"),
                    "cam_x": dom_info["camState"].get("camX"),
                    "frame_path": str(frame_path),
                }
                results.append(res_entry)
                print(f"Scene {sc_num} @ {t_ms}ms: Boy Pixels={boy_pixel_min}..{boy_pixel_max} (DOM {dom_info['boy_bounds']}), Girl Pixels={girl_pixel_min}..{girl_pixel_max} (DOM {dom_info['girl_bounds']}), camX={dom_info['camState'].get('camX'):.1f}, zoom={dom_info['camState'].get('camZoom'):.2f}")

        browser.close()

    metrics_path = output_dir / "camera_framing_metrics.json"
    metrics_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved framing metrics to {metrics_path}")

if __name__ == "__main__":
    main()
