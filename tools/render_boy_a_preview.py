"""
Renders boy_a states using Playwright to preview images and a contact sheet.
"""
from pathlib import Path
import re
from PIL import Image
from playwright.sync_api import sync_playwright

def render_previews():
    svg_path = Path("assets/2d/characters/boy_a/character.svg")
    svg_content = svg_path.read_text(encoding="utf-8")

    out_dir = Path("output/stage_character/boy_a")
    out_dir.mkdir(parents=True, exist_ok=True)

    states = [
        ("r1_c0_mouth_closed", "open", "closed"),
        ("r1_c1_mouth_slightly_open", "open", "slightly_open"),
        ("r2_c0_mouth_wide_open", "open", "wide_open"),
        ("r2_c1_mouth_round_o", "open", "round_o"),
        ("r3_c0_neutral_open", "open", "closed"),
        ("r3_c1_eyes_blink", "blink", "closed"),
        ("r4_c0_eyes_screen_left", "screen_left", "closed"),
        ("r4_c1_eyes_screen_right", "screen_right", "closed"),
    ]

    rendered_images = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 560, "height": 630})
        for name, eye, mouth in states:
            custom_style = f"""
            .eye-state {{ display: none !important; }}
            .mouth-state {{ display: none !important; }}
            #eyes-{eye} {{ display: inline !important; }}
            #mouth-{mouth} {{ display: inline !important; }}
            """
            styled_svg = re.sub(r"<style>.*?</style>", f"<style>{custom_style}</style>", svg_content, flags=re.DOTALL)
            html = f"""<!DOCTYPE html>
            <html>
            <body style="margin:0; padding:0; background: #ffffff; display: flex; justify-content: center; align-items: center;">
            {styled_svg}
            </body>
            </html>"""
            page.set_content(html)
            out_png = out_dir / f"{name}.png"
            page.screenshot(path=str(out_png))
            print(f"Rendered {name} -> {out_png}")
            rendered_images.append(out_png)
        browser.close()

    # Create a 4x2 contact sheet matching the reference sheet
    sheet_w = 560 * 2
    sheet_h = 630 * 4
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 255, 255))
    for idx, img_path in enumerate(rendered_images):
        row = idx // 2
        col = idx % 2
        im = Image.open(img_path)
        sheet.paste(im, (col * 560, row * 630))

    contact_path = out_dir / "boy_a_contact_sheet.png"
    sheet.save(contact_path)
    print(f"Saved contact sheet to {contact_path}")

if __name__ == "__main__":
    render_previews()
