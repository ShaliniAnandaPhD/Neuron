# LLaMA 3 Neuron Framework

A REST service that runs Neuron style multi-agent pipelines on a self-hosted
LLaMA 3 model. Requests flow through specialised agents (intake, analysis,
synthesis, quality control, cross-check, output) in one of four orchestration
patterns: sequential, parallel, hierarchical or mesh.

## Architecture

| Piece | File | Notes |
|-------|------|-------|
| API | `main.py` | FastAPI app, auth by API key, rate limiting |
| Agents | `agents.py` | The six agent types above |
| Orchestrator | `orchestrator.py` | Runs the orchestration patterns |
| Model client | `llama_client.py` | Talks to an OpenAI-compatible LLaMA server (llama.cpp) |
| Message bus / task queue | `message_bus.py`, `task_queue.py` | Redis |
| Data models | `models.py` | Tasks, messages, agent state |
| Monitoring | `monitoring.py` | Prometheus metrics at `/metrics` |

## Run it

1. Put a LLaMA 3 GGUF model at `models/llama3.gguf`.
2. Copy `.env.example` to `.env` and set `LLAMA3_API_KEY` and `JWT_SECRET`.
3. Start the stack (PostgreSQL, Redis, llama.cpp server, the API):

```bash
cd llam3-neuron-framework
docker compose up --build
# add Prometheus and Grafana:
docker compose --profile monitoring up --build
```

The API listens on http://localhost:8000. Main endpoints:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/process` | Run one task through the agents |
| `POST /api/v1/batch` | Run several tasks |
| `GET /api/v1/task/{task_id}` | Task status and result |
| `GET /api/v1/agents/status` | Agent health |
| `GET /api/v1/system/status` | System overview |
| `GET /health`, `GET /metrics` | Health check, Prometheus metrics |

To run the API outside Docker: `pip install -r requirements.txt`, start Redis,
PostgreSQL and a llama.cpp server yourself, then `python main.py`.
`scripts/init_db.py` creates the database tables and `scripts/test_system.py`
exercises a running instance.
