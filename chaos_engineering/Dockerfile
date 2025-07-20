# Multi-stage Dockerfile for Chaos Engineering Test Suite

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 chaos && \
    mkdir -p /app/chaos_reports && \
    chown -R chaos:chaos /app

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/chaos/.local

# Copy application code
COPY --chown=chaos:chaos . .

# Switch to non-root user
USER chaos

# Update PATH
ENV PATH=/home/chaos/.local/bin:$PATH

# Default configuration
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Entry point
ENTRYPOINT ["python", "main.py"]

# Default arguments
CMD ["--scenario", "cascade-failure"]