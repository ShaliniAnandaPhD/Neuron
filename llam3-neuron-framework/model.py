#!/usr/bin/env python3
"""
Data Models and Schemas for LLaMA3 Neuron Framework
Defines all data structures used throughout the system
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import uuid
import json

from config import AgentType, MessagePriority, OrchestrationPattern

# ============================================================================
# BASE MODELS
# ============================================================================

@dataclass
class BaseModel:
    """Base model with common fields and methods"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary representation"""
        data = asdict(self)
        # Convert datetime objects to ISO format
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert model to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create model from dictionary"""
        # Convert ISO format strings back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

# ============================================================================
# TASK MODELS
# ============================================================================

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

@dataclass
class Task(BaseModel):
    """
    Represents a processing task in the system
    
    Attributes:
        task_type: Type of task to be performed
        payload: Task input data
        priority: Task priority level
        pattern: Orchestration pattern to use
        status: Current task status
        assigned_agent: Agent assigned to process this task
        parent_task_id: ID of parent task if this is a subtask
        retry_count: Number of retry attempts
        max_retries: Maximum retry attempts allowed
        timeout_seconds: Task timeout in seconds
        result: Task execution result
        error: Error message if task failed
        execution_time: Time taken to execute task
        token_count: Number of tokens processed
    """
    task_type: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.MEDIUM
    pattern: OrchestrationPattern = OrchestrationPattern.SEQUENTIAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 300.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    token_count: Optional[int] = None
    
    def is_complete(self) -> bool:
        """Check if task is in a terminal state"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT]
    
    def can_retry(self) -> bool:
        """Check if task can be retried"""
        return self.retry_count < self.max_retries and self.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT]

# ============================================================================
# AGENT MODELS
# ============================================================================

class AgentStatus(Enum):
    """Agent operational status"""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class AgentState(BaseModel):
    """
    Current state of an agent
    
    Attributes:
        agent_id: Unique agent identifier
        agent_type: Type of agent
        status: Current operational status
        current_task_id: ID of task currently being processed
        processed_tasks: Number of tasks processed
        failed_tasks: Number of failed tasks
        total_tokens: Total tokens processed
        average_latency: Average task processing latency
        last_heartbeat: Last heartbeat timestamp
        capabilities: Agent capabilities and features
        resource_usage: Current resource usage metrics
    """
    agent_id: str
    agent_type: AgentType
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None
    processed_tasks: int = 0
    failed_tasks: int = 0
    total_tokens: int = 0
    average_latency: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    capabilities: List[str] = field(default_factory=list)
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    def update_heartbeat(self):
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def is_available(self) -> bool:
        """Check if agent is available for tasks"""
        return self.status == AgentStatus.IDLE
    
    def is_healthy(self) -> bool:
        """Check if agent is healthy"""
        time_since_heartbeat = (datetime.utcnow() - self.last_heartbeat).seconds
        return time_since_heartbeat < 60 and self.status != AgentStatus.ERROR

# ============================================================================
# MESSAGE MODELS
# ============================================================================

@dataclass
class Message(BaseModel):
    """
    Inter-agent message
    
    Attributes:
        source_agent: ID of sending agent
        target_agent: ID of receiving agent
        message_type: Type of message
        payload: Message content
        priority: Message priority
        correlation_id: ID for correlating related messages
        reply_to: ID of message this is replying to
        ttl: Time to live in seconds
        delivered: Whether message was delivered
        acknowledged: Whether message was acknowledged
    """
    source_agent: str
    target_agent: str
    message_type: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.MEDIUM
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: int = 300  # 5 minutes default
    delivered: bool = False
    acknowledged: bool = False
    
    def is_expired(self) -> bool:
        """Check if message has expired"""
        age = (datetime.utcnow() - self.created_at).seconds
        return age > self.ttl

# ============================================================================
# ORCHESTRATION MODELS
# ============================================================================

