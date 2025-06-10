# Neuron Safety System Requirements
# =================================
#
# Created by Shalini Ananda, PhD
# © 2025 All Rights Reserved
#
# Dependencies for the Neuron Framework Safety System
# This file lists all required Python packages for the safety
# monitoring, configuration management, and CLI interface.
#
# LEGAL NOTICE:
# This requirements file is part of proprietary safety protocols.
# Commercial use requires explicit licensing from the author.

# Core Python packages
# --------------------

# YAML configuration file support
PyYAML>=6.0.1

# Enhanced logging and structured logging
loguru>=0.7.0

# Data validation and parsing
pydantic>=2.5.0

# CLI argument parsing and command-line interface
click>=8.1.7
rich>=13.7.0  # For rich terminal output and formatting

# Date and time utilities
python-dateutil>=2.8.2

# HTTP client for external integrations
requests>=2.31.0
httpx>=0.25.0  # Async HTTP client

# Async programming support
asyncio-extra>=0.1.0

# Configuration management
configparser>=5.3.0
python-dotenv>=1.0.0  # Environment variable management

# Data serialization and storage
# ------------------------------

# JSON handling with better performance
orjson>=3.9.10

# Database connectivity (for audit logs)
SQLAlchemy>=2.0.23
alembic>=1.13.0  # Database migrations

# File format support
toml>=0.10.2  # TOML configuration files

# Monitoring and observability
# ----------------------------

# Metrics collection and monitoring
prometheus-client>=0.19.0
psutil>=5.9.6  # System resource monitoring

# Performance profiling
py-spy>=0.3.14  # Production profiling

# Memory usage tracking
memory-profiler>=0.61.0

# Networking and communication
# ---------------------------

# WebSocket support for real-time monitoring
websockets>=12.0

# Message queue support
redis>=5.0.1
celery>=5.3.4  # Task queue for background processing

# Security and encryption
# -----------------------

# Cryptographic functions
cryptography>=41.0.7
bcrypt>=4.1.2

# JWT token handling
PyJWT>=2.8.0

# Secure random number generation
secrets  # Built-in Python module

# Testing and validation
# ---------------------

# Unit testing framework
pytest>=7.4.3
pytest-asyncio>=0.21.1
pytest-cov>=4.1.0  # Coverage reporting

# Property-based testing
hypothesis>=6.92.1

# Load testing and stress testing
locust>=2.17.0

# Integration testing
pytest-mock>=3.12.0

# Development and debugging
# ------------------------

# Code formatting and linting
black>=23.11.0
isort>=5.12.0
flake8>=6.1.0
mypy>=1.7.1  # Type checking

# Documentation generation
sphinx>=7.2.6
sphinx-rtd-theme>=1.3.0

# Development utilities
ipython>=8.17.2  # Enhanced Python shell
jupyter>=1.0.0  # Notebook support for analysis

# Optional enterprise features
# ---------------------------

# Machine learning for anomaly detection (optional)
scikit-learn>=1.3.2
numpy>=1.24.4
pandas>=2.1.3

# Time series analysis (optional)
influxdb-client>=1.38.0

# Advanced visualization (optional)
matplotlib>=3.8.2
plotly>=5.17.0

# Cloud platform integrations (optional)
# ---------------------------------------

# AWS SDK
boto3>=1.34.0

# Google Cloud SDK
google-cloud>=0.34.0

# Azure SDK
azure-identity>=1.15.0
azure-storage-blob>=12.19.0

# Kubernetes integration
kubernetes>=28.1.0

# Docker integration
docker>=6.1.3

# Compliance and audit
# -------------------

# GDPR compliance utilities
gdpr-tools>=1.0.0

# SOC2 compliance helpers
compliance-framework>=2.1.0

# Audit trail utilities
audit-log>=1.2.0

# Platform-specific requirements
# -----------------------------

# Windows-specific packages
pywin32>=306; sys_platform == "win32"

# macOS-specific packages
pyobjc>=10.0; sys_platform == "darwin"

# Linux-specific packages
systemd-python>=235; sys_platform == "linux"

# Version constraints for stability
