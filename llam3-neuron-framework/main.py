#!/usr/bin/env python3
"""
Main API Server for LLaMA3 Neuron Framework
FastAPI-based REST API for the orchestration system
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid

from config import (
    get_logger,
    validate_config,
    API_HOST,
    API_PORT,
    API_WORKERS,
    ENABLE_AUTH,
    API_KEY_HEADER,
    FEATURES,
    DEFAULT_AGENT_CONFIGS,
    OrchestrationPattern,
    MessagePriority
)
from models import (
    ProcessingRequest,
    ProcessingResponse,
    BatchRequest,
    BatchResponse,
    Task,
    TaskStatus,
    HealthStatus,
    validate_request
)
from agents import AgentFactory
from orchestrator import OrchestrationEngine
from message_bus import create_message_bus
from task_queue import create_task_queue
from llama_client import create_llama_client
from monitoring import MonitoringService
from utils import RateLimiter, json_dumps

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

# System components (initialized in lifespan)
agents: Dict[str, Any] = {}
message_bus = None
task_queue = None
orchestrator = None
monitoring = None
llama_client = None
rate_limiter = None

# ============================================================================
# API MODELS
# ============================================================================

class ProcessRequest(BaseModel):
    """API request model for processing"""
    content: str = Field(..., description="Content to process")
    content_type: str = Field("text", description="Type of content")
    pattern: Optional[str] = Field(None, description="Orchestration pattern to use")
    priority: Optional[str] = Field("medium", description="Processing priority")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processing options")

class ProcessResponse(BaseModel):
    """API response model for processing"""
    request_id: str = Field(..., description="Request ID")
    status: str = Field(..., description="Processing status")
    result: Optional[Dict[str, Any]] = Field(None, description="Processing result")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    pattern_used: str = Field(..., description="Orchestration pattern used")
    agents_involved: List[str] = Field(..., description="Agents that processed the request")

class BatchProcessRequest(BaseModel):
    """API request model for batch processing"""
    requests: List[ProcessRequest] = Field(..., description="List of requests to process")
    pattern: Optional[str] = Field(None, description="Orchestration pattern for batch")
    priority: Optional[str] = Field("batch", description="Batch priority")

class SystemStatus(BaseModel):
    """System status response model"""
    status: str = Field(..., description="Overall system status")
    health: Dict[str, Any] = Field(..., description="Component health status")
    metrics: Dict[str, Any] = Field(..., description="System metrics")
    agents: Dict[str, Any] = Field(..., description="Agent statuses")
    version: str = Field("1.0.0", description="API version")

# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown
    """
    # Startup
    logger.info("Starting LLaMA3 Neuron Framework API")
    
    # Validate configuration
    if not validate_config():
        raise RuntimeError("Invalid configuration")
    
    global agents, message_bus, task_queue, orchestrator, monitoring, llama_client, rate_limiter
    
    try:
        # Initialize LLaMA client
        logger.info("Initializing LLaMA client...")
        llama_client = await create_llama_client().__aenter__()
        
        # Initialize message bus
        logger.info("Initializing message bus...")
        message_bus = create_message_bus(distributed=FEATURES.get("enable_distributed", False))
        await message_bus.start()
        
        # Initialize task queue
        logger.info("Initializing task queue...")
        task_queue = create_task_queue(
            queue_type="scheduled" if FEATURES.get("enable_scheduling", False) else "basic"
        )
        if hasattr(task_queue, 'start'):
            await task_queue.start()
        else:
            await task_queue.connect()
        
        # Create agents
        logger.info("Creating agents...")
        for agent_id, config in DEFAULT_AGENT_CONFIGS.items():
            agent = AgentFactory.create_agent(config.agent_type, config)
            await agent.start()
            agents[agent_id] = agent
            
            # Register with message bus
            message_bus.register_agent(agent_id, agent.handle_message)
        
        # Initialize orchestrator
        logger.info("Initializing orchestrator...")
        orchestrator = OrchestrationEngine(agents, message_bus, task_queue)
        
        # Initialize monitoring
        logger.info("Initializing monitoring...")
        monitoring = MonitoringService(agents, task_queue, message_bus, llama_client)
        await monitoring.start()
        
        # Initialize rate limiter
        if FEATURES.get("enable_rate_limiting", True):
            from config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
            rate_limiter = RateLimiter(
                rate=RATE_LIMIT_REQUESTS / RATE_LIMIT_WINDOW,
                capacity=RATE_LIMIT_REQUESTS
            )
        
        logger.info("API startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLaMA3 Neuron Framework API")
    
    try:
        # Stop monitoring
        if monitoring:
            await monitoring.stop()
        
        # Stop agents
        for agent in agents.values():
            await agent.stop()
        
        # Stop task queue
        if task_queue:
            if hasattr(task_queue, 'stop'):
                await task_queue.stop()
            else:
                await task_queue.close()
        
        # Stop message bus
        if message_bus:
            await message_bus.stop()
        
        # Close LLaMA client
        if llama_client:
            await llama_client.__aexit__(None, None, None)
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    
    logger.info("API shutdown complete")

# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="LLaMA3 Neuron Framework API",
    description="Production-ready agent orchestration framework using LLaMA3",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AUTHENTICATION
# ============================================================================

async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key if authentication is enabled"""
    if not ENABLE_AUTH:
        return True
    
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # In production, validate against database or secure store
    # This is a simple example
    if x_api_key != "your-api-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True

# ============================================================================
# RATE LIMITING
# ============================================================================

async def check_rate_limit(request: Request):
    """Check rate limit if enabled"""
    if not rate_limiter:
        return True
    
    # Use client IP as identifier
    client_ip = request.client.host
    
    # Check if rate limit allows request
    allowed = await rate_limiter.acquire()
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    return True

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "LLaMA3 Neuron Framework",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs"
    }

@app.post("/api/v1/process", response_model=ProcessResponse)
async def process_content(
    request: ProcessRequest,
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Process content through the orchestration system
    
    Args:
        request: Processing request
        
    Returns:
        Processing response
    """
    start_time = time.time()
    
    try:
        # Create processing request
        processing_request = ProcessingRequest(
            content=request.content,
            content_type=request.content_type,
            processing_options=request.options,
            pattern=OrchestrationPattern(request.pattern) if request.pattern else None,
            priority=MessagePriority[request.priority.upper()]
        )
        
        # Validate request
        validation_errors = validate_request(processing_request)
        if validation_errors:
            raise HTTPException(status_code=400, detail=f"Invalid request: {', '.join(validation_errors)}")
        
        # Process through orchestrator
        response = await orchestrator.process_request(processing_request)
        
        # Convert to API response
        return ProcessResponse(
            request_id=response.request_id,
            status=response.status.value,
            result=response.result,
            error=response.error,
            processing_time_ms=response.processing_time_ms,
            pattern_used=response.pattern_used.value if response.pattern_used else "unknown",
            agents_involved=response.agents_involved
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing error: {e}")
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessResponse(
            request_id=str(uuid.uuid4()),
            status="failed",
            error=str(e),
            processing_time_ms=processing_time,
            pattern_used="none",
            agents_involved=[]
        )

@app.post("/api/v1/batch", response_model=BatchResponse)
async def process_batch(
    request: BatchProcessRequest,
    authenticated: bool = Depends(verify_api_key),
    rate_limited: bool = Depends(check_rate_limit)
):
    """
    Process multiple requests as a batch
    
    Args:
        request: Batch processing request
        
    Returns:
        Batch processing response
    """
    if not FEATURES.get("enable_batching", True):
        raise HTTPException(status_code=501, detail="Batch processing not enabled")
    
    start_time = time.time()
    batch_id = str(uuid.uuid4())
    
    # Create batch request
    batch_request = BatchRequest(
        requests=[
            ProcessingRequest(
                content=req.content,
                content_type=req.content_type,
                processing_options=req.options,
                pattern=OrchestrationPattern(req.pattern) if req.pattern else None,
                priority=MessagePriority[req.priority.upper()]
            )
            for req in request.requests
        ],
        pattern=OrchestrationPattern(request.pattern) if request.pattern else None,
        priority=MessagePriority[request.priority.upper()]
    )
    
    # Process each request
    responses = []
    for req in batch_request.requests:
        try:
            response = await orchestrator.process_request(req)
            responses.append(response)
        except Exception as e:
            logger.error(f"Batch item processing error: {e}")
            responses.append(ProcessingResponse(
                request_id=req.id,
                status=TaskStatus.FAILED,
                error=str(e),
                processing_time_ms=0
            ))
    
    # Calculate batch statistics
    total_processed = len(responses)
    total_failed = sum(1 for r in responses if r.status == TaskStatus.FAILED)
    total_tokens = sum(r.total_tokens for r in responses)
    processing_time = (time.time() - start_time) * 1000
    
    return BatchResponse(
        batch_id=batch_id,
        status=TaskStatus.COMPLETED if total_failed == 0 else TaskStatus.FAILED,
        responses=responses,
        total_processed=total_processed,
        total_failed=total_failed,
        total_tokens=total_tokens,
        processing_time_ms=processing_time,
        pattern_used=batch_request.pattern
    )

@app.get("/api/v1/task/{task_id}")
async def get_task_status(
    task_id: str,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Get task status and result
    
    Args:
        task_id: Task ID to check
        
    Returns:
        Task status and result if available
    """
    # Get task status
    task = await task_queue.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get result if completed
    result = None
    if task.is_complete():
        result = await task_queue.get_task_result(task_id)
    
    return {
        "task_id": task_id,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "assigned_agent": task.assigned_agent,
        "result": result.to_dict() if result else None,
        "error": task.error
    }

@app.get("/api/v1/agents/status")
async def get_agents_status(authenticated: bool = Depends(verify_api_key)):
    """
    Get status of all agents
    
    Returns:
        Dictionary of agent statuses
    """
    agent_statuses = {}
    
    for agent_id, agent in agents.items():
        state = agent.get_status()
        metrics = agent.get_metrics()
        
        agent_statuses[agent_id] = {
            "agent_type": state.agent_type.value,
            "status": state.status.value,
            "current_task": state.current_task_id,
            "processed_tasks": state.processed_tasks,
            "failed_tasks": state.failed_tasks,
            "average_latency": state.average_latency,
            "is_healthy": state.is_healthy(),
            "is_available": state.is_available(),
            "metrics": metrics
        }
    
    return agent_statuses

@app.get("/api/v1/patterns/metrics")
async def get_pattern_metrics(authenticated: bool = Depends(verify_api_key)):
    """
    Get orchestration pattern metrics
    
    Returns:
        Metrics for each orchestration pattern
    """
    pattern_metrics = await orchestrator.get_pattern_metrics()
    engine_stats = await orchestrator.get_engine_stats()
    
    metrics = {}
    for pattern, metric in pattern_metrics.items():
        metrics[pattern.value] = {
            "total_executions": metric.total_executions,
            "success_rate": metric.success_rate,
            "average_latency_ms": metric.average_latency_ms,
            "average_correlation_score": metric.average_correlation_score,
            "average_replication_rate": metric.average_replication_rate,
            "average_performance_lift": metric.average_performance_lift
        }
    
    return {
        "patterns": metrics,
        "engine_stats": engine_stats
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Returns:
        System health status
    """
    try:
        system_status = await monitoring.get_system_status()
        overall_health = system_status["health"].get("overall", {})
        
        # Determine HTTP status code based on health
        status_code = 200
        if overall_health.get("status") == "unhealthy":
            status_code = 503
        elif overall_health.get("status") == "degraded":
            status_code = 200  # Still return 200 for degraded
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": overall_health.get("status", "unknown"),
                "message": overall_health.get("message", ""),
                "timestamp": system_status["last_check"],
                "components": {
                    k: v.get("status") for k, v in system_status["health"].items()
                    if k != "overall"
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
        )

@app.get("/api/v1/system/status", response_model=SystemStatus)
async def get_system_status(authenticated: bool = Depends(verify_api_key)):
    """
    Get comprehensive system status
    
    Returns:
        Detailed system status including health and metrics
    """
    system_status = await monitoring.get_system_status()
    agent_statuses = await get_agents_status(authenticated)
    
    # Determine overall status
    overall_health = system_status["health"].get("overall", {})
    status = overall_health.get("status", "unknown")
    
    return SystemStatus(
        status=status,
        health=system_status["health"],
        metrics=system_status["metrics"],
        agents=agent_statuses
    )

@app.get("/metrics")
async def get_metrics(authenticated: bool = Depends(verify_api_key)):
    """
    Get Prometheus metrics
    
    Returns:
        Prometheus formatted metrics
    """
    if not FEATURES.get("enable_metrics", True):
        raise HTTPException(status_code=501, detail="Metrics not enabled")
    
    metrics_data = monitoring.get_prometheus_metrics()
    return PlainTextResponse(content=metrics_data, media_type="text/plain")

@app.get("/api/v1/queue/stats")
async def get_queue_stats(authenticated: bool = Depends(verify_api_key)):
    """
    Get task queue statistics
    
    Returns:
        Queue statistics
    """
    stats = await task_queue.get_stats()
    return stats

@app.get("/api/v1/message-bus/stats")
async def get_message_bus_stats(authenticated: bool = Depends(verify_api_key)):
    """
    Get message bus statistics
    
    Returns:
        Message bus statistics
    """
    stats = await message_bus.get_stats()
    return stats

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": time.time()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": time.time()
        }
    )

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the API server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LLaMA3 Neuron Framework API Server")
    parser.add_argument("--host", default=API_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=API_PORT, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=API_WORKERS, help="Number of worker processes")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Start server
    logger.info(f"Starting API server on {args.host}:{args.port}")
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        workers=args.workers if not args.reload else 1,
        reload=args.reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()