@dataclass
class OrchestrationEvent(BaseModel):
    """
    Event in the orchestration system
    
    Attributes:
        event_type: Type of event
        source: Source of the event
        target: Target of the event
        pattern: Orchestration pattern in use
        task_id: Associated task ID
        message_id: Associated message ID
        latency_ms: Event latency in milliseconds
        success: Whether event was successful
        error_message: Error message if failed
        metrics: Additional metrics for the event
    """
    event_type: str
    source: str
    target: Optional[str] = None
    pattern: Optional[OrchestrationPattern] = None
    task_id: Optional[str] = None
    message_id: Optional[str] = None
    latency_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PatternMetrics(BaseModel):
    """
    Metrics for an orchestration pattern
    
    Attributes:
        pattern: The orchestration pattern
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        total_latency_ms: Total latency across all executions
        total_tokens: Total tokens processed
        correlation_scores: List of correlation scores
        replication_rates: List of replication rates
        performance_lifts: List of performance lift values
    """
    pattern: OrchestrationPattern
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    correlation_scores: List[float] = field(default_factory=list)
    replication_rates: List[float] = field(default_factory=list)
    performance_lifts: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @property
    def average_latency_ms(self) -> float:
        """Calculate average latency"""
        if self.total_executions == 0:
            return 0.0
        return self.total_latency_ms / self.total_executions
    
    @property
    def average_correlation_score(self) -> float:
        """Calculate average correlation score"""
        if not self.correlation_scores:
            return 0.0
        return sum(self.correlation_scores) / len(self.correlation_scores)
    
    @property
    def average_replication_rate(self) -> float:
        """Calculate average replication rate"""
        if not self.replication_rates:
            return 0.0
        return sum(self.replication_rates) / len(self.replication_rates)
    
    @property
    def average_performance_lift(self) -> float:
        """Calculate average performance lift"""
        if not self.performance_lifts:
            return 0.0
        return sum(self.performance_lifts) / len(self.performance_lifts)

# ============================================================================
# ANALYSIS MODELS
# ============================================================================

@dataclass
class AnalysisResult(BaseModel):
    """
    Result of pattern analysis
    
    Attributes:
        pattern: Analyzed pattern
        correlation_score: Pattern correlation score
        replication_rate: Pattern replication rate
        performance_lift: Performance improvement percentage
        bottlenecks: Identified bottlenecks
        recommendations: Optimization recommendations
        optimal_sequence: Optimal agent sequence
        confidence_interval: Confidence interval for metrics
        sample_size: Number of samples analyzed
    """
    pattern: OrchestrationPattern
    correlation_score: float
    replication_rate: float
    performance_lift: float
    bottlenecks: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    optimal_sequence: List[str] = field(default_factory=list)
    confidence_interval: Dict[str, tuple] = field(default_factory=dict)
    sample_size: int = 0
    
    def meets_thresholds(self, correlation_threshold: float = 0.7, 
                        replication_threshold: float = 0.85) -> bool:
        """Check if analysis meets success thresholds"""
        return (self.correlation_score >= correlation_threshold and 
                self.replication_rate >= replication_threshold)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

@dataclass
class ProcessingRequest(BaseModel):
    """
    Request for processing
    
    Attributes:
        content: Content to be processed
        content_type: Type of content (text, json, etc.)
        processing_options: Processing configuration options
        pattern: Preferred orchestration pattern
        priority: Request priority
        client_id: Client identifier
        callback_url: URL for async callbacks
        timeout_seconds: Request timeout
    """
    content: Union[str, Dict[str, Any]]
    content_type: str = "text"
    processing_options: Dict[str, Any] = field(default_factory=dict)
    pattern: Optional[OrchestrationPattern] = None
    priority: MessagePriority = MessagePriority.MEDIUM
    client_id: Optional[str] = None
    callback_url: Optional[str] = None
    timeout_seconds: float = 300.0
    
    def get_content_as_text(self) -> str:
        """Get content as text string"""
        if isinstance(self.content, str):
            return self.content
        return json.dumps(self.content)
    
    def estimate_tokens(self) -> int:
        """Estimate token count for content"""
        # Rough estimation: 1 token ≈ 4 characters
        text = self.get_content_as_text()
        return len(text) // 4

