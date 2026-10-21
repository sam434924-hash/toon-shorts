"""
Purpose: Cost estimation and user pre-flight confirmation gate.
Inputs: Script plan, style preset, and estimated rewrite counts.
Outputs: Detailed CostEstimate dataclass and confirmation gate boolean.
Depends on: core.config, core.models, dataclasses, sys
Used by: core.pipeline
Config keys: PRICING
Tests: tests/unit/test_spend_cap.py
"""

from dataclasses import dataclass
import sys
from .models import ScriptPlan
from . import config


@dataclass
class CostEstimate:
    total_cost_usd: float
    text_calls: int
    image_calls: int
    tts_calls: int
    tts_character_count: int
    details: str


def estimate_costs(plan: ScriptPlan, style_preset: dict, rewrite_count: int = 1) -> CostEstimate:
    """Computes predicted API calls and dollar cost before performing any generation."""
    num_scenes = len(plan.scenes)
    num_characters = len(plan.characters)
    total_tts_chars = sum(len(s.dialogue_line) for s in plan.scenes)

    # Text calls: 1 plan + 1 critic + rewrites
    text_calls = 1 + 1 + rewrite_count
    est_input_tokens = text_calls * 2500
    est_output_tokens = text_calls * 1000
    text_cost = (
        (est_input_tokens / 1_000_000) * config.PRICING["text_input_per_million_tokens"] +
        (est_output_tokens / 1_000_000) * config.PRICING["text_output_per_million_tokens"]
    )

    # Image calls:
    is_code_renderer = style_preset.get("renderer") == "pillow" or plan.art_style.lower() == "stickman"
    if is_code_renderer:
        image_calls = 0
        image_cost = 0.0
    else:
        image_calls = num_characters + num_scenes
        image_cost = image_calls * config.PRICING["image_per_generation"]

    # TTS calls:
    tts_calls = num_scenes
    tts_cost = (total_tts_chars / 1000) * config.PRICING["tts_per_thousand_characters"]

    total_cost = text_cost + image_cost + tts_cost

    summary = (
        f"\n=======================================================\n"
        f"                  PRE-FLIGHT COST ESTIMATE              \n"
        f"=======================================================\n"
        f"  Topic/Title:       {plan.title}\n"
        f"  Art Style:         {plan.art_style} ({'Local Pillow (Free)' if is_code_renderer else 'Gemini Imagen'})\n"
        f"  Scene Count:       {num_scenes} scenes\n"
        f"  Total Dialogue:    {total_tts_chars} characters\n"
        f"-------------------------------------------------------\n"
        f"  Planned API Calls: {text_calls + image_calls + tts_calls} total\n"
        f"    - Text / Critic: {text_calls} calls (~${text_cost:.4f})\n"
        f"    - Image Gen:     {image_calls} images (~${image_cost:.4f})\n"
        f"    - Voice / TTS:   {tts_calls} lines  (~${tts_cost:.4f})\n"
        f"-------------------------------------------------------\n"
        f"  ESTIMATED TOTAL:   ${total_cost:.4f} USD\n"
        f"=======================================================\n"
    )

    return CostEstimate(
        total_cost_usd=round(total_cost, 4),
        text_calls=text_calls,
        image_calls=image_calls,
        tts_calls=tts_calls,
        tts_character_count=total_tts_chars,
        details=summary,
    )


def confirm_cost_gate(estimate: CostEstimate, auto_confirm: bool = False) -> bool:
    """Displays estimated cost and pauses for user confirmation unless auto_confirm is True."""
    print(estimate.details)
    if auto_confirm:
        print("[Auto-Confirm] --yes flag provided. Proceeding with generation...\n")
        return True

    try:
        response = input("Proceed with generation? [y/N]: ").strip().lower()
        if response in ("y", "yes"):
            print("Confirmed. Starting generation pipeline...\n")
            return True
        else:
            print("Operation aborted by user.")
            return False
    except (EOFError, KeyboardInterrupt):
        print("\nOperation aborted.")
        return False
