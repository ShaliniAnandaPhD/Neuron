FROM python:3.9-slim

LABEL version="2.0"
LABEL description="Advanced Neuron Agent for Legal"
LABEL industry="Legal"
LABEL use_case="Patient Data Management"
LABEL complexity="Basic (3 blocks)"
LABEL behavior="Innovator"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY test_advanced.py .

# Create logs directory
RUN mkdir -p logs

# Create non-root user
RUN useradd -m -u 1000 neuron && chown -R neuron:neuron /app
USER neuron

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 -c "import asyncio; from main import AdvancedNeuronSystem; \
                  system = AdvancedNeuronSystem(); \
                  print('Agent healthy')" || exit 1

# Expose port for future API integration
EXPOSE 8080

# Run the agent
CMD ["python3", "main.py"]
