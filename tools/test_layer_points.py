"""
Tests which layers color pixel (160, 180).
"""
from xml.etree import ElementTree as ET
from playwright.sync_api import sync_playwright
from PIL import Image

tree = ET.parse("assets/2d/characters/boy_a/character.svg")
root = tree.getroot()
ns = {"svg": "http://www.w3.org/2000/svg"}

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 560, "height": 630})
    for g in root.findall(".//svg:g", ns):
        gid = g.attrib.get("id", "")
        if not gid.startswith("layer-"):
            continue
        g_xml = ET.tostring(g, encoding="unicode")
        svg_doc = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:white">
<svg viewBox="0 0 560 630" width="560" height="630" xmlns="http://www.w3.org/2000/svg">
{g_xml}
</svg>
</body>
</html>"""
        page.set_content(svg_doc)
        page.screenshot(path="temp_l.png")
        im = Image.open("temp_l.png").convert("RGB")
        c = im.getpixel((160, 180))
        if c != (255, 255, 255):
            print(f"Layer {gid}: color at (160, 180) = {c}")
    browser.close()