@dataclass
class ProcessingResponse(BaseModel):
    """
    Response from processing
    
    Attributes:
        request_id: ID of original request
        status: Processing status
        result: Processing result
        pattern_used: Orchestration pattern used
        agents_involved: List of agents that processed request
        total_tokens: Total tokens processed
        processing_time_ms: Total processing time
        error: Error message if failed
        warnings: List of warning messages
    """
    request_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    pattern_used: Optional[OrchestrationPattern] = None
    agents_involved: List[str] = field(default_factory=list)
    total_tokens: int = 0
    processing_time_ms: float = 0.0
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def is_success(self) -> bool:
        """Check if processing was successful"""
        return self.status == TaskStatus.COMPLETED and self.error is None

# ============================================================================
# BATCH MODELS
# ============================================================================

@dataclass
class BatchRequest(BaseModel):
    """
    Batch processing request
    
    Attributes:
        requests: List of individual requests
        batch_options: Batch processing options
        pattern: Orchestration pattern for batch
        priority: Batch priority
        client_id: Client identifier
        callback_url: URL for batch completion callback
    """
    requests: List[ProcessingRequest]
    batch_options: Dict[str, Any] = field(default_factory=dict)
    pattern: Optional[OrchestrationPattern] = None
    priority: MessagePriority = MessagePriority.BATCH
    client_id: Optional[str] = None
    callback_url: Optional[str] = None
    
    @property
    def size(self) -> int:
        """Get batch size"""
        return len(self.requests)
    
    def estimate_total_tokens(self) -> int:
        """Estimate total tokens in batch"""
        return sum(req.estimate_tokens() for req in self.requests)

