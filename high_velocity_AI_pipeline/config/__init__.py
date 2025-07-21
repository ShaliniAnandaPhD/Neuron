"""
Configuration Package
Centralized configuration management for the High-Velocity AI Pipeline
"""

import os
import json
from pathlib import Path

# Get the config directory path
CONFIG_DIR = Path(__file__).parent

def load_config_file(filename: str) -> dict:
    """Load a configuration file from the config directory"""
    config_path = CONFIG_DIR / filename
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)

def get_config_path(filename: str) -> Path:
    """Get the full path to a configuration file"""
    return CONFIG_DIR / filename

# Available configuration files
AVAILABLE_CONFIGS = [
    "production.json",
    "development.json", 
    "benchmark.json"
]

__all__ = [
    "load_config_file",
    "get_config_path",
    "AVAILABLE_CONFIGS",
    "CONFIG_DIR"
]