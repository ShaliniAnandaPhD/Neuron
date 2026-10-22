# FS_Neuron: NFL data pipeline for Fantasy Football Neuron

The data layer behind the Fantasy Football Neuron implementation: it collects
live NFL data from several providers, normalizes it, and aggregates player
statistics for the agents in [`../FFSapp`](../FFSapp).

| Module | What it does |
|--------|--------------|
| `nfl_data_models.py` | Data models and enums: player updates, games, injuries, stat categories, configuration |
| `nf_data_sources.py` | Provider integrations with rate limiting, retries and normalization, plus a `DataSourceManager` that combines them |
| `nfl_data_pipeline.py` | Real-time ingestion service (FastAPI, Redis, PostgreSQL, Prometheus metrics); targets under 200 ms latency |
| `player_stats_system.py` | Season stat aggregation and validation: points per game, target share, snap share, red zone usage |

These modules are a reference implementation extracted from the production
system. They expect provider access, Redis and PostgreSQL, and are not wired
into the repository's test suite.

Main dependencies: `aiohttp`, `backoff`, `beautifulsoup4`, `redis`,
`asyncpg`, `sqlalchemy`, `fastapi`, `pydantic`, `prometheus-client`,
`numpy`, `pandas`, `scipy`. (`nfl_data_pipeline.py` imports `aioredis`, which
has since been merged into `redis` as `redis.asyncio`.)
