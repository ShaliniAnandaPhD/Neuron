# Build from the repository root, so the image gets the neuron package too:
#   docker build -f Microservices/ambiguity/Dockerfile -t ambiguity-resolver .
#   docker run -p 8000:8000 ambiguity-resolver
FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml README.md LICENSE.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY Microservices ./Microservices
RUN pip install --no-cache-dir -r Microservices/ambiguity/requirements.txt

EXPOSE 8000
CMD ["uvicorn", "Microservices.ambiguity.api:app", "--host", "0.0.0.0", "--port", "8000"]
