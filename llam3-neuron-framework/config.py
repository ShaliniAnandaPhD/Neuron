#!/usr/bin/env python3
"""
Production Configuration for LLaMA3 Neuron Framework
Handles all configuration settings, environment variables, and constants
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

# Weights & Biases Configuration
WANDB_ENTITY = os.getenv("WANDB_ENTITY", "neuron-framework")
WANDB_PROJECT = os.getenv("WANDB_PROJECT", "llama3-orchestration")
WEAVE_PROJECT_NAME = f"{WANDB_ENTITY}/{WANDB_PROJECT}"

# LLaMA3 Model Configuration
LLAMA3_MODEL_PATH = os.getenv("LLAMA3_MODEL_PATH", "/models/llama3")
LLAMA3_API_ENDPOINT = os.getenv("LLAMA3_API_ENDPOINT", "http://localhost:8080")
LLAMA3_API_KEY = os.getenv("LLAMA3_API_KEY", "")

# System Configuration
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://localhost/neuron")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "4"))

# ============================================================================
# LLAMA3 SPECIFICATIONS
# ============================================================================

# Model Parameters
LLAMA3_CONTEXT_WINDOW = 8192  # Maximum tokens in context
LLAMA3_EMBEDDING_DIM = 4096   # Embedding dimension
LLAMA3_MAX_GENERATION = 4096  # Maximum generation tokens
LLAMA3_VOCAB_SIZE = 128256    # Vocabulary size

# Performance Parameters
OPTIMAL_BATCH_SIZE = int(os.getenv("OPTIMAL_BATCH_SIZE", "8"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "16"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))
TOKEN_RATE_LIMIT = int(os.getenv("TOKEN_RATE_LIMIT", "100000"))

# ============================================================================
# AGENT CONFIGURATION
# ============================================================================

class AgentType(Enum):
    """Enumeration of available agent types in the system"""
    INTAKE = "intake"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    OUTPUT = "output"
    QUALITY_CONTROL = "quality_control"
    CROSS_CHECK = "cross_check"
    ROUTER = "router"
    COORDINATOR = "coordinator"

class MessagePriority(Enum):
    """Message priority levels for inter-agent communication"""
    CRITICAL = 1  # Immediate processing required
    HIGH = 2      # Process as soon as possible
    MEDIUM = 3    # Normal processing
    LOW = 4       # Process when resources available
    BATCH = 5     # Can be batched with other messages

class OrchestrationPattern(Enum):
    """Available orchestration patterns for processing"""
    SEQUENTIAL = "sequential"      # One agent after another
    PARALLEL = "parallel"          # Multiple agents simultaneously
    HIERARCHICAL = "hierarchical"  # Tree-based processing
    MESH = "mesh"                  # Full interconnection
    ADAPTIVE = "adaptive"          # Dynamic pattern selection
    PIPELINE = "pipeline"          # Stream processing
    SCATTER_GATHER = "scatter_gather"  # Map-reduce style

# ============================================================================
# AGENT SPECIFICATIONS
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for individual agents"""
    agent_id: str
    agent_type: AgentType
    model_config: Dict[str, Any]
    max_concurrent_tasks: int = 5
    timeout_seconds: float = 60.0
    retry_attempts: int = 3
    memory_limit_mb: int = 1024
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

