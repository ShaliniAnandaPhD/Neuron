"""
Tests Package
Comprehensive test suite for the High-Velocity AI Pipeline
"""

import sys
import os
from pathlib import Path

# Add src directory to path for testing
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Test configuration
TEST_CONFIG = {
    "use_mock_apis": True,
    "test_data_dir": project_root / "tests" / "data",
    "temp_export_dir": project_root / "tests" / "temp_exports"
}

__version__ = "1.0.0"
__all__ = ["TEST_CONFIG"]