FROM python:3.9-slim

LABEL version="2.0"
LABEL description="Advanced Neuron Agent for Healthcare"
LABEL industry="Healthcare"

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY test_advanced.py .

RUN useradd -m -u 1000 neuron && chown -R neuron:neuron /app
USER neuron

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import main; print('Agent healthy')" || exit 1

EXPOSE 8080

CMD ["python", "main.py"]