# Default agent configurations
DEFAULT_AGENT_CONFIGS = {
    "intake": AgentConfig(
        agent_id="intake_01",
        agent_type=AgentType.INTAKE,
        model_config={
            "temperature": 0.3,
            "max_tokens": 1024,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        max_concurrent_tasks=10,
        timeout_seconds=30.0
    ),
    "analysis": AgentConfig(
        agent_id="analysis_01",
        agent_type=AgentType.ANALYSIS,
        model_config={
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1
        },
        max_concurrent_tasks=5,
        timeout_seconds=120.0,
        memory_limit_mb=2048
    ),
    "synthesis": AgentConfig(
        agent_id="synthesis_01",
        agent_type=AgentType.SYNTHESIS,
        model_config={
            "temperature": 0.5,
            "max_tokens": 3072,
            "top_p": 0.92,
            "frequency_penalty": 0.05,
            "presence_penalty": 0.05
        },
        max_concurrent_tasks=3,
        timeout_seconds=180.0,
        memory_limit_mb=4096
    ),
    "output": AgentConfig(
        agent_id="output_01",
        agent_type=AgentType.OUTPUT,
        model_config={
            "temperature": 0.3,
            "max_tokens": 2048,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        max_concurrent_tasks=8,
        timeout_seconds=60.0
    ),
    "quality_control": AgentConfig(
        agent_id="qc_01",
        agent_type=AgentType.QUALITY_CONTROL,
        model_config={
            "temperature": 0.1,
            "max_tokens": 1024,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        max_concurrent_tasks=5,
        timeout_seconds=45.0
    ),
    "cross_check": AgentConfig(
        agent_id="crosscheck_01",
        agent_type=AgentType.CROSS_CHECK,
        model_config={
            "temperature": 0.2,
            "max_tokens": 1024,
            "top_p": 0.9,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        max_concurrent_tasks=5,
        timeout_seconds=45.0
    )
}

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================

# Redis key prefixes
REDIS_PREFIX = "neuron:"
REDIS_AGENT_PREFIX = f"{REDIS_PREFIX}agent:"
REDIS_TASK_PREFIX = f"{REDIS_PREFIX}task:"
REDIS_RESULT_PREFIX = f"{REDIS_PREFIX}result:"
REDIS_METRIC_PREFIX = f"{REDIS_PREFIX}metric:"
REDIS_LOCK_PREFIX = f"{REDIS_PREFIX}lock:"

# Redis expiration times (seconds)
TASK_EXPIRY = 3600           # 1 hour
RESULT_EXPIRY = 86400        # 24 hours
METRIC_EXPIRY = 604800       # 7 days
LOCK_EXPIRY = 300            # 5 minutes

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database table names
DB_AGENTS_TABLE = "agents"
DB_TASKS_TABLE = "tasks"
DB_RESULTS_TABLE = "results"
DB_METRICS_TABLE = "metrics"
DB_EVENTS_TABLE = "orchestration_events"

# ============================================================================
# MONITORING & LOGGING
# ============================================================================

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "neuron_framework.log")

# Metrics configuration
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"
METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
METRICS_INTERVAL = int(os.getenv("METRICS_INTERVAL", "60"))  # seconds

# Health check configuration
HEALTH_CHECK_PORT = int(os.getenv("HEALTH_CHECK_PORT", "8081"))
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))  # seconds

# ============================================================================
# PERFORMANCE THRESHOLDS
# ============================================================================

# Success criteria for pattern evaluation
CORRELATION_THRESHOLD = 0.7   # Minimum correlation score
REPLICATION_THRESHOLD = 0.85  # Minimum replication rate
MIN_PERFORMANCE_LIFT = 0.1    # Minimum 10% improvement

# Performance monitoring thresholds
MAX_LATENCY_MS = 1000        # Maximum acceptable latency
MIN_THROUGHPUT_TPS = 10      # Minimum transactions per second
MAX_ERROR_RATE = 0.05        # Maximum 5% error rate
MAX_MEMORY_USAGE_PCT = 80    # Maximum 80% memory usage

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# API Security
API_KEY_HEADER = "X-API-Key"
ENABLE_AUTH = os.getenv("ENABLE_AUTH", "true").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# Rate limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "1000"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # seconds

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Feature toggles for production
FEATURES = {
    "enable_weave_tracing": os.getenv("ENABLE_WEAVE", "true").lower() == "true",
    "enable_caching": os.getenv("ENABLE_CACHING", "true").lower() == "true",
    "enable_batching": os.getenv("ENABLE_BATCHING", "true").lower() == "true",
    "enable_auto_scaling": os.getenv("ENABLE_AUTO_SCALING", "false").lower() == "true",
    "enable_circuit_breaker": os.getenv("ENABLE_CIRCUIT_BREAKER", "true").lower() == "true",
    "enable_request_validation": os.getenv("ENABLE_REQUEST_VALIDATION", "true").lower() == "true",
    "enable_response_compression": os.getenv("ENABLE_RESPONSE_COMPRESSION", "true").lower() == "true"
}

# ============================================================================
# CIRCUIT BREAKER CONFIGURATION
# ============================================================================

CIRCUIT_BREAKER_THRESHOLD = 5    # Failures before opening
CIRCUIT_BREAKER_TIMEOUT = 60     # Seconds before attempting reset
CIRCUIT_BREAKER_MAX_ATTEMPTS = 3 # Max attempts before permanent failure

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    
    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        
        # File handler if specified
        if LOG_FILE:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setLevel(getattr(logging, LOG_LEVEL))
            file_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)
    
    return logger

def validate_config() -> bool:
    """
    Validate that all required configuration is present
    
    Returns:
        True if configuration is valid, False otherwise
    """
    required_vars = []
    
    if ENABLE_AUTH:
        required_vars.extend(["JWT_SECRET"])
    
    if FEATURES["enable_weave_tracing"]:
        required_vars.extend(["WANDB_ENTITY"])
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger = get_logger(__name__)
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    return True

# ============================================================================
# CONFIGURATION EXPORT
# ============================================================================

# Export all configuration as a dictionary for easy access
CONFIG = {
    "wandb": {
        "entity": WANDB_ENTITY,
        "project": WANDB_PROJECT,
        "weave_project": WEAVE_PROJECT_NAME
    },
    "llama3": {
        "model_path": LLAMA3_MODEL_PATH,
        "api_endpoint": LLAMA3_API_ENDPOINT,
        "api_key": LLAMA3_API_KEY,
        "context_window": LLAMA3_CONTEXT_WINDOW,
        "embedding_dim": LLAMA3_EMBEDDING_DIM,
        "max_generation": LLAMA3_MAX_GENERATION,
        "vocab_size": LLAMA3_VOCAB_SIZE,
        "optimal_batch_size": OPTIMAL_BATCH_SIZE
    },
    "system": {
        "max_workers": MAX_WORKERS,
        "redis_url": REDIS_URL,
        "postgres_url": POSTGRES_URL
    },
    "api": {
        "host": API_HOST,
        "port": API_PORT,
        "workers": API_WORKERS
    },
    "agents": DEFAULT_AGENT_CONFIGS,
    "features": FEATURES,
    "thresholds": {
        "correlation": CORRELATION_THRESHOLD,
        "replication": REPLICATION_THRESHOLD,
        "performance_lift": MIN_PERFORMANCE_LIFT,
        "max_latency_ms": MAX_LATENCY_MS,
        "min_throughput_tps": MIN_THROUGHPUT_TPS,
        "max_error_rate": MAX_ERROR_RATE
    }
}