@dataclass
class BatchResponse(BaseModel):
    """
    Batch processing response
    
    Attributes:
        batch_id: Batch request ID
        status: Overall batch status
        responses: Individual responses
        total_processed: Total requests processed
        total_failed: Total requests failed
        total_tokens: Total tokens processed
        processing_time_ms: Total processing time
        pattern_used: Orchestration pattern used
    """
    batch_id: str
    status: TaskStatus
    responses: List[ProcessingResponse] = field(default_factory=list)
    total_processed: int = 0
    total_failed: int = 0
    total_tokens: int = 0
    processing_time_ms: float = 0.0
    pattern_used: Optional[OrchestrationPattern] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate batch success rate"""
        if self.total_processed == 0:
            return 0.0
        return (self.total_processed - self.total_failed) / self.total_processed

# ============================================================================
# MONITORING MODELS
# ============================================================================

@dataclass
class HealthStatus(BaseModel):
    """
    System health status
    
    Attributes:
        component: Component name
        status: Health status (healthy, degraded, unhealthy)
        checks: Individual health check results
        message: Human-readable status message
        last_check: Last health check timestamp
        uptime_seconds: Component uptime in seconds
    """
    component: str
    status: str  # healthy, degraded, unhealthy
    checks: Dict[str, bool] = field(default_factory=dict)
    message: str = "OK"
    last_check: datetime = field(default_factory=datetime.utcnow)
    uptime_seconds: float = 0.0
    
    def is_healthy(self) -> bool:
        """Check if component is healthy"""
        return self.status == "healthy"
    
    def add_check(self, name: str, passed: bool):
        """Add a health check result"""
        self.checks[name] = passed
        # Update overall status based on checks
        if all(self.checks.values()):
            self.status = "healthy"
            self.message = "All checks passed"
        elif any(self.checks.values()):
            self.status = "degraded"
            failed_checks = [k for k, v in self.checks.items() if not v]
            self.message = f"Failed checks: {', '.join(failed_checks)}"
        else:
            self.status = "unhealthy"
            self.message = "All checks failed"

@dataclass
class MetricSnapshot(BaseModel):
    """
    Performance metric snapshot
    
    Attributes:
        metric_name: Name of the metric
        value: Current metric value
        unit: Metric unit
        timestamp: When metric was recorded
        labels: Additional labels/tags
        aggregation_type: How metric is aggregated (sum, avg, max, min)
    """
    metric_name: str
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    aggregation_type: str = "gauge"

# ============================================================================
# ERROR MODELS
# ============================================================================

@dataclass
class ErrorDetail(BaseModel):
    """
    Detailed error information
    
    Attributes:
        error_code: Unique error code
        error_type: Type of error
        message: Human-readable error message
        details: Additional error details
        stack_trace: Stack trace if available
        context: Error context information
        recoverable: Whether error is recoverable
        retry_after: Seconds to wait before retry
    """
    error_code: str
    error_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True
    retry_after: Optional[int] = None
    
    def to_user_message(self) -> str:
        """Get user-friendly error message"""
        if self.recoverable and self.retry_after:
            return f"{self.message}. Please retry after {self.retry_after} seconds."
        return self.message

# ============================================================================
# CACHE MODELS
# ============================================================================

@dataclass
class CacheEntry(BaseModel):
    """
    Cache entry
    
    Attributes:
        key: Cache key
        value: Cached value
        ttl_seconds: Time to live in seconds
        expires_at: Expiration timestamp
        hits: Number of cache hits
        tags: Cache tags for invalidation
    """
    key: str
    value: Any
    ttl_seconds: int = 3600
    expires_at: Optional[datetime] = None
    hits: int = 0
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate expiration time"""
        if self.expires_at is None:
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() > self.expires_at
    
    def increment_hits(self):
        """Increment hit counter"""
        self.hits += 1
        self.updated_at = datetime.utcnow()

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_task(task: Task) -> List[str]:
    """
    Validate a task object
    
    Args:
        task: Task to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not task.task_type:
        errors.append("Task type is required")
    
    if not task.payload:
        errors.append("Task payload is required")
    
    if task.timeout_seconds <= 0:
        errors.append("Timeout must be positive")
    
    if task.max_retries < 0:
        errors.append("Max retries cannot be negative")
    
    return errors

def validate_request(request: ProcessingRequest) -> List[str]:
    """
    Validate a processing request
    
    Args:
        request: Request to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not request.content:
        errors.append("Content is required")
    
    if request.content_type not in ["text", "json", "xml", "binary"]:
        errors.append(f"Invalid content type: {request.content_type}")
    
    if request.timeout_seconds <= 0:
        errors.append("Timeout must be positive")
    
    estimated_tokens = request.estimate_tokens()
    if estimated_tokens > 8192:  # LLaMA3 context window
        errors.append(f"Content too large: {estimated_tokens} tokens (max: 8192)")
    
    return errors

# ============================================================================
# TYPE EXPORTS
# ============================================================================

# Export commonly used type unions
TaskOrRequest = Union[Task, ProcessingRequest]
AgentIdentifier = Union[str, AgentState]
PatternIdentifier = Union[str, OrchestrationPattern]

# Model registry for serialization/deserialization
MODEL_REGISTRY = {
    "Task": Task,
    "AgentState": AgentState,
    "Message": Message,
    "OrchestrationEvent": OrchestrationEvent,
    "PatternMetrics": PatternMetrics,
    "AnalysisResult": AnalysisResult,
    "ProcessingRequest": ProcessingRequest,
    "ProcessingResponse": ProcessingResponse,
    "BatchRequest": BatchRequest,
    "BatchResponse": BatchResponse,
    "HealthStatus": HealthStatus,
    "MetricSnapshot": MetricSnapshot,
    "ErrorDetail": ErrorDetail,
    "CacheEntry": CacheEntry
}

def deserialize_model(model_type: str, data: Dict[str, Any]) -> BaseModel:
    """
    Deserialize a model from dictionary
    
    Args:
        model_type: Type of model to deserialize
        data: Dictionary data
        
    Returns:
        Deserialized model instance
        
    Raises:
        ValueError: If model type is unknown
    """
    if model_type not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model_class = MODEL_REGISTRY[model_type]
    return model_class.from_dict(data)