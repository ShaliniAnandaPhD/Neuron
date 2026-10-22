FROM python:3.12-slim

WORKDIR /app

# The agent uses only the standard library, so there is nothing to pip install.
COPY neuron_agent.py add_use_case.py ./
COPY use_cases/ use_cases/

RUN useradd -m -u 1000 neuron
USER neuron

# docker run -it neuron-agent --use-case legal
ENTRYPOINT ["python", "neuron_agent.py"]
CMD ["--list"]
