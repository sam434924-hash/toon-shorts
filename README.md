# ToonShorts

An automated end-to-end Python pipeline for creating short, funny, animated vertical videos (9:16, 1080x1920) for YouTube Shorts in multiple artistic styles.

## Supported Styles (`styles/*.json`)
1. **stickman**: Procedurally drawn in code with Pillow (100% consistent, zero API cost).
2. **crayon**: Gemini Imagen styled wax crayon drawing on construction paper.
3. **paper_cutout**: Layered papercraft stop-motion collage with drop shadows.
4. **pixel_art**: 16-bit retro arcade pixel sprites.
5. **chalkboard**: Dusty chalk classroom illustration on dark slate blackboard.

## Installation
```bash
pip install -r requirements.txt
```

## Configuration
Copy `.env.example` to `.env` and set your API key:
```bash
cp .env.example .env
```
Add your key inside `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Usage
Run the CLI to make a vertical short video:
```bash
python -m toonshorts make --style stickman --topic "The Missing Semicolon"
python -m toonshorts make --style crayon --topic "Dragon Ice Cream" --yes
```

## Running Tests
```bash
python -m pytest tests
```
