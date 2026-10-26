"""
Purpose: ASS subtitle generation with security escaping and word highlighting.
Inputs: Script plan, scene audio timing objects, and subtitle style config.
Outputs: ASS format subtitle file with word-by-word karaoke highlights.
Depends on: core.models, pathlib, typing
Used by: core.assembler, subtitles
Config keys: None
Tests: tests/unit/test_escaping.py
"""

from pathlib import Path
from typing import List, Dict, Any
from .models import ScriptPlan, SceneAudio, strip_speaker_label


def escape_ass_text(text: str) -> str:
    """Strictly escapes raw model text to prevent ASS injection or formatting corruption."""
    if not text:
        return ""
    text = strip_speaker_label(text)
    # 1. Neutralize backslashes (ASS override control prefix)
    sanitized = text.replace("\\", "/")
    # 2. Neutralize braces (ASS tag delimiters) with fullwidth unicode equivalents
    sanitized = sanitized.replace("{", "｛").replace("}", "｝")
    # 3. Neutralize percent signs (format string safety)
    sanitized = sanitized.replace("%", "％")
    # 4. Remove carriage returns and raw newlines
    sanitized = sanitized.replace("\r", " ").replace("\n", " ")
    return sanitized.strip()


def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS timestamp format: H:MM:SS.cs (centiseconds)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def generate_ass_subtitles(
    plan: ScriptPlan,
    scene_audios: List[SceneAudio],
    style_preset: Dict[str, Any],
    output_path: Path,
):
    """Generates a complete ASS subtitle file with rapid phone-optimized word highlighting."""
    caption_cfg = style_preset.get("caption", {})
    font_name = caption_cfg.get("font", "Arial")
    font_size = caption_cfg.get("font_size", 72)
    primary_color = caption_cfg.get("primary_color", "&H00FFFFFF")
    outline_color = caption_cfg.get("outline_color", "&H00111111")
    highlight_color = caption_cfg.get("highlight_color", "&H0000D8F6")
    alignment = caption_cfg.get("alignment", 8)
    default_margin = 120 if alignment == 8 else 420
    margin_v = caption_cfg.get("margin_v", default_margin)
    outline_width = caption_cfg.get("outline_width", 6)
    shadow = caption_cfg.get("shadow", 3)
    border_style = caption_cfg.get("border_style", 3 if style_preset.get("name") == "night_studio" else 1)
    back_color = caption_cfg.get("back_color", "&H60050811" if style_preset.get("name") == "night_studio" else "&H80000000")

    ass_header = f"""[Script Info]
Title: ToonShorts Captions
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},{back_color},-1,0,0,0,100,100,0,0,{border_style},{outline_width},{shadow},{alignment},60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    current_timeline = 0.0

    for i, audio in enumerate(scene_audios):
        scene_start = current_timeline
        words = audio.word_timings

        if not words:
            scene_text = escape_ass_text(plan.scenes[i].dialogue_line)
            t_start = format_ass_time(scene_start)
            t_end = format_ass_time(scene_start + audio.duration_seconds)
            dialogue_lines.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{scene_text}")
        else:
            phrase_chunk_size = 8
            for chunk_idx in range(0, len(words), phrase_chunk_size):
                chunk = words[chunk_idx:chunk_idx + phrase_chunk_size]
                chunk_escaped = [escape_ass_text(w.word) for w in chunk]
                split_at = len(chunk) // 2 if len(chunk) > 4 else -1

                for word_pos, active_word in enumerate(chunk):
                    w_start = format_ass_time(scene_start + active_word.start_time)
                    w_end = format_ass_time(scene_start + active_word.end_time)

                    formatted_words = []
                    for j, txt in enumerate(chunk_escaped):
                        if j == word_pos:
                            formatted_words.append(f"{{\\c{highlight_color}\\b1}}{txt}{{\\c{primary_color}\\b1}}")
                        else:
                            formatted_words.append(txt)

                    if split_at > 0:
                        line1 = " ".join(formatted_words[:split_at])
                        line2 = " ".join(formatted_words[split_at:])
                        line_text = f"{line1}\\N{line2}"
                    else:
                        line_text = " ".join(formatted_words)

                    dialogue_lines.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{line_text}")

        current_timeline += audio.scene_total_duration

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for d in dialogue_lines:
            f.write(d + "\n")
