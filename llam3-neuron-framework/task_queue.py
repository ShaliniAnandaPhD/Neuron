#!/usr/bin/env python3
"""
Task Queue for LLaMA3 Neuron Framework
Manages task queuing, scheduling, and distribution
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import uuid
import heapq
from datetime import datetime, timedelta

from config import (
    MessagePriority,
    get_logger,
    REDIS_URL,
    REDIS_TASK_PREFIX,
    REDIS_RESULT_PREFIX,
    TASK_EXPIRY,
    RESULT_EXPIRY
)
from models import Task, TaskStatus, ProcessingResponse
from utils import Metrics, async_retry

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# TASK QUEUE INTERFACE
# ============================================================================

class TaskQueue:
    """
    Priority-based task queue with Redis persistence
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize task queue
        
        Args:
            redis_url: Redis connection URL (optional)
        """
        self.redis_url = redis_url or REDIS_URL
        self._redis_client = None
        
        # In-memory queues for each priority
        self._priority_queues: Dict[MessagePriority, List[tuple]] = {
            priority: [] for priority in MessagePriority
        }
        
        # Task tracking
        self._tasks: Dict[str, Task] = {}
        self._processing_tasks: Dict[str, str] = {}  # task_id -> agent_id
        self._completed_tasks: Dict[str, ProcessingResponse] = {}
        
        # Metrics
        self._metrics = Metrics("task_queue")
        
        # Callbacks
        self._task_callbacks: Dict[str, Callable] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Connect to Redis if URL provided"""
        if self.redis_url and self.redis_url != "redis://localhost:6379":
            try:
                import redis.asyncio as redis
                self._redis_client = await redis.from_url(self.redis_url)
                logger.info(f"Connected to Redis at {self.redis_url}")
                
                # Load existing tasks from Redis
                await self._load_tasks_from_redis()
                
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory queue.")
    
    async def close(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
    
    async def submit_task(self, task: Task, callback: Optional[Callable] = None) -> str:
        """
        Submit a task to the queue
        
        Args:
            task: Task to submit
            callback: Optional callback for task completion
            
        Returns:
            Task ID
        """
        async with self._lock:
            # Set task status
            task.status = TaskStatus.QUEUED
            task.updated_at = datetime.utcnow()
            
            # Store task
            self._tasks[task.id] = task
            
            # Store callback if provided
            if callback:
                self._task_callbacks[task.id] = callback
            
            # Add to priority queue
            # Use negative priority for min heap (higher priority = lower number)
            priority_value = task.priority.value
            timestamp = time.time()
            heapq.heappush(
                self._priority_queues[task.priority],
                (priority_value, timestamp, task.id)
            )
            
            # Persist to Redis if available
            if self._redis_client:
                await self._persist_task(task)
            
            # Update metrics
            await self._metrics.increment("tasks_submitted")
            await self._metrics.increment(f"tasks_submitted_{task.priority.name.lower()}")
            
            logger.debug(f"Submitted task {task.id} with priority {task.priority.name}")
            
            return task.id
    
    async def get_task(self, agent_id: str, agent_types: List[str] = None) -> Optional[Task]:
        """
        Get next task for an agent
        
        Args:
            agent_id: Agent requesting task
            agent_types: Types of tasks the agent can handle
            
        Returns:
            Next task or None
        """
        async with self._lock:
            # Try each priority queue in order
            for priority in MessagePriority:
                queue = self._priority_queues[priority]
                
                # Try to find a suitable task
                temp_items = []
                found_task = None
                
                while queue and not found_task:
                    priority_val, timestamp, task_id = heapq.heappop(queue)
                    
                    if task_id in self._tasks:
                        task = self._tasks[task_id]
                        
                        # Check if task is still valid
                        if task.status == TaskStatus.QUEUED:
                            # Check if agent can handle this task type
                            if not agent_types or task.task_type in agent_types:
                                found_task = task
                                break
                    
                    temp_items.append((priority_val, timestamp, task_id))
                
                # Restore items to queue
                for item in temp_items:
                    if not found_task or item[2] != found_task.id:
                        heapq.heappush(queue, item)
                
                if found_task:
                    # Mark task as processing
                    found_task.status = TaskStatus.PROCESSING
                    found_task.assigned_agent = agent_id
                    found_task.updated_at = datetime.utcnow()
                    
                    # Track processing
                    self._processing_tasks[found_task.id] = agent_id
                    
                    # Update in Redis
                    if self._redis_client:
                        await self._persist_task(found_task)
                    
                    # Update metrics
                    await self._metrics.increment("tasks_assigned")
                    await self._metrics.increment(f"tasks_assigned_{agent_id}")
                    
                    logger.debug(f"Assigned task {found_task.id} to agent {agent_id}")
                    
                    return found_task
            
            return None
    
    async def complete_task(self, task_id: str, response: ProcessingResponse):
        """
        Mark task as completed
        
        Args:
            task_id: Task ID
            response: Processing response
        """
        async with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Task {task_id} not found")
                return
            
            task = self._tasks[task_id]
            
            # Update task status
            task.status = response.status
            task.result = response.result
            task.error = response.error
            task.execution_time = response.processing_time_ms / 1000.0
            task.token_count = response.total_tokens
            task.updated_at = datetime.utcnow()
            
            # Remove from processing
            if task_id in self._processing_tasks:
                del self._processing_tasks[task_id]
            
            # Store response
            self._completed_tasks[task_id] = response
            
            # Update in Redis
            if self._redis_client:
                await self._persist_task(task)
                await self._persist_result(task_id, response)
            
            # Update metrics
            if response.status == TaskStatus.COMPLETED:
                await self._metrics.increment("tasks_completed")
            else:
                await self._metrics.increment("tasks_failed")
            
            await self._metrics.record("task_processing_time_ms", response.processing_time_ms)
            
            # Trigger callback if exists
            if task_id in self._task_callbacks:
                callback = self._task_callbacks[task_id]
                del self._task_callbacks[task_id]
                
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(response)
                    else:
                        callback(response)
                except Exception as e:
                    logger.error(f"Error in task callback: {e}")
            
            logger.debug(f"Completed task {task_id} with status {response.status}")
    
    async def requeue_task(self, task_id: str):
        """
        Requeue a task (e.g., after agent failure)
        
        Args:
            task_id: Task ID to requeue
        """
        async with self._lock:
            if task_id not in self._tasks:
                logger.warning(f"Task {task_id} not found")
                return
            
            task = self._tasks[task_id]
            
            # Check if task can be retried
            if not task.can_retry():
                logger.warning(f"Task {task_id} cannot be retried")
                task.status = TaskStatus.FAILED
                task.error = "Max retries exceeded"
                return
            
            # Update task for retry
            task.status = TaskStatus.QUEUED
            task.retry_count += 1
            task.assigned_agent = None
            task.updated_at = datetime.utcnow()
            
            # Remove from processing
            if task_id in self._processing_tasks:
                del self._processing_tasks[task_id]
            
            # Re-add to queue with lower priority
            new_priority = min(
                MessagePriority.LOW,
                MessagePriority(task.priority.value + 1)
            )
            
            priority_value = new_priority.value
            timestamp = time.time()
            heapq.heappush(
                self._priority_queues[new_priority],
                (priority_value, timestamp, task.id)
            )
            
            # Update in Redis
            if self._redis_client:
                await self._persist_task(task)
            
            # Update metrics
            await self._metrics.increment("tasks_requeued")
            
            logger.debug(f"Requeued task {task_id} (retry {task.retry_count})")
    
    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """
        Get task status
        
        Args:
            task_id: Task ID
            
        Returns:
            Task or None
        """
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def get_task_result(self, task_id: str) -> Optional[ProcessingResponse]:
        """
        Get task result
        
        Args:
            task_id: Task ID
            
        Returns:
            Processing response or None
        """
        async with self._lock:
            # Check in-memory first
            if task_id in self._completed_tasks:
                return self._completed_tasks[task_id]
            
            # Try Redis
            if self._redis_client:
                try:
                    key = f"{REDIS_RESULT_PREFIX}{task_id}"
                    data = await self._redis_client.get(key)
                    if data:
                        return ProcessingResponse.from_dict(json.loads(data))
                except Exception as e:
                    logger.error(f"Failed to get result from Redis: {e}")
            
            return None
    
    async def cleanup_expired_tasks(self):
        """Clean up expired tasks"""
        async with self._lock:
            now = datetime.utcnow()
            expired_tasks = []
            
            for task_id, task in self._tasks.items():
                # Check if task is expired
                age = (now - task.created_at).total_seconds()
                if age > task.timeout_seconds and task.status in [TaskStatus.QUEUED, TaskStatus.PROCESSING]:
                    expired_tasks.append(task_id)
            
            # Mark expired tasks as timeout
            for task_id in expired_tasks:
                task = self._tasks[task_id]
                task.status = TaskStatus.TIMEOUT
                task.error = "Task timeout"
                task.updated_at = now
                
                # Remove from processing
                if task_id in self._processing_tasks:
                    del self._processing_tasks[task_id]
                
                # Update metrics
                await self._metrics.increment("tasks_timeout")
                
                logger.warning(f"Task {task_id} timed out")
    
    async def _persist_task(self, task: Task):
        """Persist task to Redis"""
        if not self._redis_client:
            return
        
        try:
            key = f"{REDIS_TASK_PREFIX}{task.id}"
            await self._redis_client.setex(
                key,
                TASK_EXPIRY,
                task.to_json()
            )
        except Exception as e:
            logger.error(f"Failed to persist task to Redis: {e}")
    
    async def _persist_result(self, task_id: str, response: ProcessingResponse):
        """Persist result to Redis"""
        if not self._redis_client:
            return
        
        try:
            key = f"{REDIS_RESULT_PREFIX}{task_id}"
            await self._redis_client.setex(
                key,
                RESULT_EXPIRY,
                response.to_json()
            )
        except Exception as e:
            logger.error(f"Failed to persist result to Redis: {e}")
    
    async def _load_tasks_from_redis(self):
        """Load existing tasks from Redis"""
        if not self._redis_client:
            return
        
        try:
            # Load tasks
            pattern = f"{REDIS_TASK_PREFIX}*"
            cursor = 0
            
            while True:
                cursor, keys = await self._redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                for key in keys:
                    try:
                        data = await self._redis_client.get(key)
                        if data:
                            task = Task.from_dict(json.loads(data))
                            self._tasks[task.id] = task
                            
                            # Re-queue if still pending
                            if task.status == TaskStatus.QUEUED:
                                priority_value = task.priority.value
                                timestamp = task.created_at.timestamp()
                                heapq.heappush(
                                    self._priority_queues[task.priority],
                                    (priority_value, timestamp, task.id)
                                )
                    except Exception as e:
                        logger.error(f"Failed to load task from Redis: {e}")
                
                if cursor == 0:
                    break
            
            logger.info(f"Loaded {len(self._tasks)} tasks from Redis")
            
        except Exception as e:
            logger.error(f"Failed to load tasks from Redis: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics
        
        Returns:
            Dictionary of statistics
        """
        async with self._lock:
            stats = await self._metrics.get_all()
            
            # Add queue sizes
            stats['queue_sizes'] = {
                priority.name: len(queue)
                for priority, queue in self._priority_queues.items()
            }
            
            # Add task counts by status
            status_counts = {}
            for task in self._tasks.values():
                status = task.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            stats['task_counts'] = status_counts
            stats['processing_count'] = len(self._processing_tasks)
            stats['total_tasks'] = len(self._tasks)
            
            return stats

# ============================================================================
# SCHEDULED TASK QUEUE
# ============================================================================

class ScheduledTaskQueue(TaskQueue):
    """
    Task queue with scheduled task support
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize scheduled task queue"""
        super().__init__(redis_url)
        self._scheduled_tasks: List[tuple] = []  # (run_at, task_id)
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the scheduler"""
        await super().connect()
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduled task queue started")
    
    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        await super().close()
        logger.info("Scheduled task queue stopped")
    
    async def schedule_task(self, task: Task, run_at: datetime) -> str:
        """
        Schedule a task to run at a specific time
        
        Args:
            task: Task to schedule
            run_at: When to run the task
            
        Returns:
            Task ID
        """
        async with self._lock:
            # Store task
            self._tasks[task.id] = task
            task.status = TaskStatus.PENDING
            task.metadata['scheduled_at'] = run_at.isoformat()
            
            # Add to scheduled queue
            heapq.heappush(
                self._scheduled_tasks,
                (run_at.timestamp(), task.id)
            )
            
            # Persist to Redis
            if self._redis_client:
                await self._persist_task(task)
            
            # Update metrics
            await self._metrics.increment("tasks_scheduled")
            
            logger.debug(f"Scheduled task {task.id} to run at {run_at}")
            
            return task.id
    
    async def schedule_recurring_task(self, 
                                    task: Task, 
                                    interval: timedelta,
                                    start_at: Optional[datetime] = None) -> str:
        """
        Schedule a recurring task
        
        Args:
            task: Task template to schedule
            interval: Recurrence interval
            start_at: When to start (default: now)
            
        Returns:
            Task ID
        """
        if not start_at:
            start_at = datetime.utcnow()
        
        # Mark as recurring
        task.metadata['recurring'] = True
        task.metadata['interval_seconds'] = interval.total_seconds()
        
        # Schedule first occurrence
        return await self.schedule_task(task, start_at)
    
    async def _scheduler_loop(self):
        """Process scheduled tasks"""
        while self._running:
            try:
                async with self._lock:
                    now = datetime.utcnow().timestamp()
                    
                    # Process due tasks
                    while self._scheduled_tasks:
                        run_at, task_id = self._scheduled_tasks[0]
                        
                        if run_at > now:
                            break
                        
                        # Remove from scheduled queue
                        heapq.heappop(self._scheduled_tasks)
                        
                        if task_id in self._tasks:
                            task = self._tasks[task_id]
                            
                            # Submit to regular queue
                            task.status = TaskStatus.QUEUED
                            await self.submit_task(task)
                            
                            # Handle recurring tasks
                            if task.metadata.get('recurring'):
                                interval = task.metadata.get('interval_seconds', 3600)
                                next_run = datetime.utcnow() + timedelta(seconds=interval)
                                
                                # Create new task instance
                                new_task = Task(
                                    task_type=task.task_type,
                                    payload=task.payload,
                                    priority=task.priority,
                                    pattern=task.pattern,
                                    metadata=task.metadata.copy()
                                )
                                
                                # Schedule next occurrence
                                await self.schedule_task(new_task, next_run)
                
                # Sleep until next task or 1 second
                if self._scheduled_tasks:
                    next_run = self._scheduled_tasks[0][0]
                    sleep_time = min(max(0, next_run - datetime.utcnow().timestamp()), 1.0)
                else:
                    sleep_time = 1.0
                
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(1)

# ============================================================================
# DISTRIBUTED TASK QUEUE
# ============================================================================

class DistributedTaskQueue(ScheduledTaskQueue):
    """
    Distributed task queue using Redis for coordination
    """
    
    def __init__(self, redis_url: str, instance_id: str):
        """
        Initialize distributed task queue
        
        Args:
            redis_url: Redis connection URL
            instance_id: Unique instance identifier
        """
        super().__init__(redis_url)
        self.instance_id = instance_id
        self._claim_prefix = f"{REDIS_PREFIX}claims:{instance_id}:"
    
    async def get_task(self, agent_id: str, agent_types: List[str] = None) -> Optional[Task]:
        """
        Get next task with distributed coordination
        
        Args:
            agent_id: Agent requesting task
            agent_types: Types of tasks the agent can handle
            
        Returns:
            Next task or None
        """
        if not self._redis_client:
            return await super().get_task(agent_id, agent_types)
        
        # Try to claim a task from Redis
        try:
            # Get all pending tasks
            pattern = f"{REDIS_TASK_PREFIX}*"
            cursor = 0
            
            while True:
                cursor, keys = await self._redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                for key in keys:
                    task_id = key.decode().replace(REDIS_TASK_PREFIX, "")
                    
                    # Try to claim the task
                    claim_key = f"{self._claim_prefix}{task_id}"
                    
                    # Atomic claim with expiry
                    claimed = await self._redis_client.set(
                        claim_key,
                        agent_id,
                        nx=True,  # Only if not exists
                        ex=300    # 5 minute expiry
                    )
                    
                    if claimed:
                        # Load task data
                        data = await self._redis_client.get(key)
                        if data:
                            task = Task.from_dict(json.loads(data))
                            
                            # Check if suitable for agent
                            if task.status == TaskStatus.QUEUED:
                                if not agent_types or task.task_type in agent_types:
                                    # Update task
                                    task.status = TaskStatus.PROCESSING
                                    task.assigned_agent = agent_id
                                    task.updated_at = datetime.utcnow()
                                    
                                    # Persist updates
                                    await self._persist_task(task)
                                    
                                    # Track locally
                                    self._tasks[task.id] = task
                                    self._processing_tasks[task.id] = agent_id
                                    
                                    return task
                        
                        # Release claim if not suitable
                        await self._redis_client.delete(claim_key)
                
                if cursor == 0:
                    break
                    
        except Exception as e:
            logger.error(f"Error getting distributed task: {e}")
        
        # Fallback to local queue
        return await super().get_task(agent_id, agent_types)
    
    async def release_claims(self):
        """Release all claims held by this instance"""
        if not self._redis_client:
            return
        
        try:
            pattern = f"{self._claim_prefix}*"
            cursor = 0
            
            while True:
                cursor, keys = await self._redis_client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                for key in keys:
                    await self._redis_client.delete(key)
                
                if cursor == 0:
                    break
                    
            logger.info(f"Released all claims for instance {self.instance_id}")
            
        except Exception as e:
            logger.error(f"Error releasing claims: {e}")
    
    async def get_distributed_stats(self) -> Dict[str, Any]:
        """
        Get statistics across all instances
        
        Returns:
            Aggregated statistics
        """
        stats = await self.get_stats()
        
        if self._redis_client:
            try:
                # Count total tasks across instances
                pattern = f"{REDIS_TASK_PREFIX}*"
                cursor = 0
                total_tasks = 0
                
                while True:
                    cursor, keys = await self._redis_client.scan(
                        cursor,
                        match=pattern,
                        count=100
                    )
                    total_tasks += len(keys)
                    
                    if cursor == 0:
                        break
                
                stats['distributed_total_tasks'] = total_tasks
                
                # Count active claims
                pattern = f"{REDIS_PREFIX}claims:*"
                cursor = 0
                active_claims = 0
                
                while True:
                    cursor, keys = await self._redis_client.scan(
                        cursor,
                        match=pattern,
                        count=100
                    )
                    active_claims += len(keys)
                    
                    if cursor == 0:
                        break
                
                stats['distributed_active_claims'] = active_claims
                
            except Exception as e:
                logger.error(f"Error getting distributed stats: {e}")
        
        return stats

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_task_queue(
    queue_type: str = "basic",
    redis_url: Optional[str] = None,
    **kwargs
) -> TaskQueue:
    """
    Create task queue instance
    
    Args:
        queue_type: Type of queue ("basic", "scheduled", "distributed")
        redis_url: Redis connection URL
        **kwargs: Additional configuration
        
    Returns:
        Task queue instance
    """
    if queue_type == "distributed":
        instance_id = kwargs.get('instance_id', f"neuron_{int(time.time())}")
        return DistributedTaskQueue(redis_url or REDIS_URL, instance_id)
    elif queue_type == "scheduled":
        return ScheduledTaskQueue(redis_url)
    else:
        return TaskQueue(redis_url)