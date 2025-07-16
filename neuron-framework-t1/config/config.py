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
    
    # Model Configuration
    PRIMARY_VISION_MODEL = "gpt-4-vision-preview"
    FALLBACK_VISION_MODEL = "claude-3-sonnet-20240229"