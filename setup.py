from setuptools import setup, find_packages
import os
import re

# Read version from __init__.py
with open(os.path.join('src', 'neuron', '__init__.py'), 'r') as f:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Filter out comments and empty lines
requirements = [line for line in requirements if line and not line.startswith('#')]

setup(
    name="neuron-framework",  # Using "neuron-framework" to avoid conflicts
    version=version,
    author="Shalini Ananda",
    author_email="your.email@example.com",
    description="A composable agent framework inspired by cognitive neuroscience",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ShaliniAnandaPhD/Neuron",
    project_urls={
        "Bug Tracker": "https://github.com/ShaliniAnandaPhD/Neuron/issues",
        "Documentation": "https://github.com/ShaliniAnandaPhD/Neuron/wiki",
        "Source Code": "https://github.com/ShaliniAnandaPhD/Neuron",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.3.0",
            "flake8>=4.0.1",
            "sphinx>=4.5.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "visualizations": [
            "graphviz>=0.19.1",
            "bokeh>=2.4.2",
        ],
        "integrations": [
            "langchain>=0.0.1",
            "openai>=0.27.0",
        ],
    },
    entry_points={
        'console_scripts': [
            'neuron=neuron.cli:main',  # CLI command
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
