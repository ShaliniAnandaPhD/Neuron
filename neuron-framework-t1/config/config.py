import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    WEAVE_PROJECT = os.getenv("WEAVE_PROJECT_NAME", "neuron-t1-test")

    # T1 Test Parameters
    CONFIDENCE_THRESHOLD = 0.8
    SWAP_TIMEOUT = 5.0
    ACCURACY_TOLERANCE = 0.02

    # Model Configuration (override with environment variables).
    # gpt-4-vision-preview and claude-3-sonnet-20240229 have been retired;
    # these are the replacements named in the providers' deprecation notices.
    PRIMARY_VISION_MODEL = os.getenv("PRIMARY_VISION_MODEL", "gpt-5.6-sol")
    FALLBACK_VISION_MODEL = os.getenv("FALLBACK_VISION_MODEL", "claude-sonnet-5-5")
    OPENAI_REASONING_EFFORT = os.getenv("PRIMARY_VISION_REASONING_EFFORT", "none")
    OPENAI_MAX_OUTPUT_TOKENS = 500
    CLAUDE_EFFORT = os.getenv("FALLBACK_VISION_EFFORT", "low")
