from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import uvicorn
import json
from ambiguity_resolver import AmbiguityResolverMicroservice, load_config

app = FastAPI(title="Ambiguity Resolver API")

# Initialize microservice
config = load_config()
resolver = AmbiguityResolverMicroservice(
    name="Ambiguity Resolver API",
    description="API for resolving ambiguity in user queries"
)
resolver.deploy()

class QueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"

class QueryBatchRequest(BaseModel):
    queries: list[str]
    user_id: str = "anonymous"

@app.post("/resolve")
async def resolve_ambiguity(request: QueryRequest):
    """Resolve ambiguity in a single query."""
    try:
        result = await resolver.resolve_ambiguity(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resolve/batch")
async def resolve_batch(request: QueryBatchRequest):
    """Resolve ambiguity in multiple queries."""
    try:
        results = []
        for query in request.queries:
            result = await resolver.resolve_ambiguity(query)
            results.append(result)
        
        return {
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    """Get current performance metrics."""
    return resolver.get_metrics()

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
