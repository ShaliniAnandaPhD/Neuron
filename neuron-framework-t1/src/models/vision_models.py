import base64
import re
import time
from typing import Any, Dict

import anthropic
import openai

from config.config import Config
from src import tracing as weave


class VisionModelRefusal(Exception):
    """The vision model declined to analyze the image."""


class VisionModelInterface:
    """Vehicle damage analysis with an OpenAI model (primary) and Claude (fallback)."""

    def __init__(self):
        # Async clients: these methods run inside the agents' event loop, and
        # the synchronous clients blocked it for the whole request.
        self.openai_client = openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)

    @weave.op()
    async def analyze_with_openai(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze an image with the primary (OpenAI) vision model."""
        start_time = time.time()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        response = await self.openai_client.chat.completions.create(
            model=Config.PRIMARY_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            # Current OpenAI models reason first; they take max_completion_tokens
            # (not max_tokens), and effort "none" keeps the answer fast.
            max_completion_tokens=Config.OPENAI_MAX_OUTPUT_TOKENS,
            reasoning_effort=Config.OPENAI_REASONING_EFFORT,
        )

        content = response.choices[0].message.content or ""
        return self._result(content, Config.PRIMARY_VISION_MODEL, start_time)

    @weave.op()
    async def analyze_with_claude(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze an image with the fallback (Claude) vision model."""
        start_time = time.time()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        message = await self.anthropic_client.beta.messages.create(
            model=Config.FALLBACK_VISION_MODEL,
            # Thinking tokens count toward max_tokens, so leave room beyond the
            # short answer itself.
            max_tokens=16000,
            # The swap has a few seconds to finish; low effort answers quickly.
            output_config={"effort": Config.CLAUDE_EFFORT},
            # If a safety classifier declines the request, the API reruns it on
            # a fallback model within the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        if message.stop_reason == "refusal":
            category = getattr(message.stop_details, "category", None)
            raise VisionModelRefusal(f"{message.model} declined the request ({category})")

        # The response can start with a (hidden) thinking block, so collect the
        # text blocks rather than reading content[0].
        content = "".join(block.text for block in message.content if block.type == "text")
        return self._result(content, message.model, start_time)

    def _result(self, content: str, model: str, start_time: float) -> Dict[str, Any]:
        return {
            "assessment": self._parse_damage_assessment(content),
            "confidence": self._extract_confidence(content),
            "raw_response": content,
            "processing_time": time.time() - start_time,
            "model": model,
        }

    def _parse_damage_assessment(self, content: str) -> Dict[str, Any]:
        """Parse a damage assessment from the model response."""
        # Simple keyword parsing; in production use structured outputs instead.
        damage_keywords = {
            "none": 0,
            "minimal": 2,
            "minor": 3,
            "moderate": 5,
            "significant": 7,
            "severe": 8,
            "total": 10,
        }

        # Whole words only: substring matching found "none" in "nonetheless".
        words = set(re.findall(r"[a-z]+", content.lower()))
        found = [keyword for keyword in damage_keywords if keyword in words]
        severity = max((damage_keywords[k] for k in found), default=0)

        return {
            "severity": severity,
            "description": content[:200],
            "keywords_found": found,
        }

    def _extract_confidence(self, content: str) -> float:
        """Extract a confidence score from the response."""
        pct_match = re.search(r"(\d+(?:\.\d+)?)%", content)
        if pct_match:
            return min(1.0, float(pct_match.group(1)) / 100)

        confidence_words = {
            "certain": 0.95,
            "confident": 0.9,
            "likely": 0.8,
            "probable": 0.7,
            "possible": 0.6,
            "uncertain": 0.4,
        }

        words = set(re.findall(r"[a-z]+", content.lower()))
        for word, score in confidence_words.items():
            if word in words:
                return score

        return 0.75  # Default confidence
