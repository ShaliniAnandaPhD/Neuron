# High-Velocity AI Pipeline - Production Docker Image
# Multi-stage build for optimized production deployment

# =============================================================================
# BUILD STAGE
# =============================================================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/src:$PYTHONPATH"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    htop \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r hvpuser && \
    useradd -r -g hvpuser -d /app -s /bin/bash hvpuser

# Create application directories
RUN mkdir -p /app/{src,config,scripts,exports,logs} && \
    chown -R hvpuser:hvpuser /app

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application files with proper ownership
COPY --chown=hvpuser:hvpuser . .

# Create necessary directories and set permissions
RUN chmod +x run_pipeline.py && \
    chmod +x scripts/*.py && \
    mkdir -p /app/exports /app/logs && \
    chown -R hvpuser:hvpuser /app/exports /app/logs

# Switch to non-root user
USER hvpuser

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python scripts/health_checker.py --check-only || exit 1

# Labels for metadata
LABEL maintainer="High-Velocity Pipeline Team" \
      version="1.0.0" \
      description="Production High-Velocity AI Pipeline" \
      org.opencontainers.image.title="High-Velocity AI Pipeline" \
      org.opencontainers.image.description="Production trading system with adaptive AI agent hot-swapping" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="High-Velocity Pipeline Team" \
      org.opencontainers.image.licenses="MIT"

# Default command
CMD ["python", "run_pipeline.py", "--config", "config/production.json"]

# =============================================================================
# DEVELOPMENT STAGE (Optional)
# =============================================================================
FROM production as development

# Switch back to root for development dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    vim \
    nano \
    git \
    bash-completion \
    iputils-ping \
    telnet \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN /opt/venv/bin/pip install \
    pytest \
    pytest-asyncio \
    black \
    flake8 \
    mypy \
    ipython \
    jupyter \
    debugpy

# Switch back to hvpuser
USER hvpuser

# Override command for development
CMD ["python", "run_pipeline.py", "--dev"]

# =============================================================================
# BENCHMARK STAGE (Optional)
# =============================================================================
FROM production as benchmark

# Install additional monitoring tools
USER root
RUN apt-get update && apt-get install -y \
    stress-ng \
    iotop \
    nethogs \
    && rm -rf /var/lib/apt/lists/*

USER hvpuser

# Override command for benchmarking
CMD ["python", "run_pipeline.py", "--benchmark", "--duration", "300"]