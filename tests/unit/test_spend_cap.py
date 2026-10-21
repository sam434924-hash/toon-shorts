"""Tests for spend cap and API limit enforcement."""

import pytest
from toonshorts.client import GeminiClientWrapper, SpendCapExceededError
from toonshorts import config


def test_api_calls_spend_cap():
    client = GeminiClientWrapper(mock=True)
    client.api_call_count = config.MAX_API_CALLS_PER_RUN - 1
    
    # One allowed
    client._increment_api_call()
    assert client.api_call_count == config.MAX_API_CALLS_PER_RUN

    # Next must raise
    with pytest.raises(SpendCapExceededError) as exc_info:
        client._increment_api_call()
    assert "Hard cap exceeded" in str(exc_info.value)


def test_image_generations_spend_cap():
    client = GeminiClientWrapper(mock=True)
    client.image_generation_count = config.MAX_IMAGES_PER_RUN - 1

    # One allowed
    client._increment_image_gen()
    assert client.image_generation_count == config.MAX_IMAGES_PER_RUN

    # Next must raise
    with pytest.raises(SpendCapExceededError) as exc_info:
        client._increment_image_gen()
    assert "Hard cap exceeded" in str(exc_info.value)
