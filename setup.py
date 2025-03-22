"""
Setup script for the Neuron framework package.
"""

import os
from setuptools import setup, find_packages

# Read the README file for the long description
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Read the requirements file for dependencies
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="neuron-framework",
    version="1.0.0",
    author="Neuron Framework Team",
    author_email="info@neuron-framework.org",
    description="A composable agent framework toolkit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/neuron-framework/neuron",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "neuron=neuron.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "neuron": ["config/*.json", "data/.gitkeep", "plugins/.gitkeep"],
    },
)
"""
