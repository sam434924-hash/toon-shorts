# ToonShorts

An automated end-to-end Python pipeline for creating short, funny, animated vertical videos (9:16, 1080x1920) for YouTube Shorts in multiple artistic styles.

## Project Path
`C:\dev\toon-shorts`

## Supported Styles (`src/toonshorts/styles/*.json`)
1. **stickman**: Minimalist 2D vector stick figure animation drawn in Pycairo with hierarchical skeleton, squash & stretch, contact shadows, and hand-drawn room background (100% consistent, zero API cost).
2. **whiteboard**: Clean modern whiteboard explainer video powered by Anime.js, Rough.js progressive stroke drawing, and Playwright.
3. **crayon**: Gemini Imagen styled wax crayon drawing on construction paper.
4. **paper_cutout**: Layered papercraft stop-motion collage with drop shadows.
5. **pixel_art**: 16-bit retro arcade pixel sprites.
6. **chalkboard**: Dusty chalk classroom illustration on dark slate blackboard.

## Render Plugins (`src/toonshorts/plugins/render/`)
- **cairo**: 2D vector stickman rendering engine implemented in Pycairo.
- **animejs**: HTML/SVG whiteboard animation rendering engine using Anime.js, Rough.js, and headless browser.
- **blender3d**: 3D headless Blender rendering engine for RobotExpressive robot character with validated built-in actions.
- **gemini**: AI image generation renderer powered by Google Imagen.
- **pillow**: Procedural stickman rendering engine implemented in Pillow.
- **fake**: Rapid offline mock rendering plugin generating valid image frames.

## 2D Layered Character System (`assets/2d/characters/stick_hoodie/`)
- A modular sliced 2D body-parts character pack with transparent layers (hoodie torso, head, expressions, articulated limbs).
- Managed by `src/toonshorts/core/character2d.py` and demo tool `tools/build_2d_hoodie_video.py`.
- Reusable asset pack (not yet connected to the main CLI pipeline).

## Prerequisites
- Python 3.11 (`py -3.11`)
- FFmpeg on PATH with `subtitles` filter enabled
- Blender (optional, for 3D robot rendering via `blender3d`)

## Installation
```bash
cd C:\dev\toon-shorts
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## Configuration
Copy `.env.example` to `.env` and set your API key:
```bash
copy .env.example .env
```
Add your key inside `.env`:
```env
GEMINI_API_KEY=your-key-here
```

## Usage
Run the CLI to make a vertical short video:
```bash
python -m toonshorts make --style stickman --topic "The Missing Semicolon"
python -m toonshorts make --style whiteboard --topic "What is an API" --yes
python -m toonshorts make --style crayon --topic "Dragon Ice Cream" --yes
```
Or use the console entry point:
```bash
toonshorts make --style stickman --topic "The Missing Semicolon"
```

## Running Tests
```bash
pytest
```
