"""
Purpose: Spend cap and API budget tracking for pipeline operations.
Inputs: Increments for API calls, image generations, and critic rewrites.
Outputs: Spend limits enforcement, raising SpendCapExceededError on threshold.
Depends on: core.config, core.errors
Used by: core, core.client
Config keys: MAX_API_CALLS_PER_RUN, MAX_CRITIC_REWRITES, MAX_IMAGES_PER_RUN
Tests: tests/unit/test_spend_cap.py
"""

from . import config
from .errors import SpendCapExceededError


class SpendCapTracker:
    """Enforces execution spend caps on API calls, images, and critic loops."""

    def __init__(self):
        self.api_call_count = 0
        self.image_generation_count = 0
        self.critic_rewrite_count = 0

    def increment_api_call(self):
        if self.api_call_count >= config.MAX_API_CALLS_PER_RUN:
            raise SpendCapExceededError(
                f"Hard cap exceeded: {self.api_call_count} API calls reached (max {config.MAX_API_CALLS_PER_RUN})."
            )
        self.api_call_count += 1

    def increment_image_gen(self):
        if self.image_generation_count >= config.MAX_IMAGES_PER_RUN:
            raise SpendCapExceededError(
                f"Hard cap exceeded: {self.image_generation_count} images reached (max {config.MAX_IMAGES_PER_RUN})."
            )
        self.image_generation_count += 1

    def increment_critic_rewrite(self):
        if self.critic_rewrite_count >= config.MAX_CRITIC_REWRITES:
            raise SpendCapExceededError(
                f"Hard cap exceeded: {self.critic_rewrite_count} critic rewrites reached (max {config.MAX_CRITIC_REWRITES})."
            )
        self.critic_rewrite_count += 1
