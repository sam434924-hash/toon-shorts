"""
Purpose: Kinetic words motion graphics plugin.
Inputs: Target word, trigger time, text phrase, and highlight color.
Outputs: Animated HTML and Anime.js keyframe animations for popping/sliding words.
Depends on: html, typing
Used by: plugins.graphics
Config keys: None
Tests: tests/unit/test_graphics_plugins.py
"""

import html
from typing import Any, Dict, List, Optional
from toonshorts.core.models import strip_speaker_label


class KineticWordsPlugin:
    """Plugin for kinetic word appearances with pop/slide animations and highlights."""
    name = "kinetic_words"

    @classmethod
    def render(
        cls,
        element_id: str,
        text: str,
        highlight_term: Optional[str] = None,
        highlight_color: str = "#38bdf8",
        start_ms: int = 0,
        duration_ms: int = 500,
        animation_type: str = "pop",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Builds HTML markup, CSS styling, and Anime.js animation descriptor for kinetic words.
        """
        clean_text = strip_speaker_label(text)
        words = clean_text.split()
        spans = []
        for idx, w in enumerate(words):
            clean = w.strip(".,!?:;\"'").lower()
            is_highlight = highlight_term and (clean == highlight_term.lower() or highlight_term.lower() in clean)
            escaped_word = html.escape(w)
            color_style = f"color: {highlight_color}; font-weight: 900;" if is_highlight else "color: #f8fafc;"
            spans.append(
                f'<span class="kw-word kw-word-{idx}" style="{color_style}">{escaped_word}</span>'
            )

        html_markup = (
            f'<div id="{element_id}" class="kinetic-words-container kw-anim-{animation_type}">\n'
            f'  <div class="kw-inner">{" ".join(spans)}</div>\n'
            f'</div>'
        )

        css_rules = f"""
#{element_id} {{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  margin: 12px 0;
  opacity: 0;
  will-change: transform, opacity;
}}
#{element_id} .kw-inner {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 44px;
  line-height: 1.25;
  letter-spacing: -0.01em;
  text-align: center;
}}
#{element_id} .kw-word {{
  display: inline-block;
  margin: 0 4px;
  transition: transform 0.2s ease;
}}
"""
        js_descriptor = {
            "target": f"#{element_id}",
            "type": "kinetic_words",
            "start_ms": start_ms,
            "duration_ms": duration_ms,
            "animation": animation_type,
            "highlight_term": highlight_term,
        }

        return {
            "html": html_markup,
            "css": css_rules,
            "descriptor": js_descriptor,
        }
