#!/usr/bin/env python3
"""
Setup script for the High-Velocity AI Pipeline.

This script handles the packaging and distribution of the pipeline,
making it installable via pip and enabling the setup of command-line entry points.
"""

import os
import re
from pathlib import Path
from setuptools import setup, find_packages

# Get the project's root directory
ROOT_DIR = Path(__file__).parent

def read_file(file_path: Path) -> str:
    """Reads the content of a given file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def get_version() -> str:
    """Dynamically reads the version from the project's __init__.py file."""
    version_file = read_file(ROOT_DIR / "src" / "__init__.py")
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def get_requirements(file_name: str) -> list[str]:
    """Reads requirements from a file, ignoring comments."""
    requirements = []
    for line in read_file(ROOT_DIR / file_name).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(line)
    return requirements

# Project metadata
NAME = "high-velocity-pipeline"
VERSION = get_version()
DESCRIPTION = "Production High-Velocity AI Pipeline for Financial Trading"
LONG_DESCRIPTION = read_file(ROOT_DIR / "README.md")
LONG_DESCRIPTION_CONTENT_TYPE = "text/markdown"
URL = "https://github.com/your-org/high-velocity-pipeline"
AUTHOR = "High-Velocity Pipeline Team"
AUTHOR_EMAIL = "team@high-velocity-pipeline.com"
LICENSE = "MIT"

# Dependencies
INSTALL_REQUIRES = get_requirements("requirements.txt")
EXTRAS_REQUIRE = {
    'dev': [
        'pytest>=7.0.0',
        'pytest-asyncio>=0.21.0',
        'black>=23.0.0',
        'flake8>=6.0.0',
        'mypy>=1.0.0',
        'pre-commit>=3.0.0'
    ],
    'monitoring': [
        'prometheus-client>=0.17.0',
        'grafana-api>=1.0.3',
        'elasticsearch>=8.0.0'
    ],
    'deployment': [
        'kubernetes>=26.0.0',
        'docker>=6.0.0',
        'ansible>=7.0.0'
    ]
}

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type=LONG_DESCRIPTION_CONTENT_TYPE,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENSE,
    
    # Find packages automatically in the 'src' directory
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    
    python_requires=">=3.8",
    
    # Install dependencies
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    
    # Define command-line scripts
    entry_points={
        'console_scripts': [
            'hvp-run=run_pipeline:main',
            'hvp-monitor=scripts.monitor_dashboard:main',
            'hvp-health=scripts.health_checker:main',
            'hvp-deploy=scripts.deployment_utils:main',
        ],
    },
    
    # Include non-Python files specified in MANIFEST.in
    include_package_data=True,
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Distributed Computing",
    ],
    
    # Keywords for discoverability
    keywords=[
        "ai", "pipeline", "trading", "financial", "high-velocity",
        "hot-swap", "performance", "monitoring", "production",
        "openai", "groq", "observability"
    ],
    
    # Project URLs for PyPI
    project_urls={
        "Bug Reports": f"{URL}/issues",
        "Source": URL,
    },
)
