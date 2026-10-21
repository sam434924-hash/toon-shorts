"""
Purpose: Compatibility re-export of Gemini client wrapper and error classes.
Inputs: Prompts, API configuration, and mock flags.
Outputs: Client instance and SpendCapExceededError class.
Depends on: core.client, core.errors
Used by: None
Config keys: None
Tests: tests/unit/test_spend_cap.py
"""

from .core.client import GeminiClientWrapper
from .core.errors import SpendCapExceededError

__all__ = ["GeminiClientWrapper", "SpendCapExceededError"]
