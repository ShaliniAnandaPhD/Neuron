"""
Unit tests for the vision models and the model swap, with the OpenAI and
Anthropic clients mocked: no API keys, network or W&B account needed.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.config import Config
from src.core.base_agent import Message
from src.models.vision_models import VisionModelInterface, VisionModelRefusal


@pytest.fixture
def vision(monkeypatch):
    monkeypatch.setattr(Config, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(Config, "ANTHROPIC_API_KEY", "test-anthropic-key")
    models = VisionModelInterface()
    models.openai_client = MagicMock()
    models.anthropic_client = MagicMock()
    return models


def openai_reply(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def claude_reply(*blocks, stop_reason="end_turn", model="claude-sonnet-5-5"):
    return SimpleNamespace(
        content=list(blocks), stop_reason=stop_reason, stop_details=None, model=model
    )


def text_block(text):
    return SimpleNamespace(type="text", text=text)


@pytest.mark.asyncio
async def test_openai_request_uses_current_model_and_parameters(vision):
    create = AsyncMock(return_value=openai_reply("Severe damage. Confidence 90%."))
    vision.openai_client.chat.completions.create = create

    result = await vision.analyze_with_openai(b"jpeg-bytes", "Assess the damage")

    kwargs = create.await_args.kwargs
    assert kwargs["model"] == Config.PRIMARY_VISION_MODEL == "gpt-5.6-sol"
    assert kwargs["max_completion_tokens"] == Config.OPENAI_MAX_OUTPUT_TOKENS
    assert kwargs["reasoning_effort"] == "none"
    assert "max_tokens" not in kwargs
    content = kwargs["messages"][0]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert result["assessment"]["severity"] == 8
    assert result["confidence"] == 0.9
    assert result["model"] == "gpt-5.6-sol"


@pytest.mark.asyncio
async def test_claude_request_and_text_after_thinking_block(vision):
    thinking = SimpleNamespace(type="thinking", thinking="")
    create = AsyncMock(
        return_value=claude_reply(thinking, text_block("Minor scratches, likely."))
    )
    vision.anthropic_client.beta.messages.create = create

    result = await vision.analyze_with_claude(b"jpeg-bytes", "Assess the damage")

    kwargs = create.await_args.kwargs
    assert kwargs["model"] == Config.FALLBACK_VISION_MODEL == "claude-sonnet-5-5"
    assert kwargs["max_tokens"] == 16000
    assert kwargs["output_config"] == {"effort": "low"}
    assert kwargs["fallbacks"] == "default"
    assert kwargs["betas"] == ["server-side-fallback-2026-07-01"]
    image, prompt = kwargs["messages"][0]["content"]
    assert image["type"] == "image" and image["source"]["media_type"] == "image/jpeg"
    assert prompt == {"type": "text", "text": "Assess the damage"}
    assert result["raw_response"] == "Minor scratches, likely."
    assert result["assessment"]["severity"] == 3
    assert result["confidence"] == 0.8


@pytest.mark.asyncio
async def test_claude_refusal_raises(vision):
    vision.anthropic_client.beta.messages.create = AsyncMock(
        return_value=claude_reply(stop_reason="refusal")
    )
    with pytest.raises(VisionModelRefusal):
        await vision.analyze_with_claude(b"jpeg-bytes", "Assess the damage")


def test_keywords_match_whole_words(vision):
    assert vision._parse_damage_assessment("Nonetheless, damage looks moderate")[
        "keywords_found"
    ] == ["moderate"]
    assert vision._extract_confidence("I am uncertain about this") == 0.4
    assert vision._extract_confidence("No percentage, no hedging") == 0.75


@pytest.mark.asyncio
async def test_swap_controller_runs_fallback_and_logs_without_crashing(monkeypatch, vision):
    from src.agents.swap_controller import SwapController

    monkeypatch.setattr(
        "src.agents.swap_controller.VisionModelInterface", lambda: vision
    )
    vision.anthropic_client.beta.messages.create = AsyncMock(
        return_value=claude_reply(text_block("Total loss, severe damage, confident."))
    )
    controller = SwapController()

    swap = Message(
        type="model_swap_request",
        payload={
            "claim_data": {"claim_id": "C-1", "image_data": b"jpeg-bytes"},
            "primary_result": {
                "model": "gpt-5.6-sol",
                "assessment": {"severity": 0},
                "confidence": 0.9,
            },
            "text_result": {"severity_score": 10},
            "fallback_model": Config.FALLBACK_VISION_MODEL,
        },
        source="conflict_detector",
        target="swap_controller",
    )

    result = await controller.execute_swap(swap)

    analysis = result.payload["analysis_result"]
    assert analysis["swap_executed"] is True
    assert analysis["swap_valid"] is True  # fallback agrees with the text (10 vs 10)
    assert analysis["fallback_analysis"]["model"] == "claude-sonnet-5-5"
    assert result.payload["metadata"]["models_used"] == ["gpt-5.6-sol", "claude-sonnet-5-5"]
