"""
Purpose: Generates a 12-frame composite filmstrip PNG across a scene for visual review.
Inputs: Scene metadata, board objects, camera shot plan, and multiplane depth styling.
Outputs: Single stitched PNG filmstrip in baseline/phase4b/filmstrip_scene1.png.
Depends on: io, numpy, pathlib, PIL, playwright, toonshorts.core.config, toonshorts.plugins.render.animejs.html_builder
Used by: tools
Config keys: None
Tests: None
"""

from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

from toonshorts.core import config
from toonshorts.plugins.render.animejs.html_builder import generate_whiteboard_html

ROOT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT_DIR / "baseline" / "phase4b"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_filmstrip(
    scene_number: int = 1,
    duration_sec: float = 5.0,
    num_frames: int = 12,
    output_filename: str = "filmstrip_scene1.png",
):
    print(f"Generating {num_frames}-frame filmstrip for Scene {scene_number}...")

    board_objs = [
        {
            "id": f"filmstrip-obj-1",
            "type": "highlight_word",
            "anchor": 800,
            "exit_time": 4500,
            "board_slot": "slot_top",
            "data": {"text": "How APIs Work", "target_word": "APIs"},
        },
        {
            "id": f"filmstrip-obj-2",
            "type": "diagram_flow",
            "anchor": 1800,
            "exit_time": 4800,
            "board_slot": "slot_mid",
            "data": {"nodes": ["Client", "Server"], "arrows": ["Request", "Response"]},
        },
    ]

    word_timings = [
        {"word": "How", "start_time": 0.5, "end_time": 0.8},
        {"word": "APIs", "start_time": 0.8, "end_time": 1.2},
        {"word": "Work", "start_time": 1.2, "end_time": 1.6},
        {"word": "request", "start_time": 2.2, "end_time": 2.6},
        {"word": "response", "start_time": 3.2, "end_time": 3.7},
    ]

    html_code = generate_whiteboard_html(
        title="Phase 4B Filmstrip Review",
        words=[{"text": "How APIs Work", "start_ms": 800, "duration_ms": 600}],
        duration_sec=duration_sec,
        scene_number=scene_number,
        board_objects=board_objs,
        word_timings=word_timings,
        theme="whiteboard",
        fps=30,
    )

    temp_html = ROOT_DIR / "temp" / f"filmstrip_scene_{scene_number}.html"
    temp_html.parent.mkdir(parents=True, exist_ok=True)
    temp_html.write_text(html_code, encoding="utf-8")

    total_ms = int(duration_sec * 1000)
    timestamps = [int(i * (total_ms / (num_frames - 1))) for i in range(num_frames)]

    thumb_w = 270
    thumb_h = 480
    cols = 4
    rows = 3
    filmstrip_img = Image.new("RGBA", (cols * thumb_w, rows * thumb_h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(filmstrip_img)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        page.goto(temp_html.resolve().as_uri())

        for idx, ts in enumerate(timestamps):
            page.evaluate(f"window.seekTo({ts})")
            buf = page.screenshot(type="png")
            frame_img = Image.open(BytesIO(buf)).convert("RGBA")
            frame_thumb = frame_img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)

            col = idx % cols
            row = idx // cols
            x = col * thumb_w
            y = row * thumb_h

            filmstrip_img.paste(frame_thumb, (x, y))

            # Draw timestamp badge
            badge_text = f"#{idx+1}: {ts}ms"
            draw.rectangle([x + 8, y + 8, x + 110, y + 32], fill=(0, 0, 0, 180))
            draw.text((x + 14, y + 12), badge_text, fill=(56, 189, 248, 255))

        browser.close()

    out_path = OUT_DIR / output_filename
    filmstrip_img.save(out_path, format="PNG")
    print(f"Saved {num_frames}-frame filmstrip to {out_path} ({out_path.stat().st_size} bytes)")
    return out_path


if __name__ == "__main__":
    generate_filmstrip(scene_number=1, output_filename="filmstrip_scene1.png")
