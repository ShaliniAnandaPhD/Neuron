#!/usr/bin/env python3
"""
Monitoring System for LLaMA3 Neuron Framework
Provides health checks, metrics collection, and system monitoring
"""

import asyncio
import time
import psutil
import platform
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import json

from config import (
    get_logger,
    METRICS_ENABLED,
    METRICS_PORT,
    HEALTH_CHECK_INTERVAL,
    MAX_LATENCY_MS,
    MIN_THROUGHPUT_TPS,
    MAX_ERROR_RATE,
    MAX_MEMORY_USAGE_PCT
)
from models import (
    HealthStatus,
    MetricSnapshot,
    AgentState,
    TaskStatus
)
from agents import BaseAgent
from task_queue import TaskQueue
from message_bus import MessageBus
from llama_client import LLaMAClient

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Request metrics
request_counter = Counter(
    'neuron_requests_total',
    'Total number of requests processed',
    ['method', 'status']
)

request_duration = Histogram(
    'neuron_request_duration_seconds',
    'Request processing duration',
    ['method', 'pattern']
)

# Agent metrics
agent_tasks_counter = Counter(
    'neuron_agent_tasks_total',
    'Total tasks processed by agents',
    ['agent_id', 'agent_type', 'status']
)

agent_task_duration = Histogram(
    'neuron_agent_task_duration_seconds',
    'Agent task processing duration',
    ['agent_id', 'agent_type']
)

agent_status_gauge = Gauge(
    'neuron_agent_status',
    'Current agent status',
    ['agent_id', 'agent_type']
)

# System metrics
system_health_gauge = Gauge(
    'neuron_system_health',
    'Overall system health score'
)

active_tasks_gauge = Gauge(
    'neuron_active_tasks',
    'Number of active tasks',
    ['priority']
)

queue_size_gauge = Gauge(
    'neuron_queue_size',
    'Task queue size',
    ['priority']
)

# Resource metrics
cpu_usage_gauge = Gauge(
    'neuron_cpu_usage_percent',
    'CPU usage percentage'
)

memory_usage_gauge = Gauge(
    'neuron_memory_usage_percent',
    'Memory usage percentage'
)

# ============================================================================
# HEALTH CHECKER
# ============================================================================

class HealthChecker:
    """
    System health checker
    """
    
    def __init__(self,
                 agents: Dict[str, BaseAgent],
                 task_queue: TaskQueue,
                 message_bus: MessageBus,
                 llama_client: LLaMAClient):
        """
        Initialize health checker
        
        Args:
            agents: Dictionary of agents
            task_queue: Task queue instance
            message_bus: Message bus instance
            llama_client: LLaMA client instance
        """
        self.agents = agents
        self.task_queue = task_queue
        self.message_bus = message_bus
        self.llama_client = llama_client
        
        self._start_time = time.time()
        self._last_check = datetime.utcnow()
        self._check_results: Dict[str, HealthStatus] = {}
    
    async def check_health(self) -> Dict[str, HealthStatus]:
        """
        Perform comprehensive health check
        
        Returns:
            Dictionary of health statuses by component
        """
        self._last_check = datetime.utcnow()
        
        # Check each component
        checks = {
            "agents": self._check_agents(),
            "task_queue": self._check_task_queue(),
            "message_bus": self._check_message_bus(),
            "llama_api": self._check_llama_api(),
            "system_resources": self._check_system_resources()
        }
        
        # Run all checks concurrently
        results = await asyncio.gather(
            *checks.values(),
            return_exceptions=True
        )
        
        # Process results
        for (component, _), result in zip(checks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {component}: {result}")
                self._check_results[component] = HealthStatus(
                    component=component,
                    status="unhealthy",
                    message=str(result)
                )
            else:
                self._check_results[component] = result
        
        # Calculate overall health
        self._check_results["overall"] = self._calculate_overall_health()
        
        # Update Prometheus metrics
        if METRICS_ENABLED:
            overall_score = self._calculate_health_score()
            system_health_gauge.set(overall_score)
        
        return self._check_results
    
    async def _check_agents(self) -> HealthStatus:
        """Check agent health"""
        status = HealthStatus(component="agents")
        
        total_agents = len(self.agents)
        healthy_agents = 0
        available_agents = 0
        
        for agent_id, agent in self.agents.items():
            agent_state = agent.get_status()
            
            # Check if agent is healthy
            if agent_state.is_healthy():
                healthy_agents += 1
                status.add_check(f"agent_{agent_id}_healthy", True)
            else:
                status.add_check(f"agent_{agent_id}_healthy", False)
            
            # Check if agent is available
            if agent_state.is_available():
                available_agents += 1
            
            # Update Prometheus metrics
            if METRICS_ENABLED:
                agent_status_gauge.labels(
                    agent_id=agent_id,
                    agent_type=agent_state.agent_type.value
                ).set(1 if agent_state.is_healthy() else 0)
        
        # Determine overall agent health
        if healthy_agents == total_agents:
            status.status = "healthy"
            status.message = f"All {total_agents} agents healthy"
        elif healthy_agents > total_agents * 0.5:
            status.status = "degraded"
            status.message = f"{healthy_agents}/{total_agents} agents healthy"
        else:
            status.status = "unhealthy"
            status.message = f"Only {healthy_agents}/{total_agents} agents healthy"
        
        return status
    
    async def _check_task_queue(self) -> HealthStatus:
        """Check task queue health"""
        status = HealthStatus(component="task_queue")
        
        try:
            # Get queue statistics
            stats = await self.task_queue.get_stats()
            
            # Check queue sizes
            total_queued = sum(stats.get("queue_sizes", {}).values())
            status.add_check("queue_not_overloaded", total_queued < 1000)
            
            # Check processing rate
            if "metrics" in stats:
                metrics = stats["metrics"]
                counters = metrics.get("counters", {})
                
                submitted = counters.get("task_queue.tasks_submitted", 0)
                completed = counters.get("task_queue.tasks_completed", 0)
                failed = counters.get("task_queue.tasks_failed", 0)
                
                if submitted > 0:
                    success_rate = completed / submitted
                    failure_rate = failed / submitted
                    
                    status.add_check("success_rate_acceptable", success_rate > 0.8)
                    status.add_check("failure_rate_acceptable", failure_rate < MAX_ERROR_RATE)
            
            # Update Prometheus metrics
            if METRICS_ENABLED:
                for priority, size in stats.get("queue_sizes", {}).items():
                    queue_size_gauge.labels(priority=priority).set(size)
                
                for status_name, count in stats.get("task_counts", {}).items():
                    active_tasks_gauge.labels(priority=status_name).set(count)
            
            status.status = "healthy" if all(status.checks.values()) else "degraded"
            
        except Exception as e:
            status.status = "unhealthy"
            status.message = f"Queue check failed: {str(e)}"
        
        return status
    
    async def _check_message_bus(self) -> HealthStatus:
        """Check message bus health"""
        status = HealthStatus(component="message_bus")
        
        try:
            # Get message bus statistics
            stats = await self.message_bus.get_stats()
            
            # Check message delivery
            if "counters" in stats:
                counters = stats["counters"]
                sent = counters.get("message_bus.messages_sent", 0)
                delivered = counters.get("message_bus.messages_delivered", 0)
                
                if sent > 0:
                    delivery_rate = delivered / sent
                    status.add_check("delivery_rate_acceptable", delivery_rate > 0.95)
            
            # Check queue sizes
            queue_sizes = stats.get("queue_sizes", {})
            for priority, size in queue_sizes.items():
                status.add_check(f"queue_{priority}_not_full", size < 1000)
            
            status.status = "healthy" if all(status.checks.values()) else "degraded"
            
        except Exception as e:
            status.status = "unhealthy"
            status.message = f"Message bus check failed: {str(e)}"
        
        return status
    
    async def _check_llama_api(self) -> HealthStatus:
        """Check LLaMA API health"""
        status = HealthStatus(component="llama_api")
        
        try:
            # Simple health check
            is_healthy = await self.llama_client.health_check()
            status.add_check("api_responsive", is_healthy)
            
            if is_healthy:
                status.status = "healthy"
                status.message = "LLaMA API is responsive"
            else:
                status.status = "unhealthy"
                status.message = "LLaMA API is not responding"
                
        except Exception as e:
            status.status = "unhealthy"
            status.message = f"LLaMA API check failed: {str(e)}"
        
        return status
    
    async def _check_system_resources(self) -> HealthStatus:
        """Check system resource usage"""
        status = HealthStatus(component="system_resources")
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            status.add_check("cpu_usage_acceptable", cpu_percent < 80)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            status.add_check("memory_usage_acceptable", memory_percent < MAX_MEMORY_USAGE_PCT)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            status.add_check("disk_usage_acceptable", disk_percent < 90)
            
            # Update Prometheus metrics
            if METRICS_ENABLED:
                cpu_usage_gauge.set(cpu_percent)
                memory_usage_gauge.set(memory_percent)
            
            status.status = "healthy" if all(status.checks.values()) else "degraded"
            status.message = f"CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%, Disk: {disk_percent:.1f}%"
            
        except Exception as e:
            status.status = "unhealthy"
            status.message = f"Resource check failed: {str(e)}"
        
        return status
    
    def _calculate_overall_health(self) -> HealthStatus:
        """Calculate overall system health"""
        status = HealthStatus(component="overall")
        
        # Count component statuses
        component_statuses = [s.status for s in self._check_results.values() if s.component != "overall"]
        
        healthy_count = component_statuses.count("healthy")
        degraded_count = component_statuses.count("degraded")
        unhealthy_count = component_statuses.count("unhealthy")
        
        # Determine overall status
        if unhealthy_count > 0:
            status.status = "unhealthy"
            status.message = f"{unhealthy_count} components unhealthy"
        elif degraded_count > len(component_statuses) * 0.5:
            status.status = "degraded"
            status.message = f"{degraded_count} components degraded"
        elif healthy_count == len(component_statuses):
            status.status = "healthy"
            status.message = "All components healthy"
        else:
            status.status = "degraded"
            status.message = f"{healthy_count}/{len(component_statuses)} components healthy"
        
        # Calculate uptime
        uptime_seconds = time.time() - self._start_time
        status.uptime_seconds = uptime_seconds
        
        return status
    
    def _calculate_health_score(self) -> float:
        """Calculate numerical health score (0-100)"""
        if not self._check_results:
            return 0.0
        
        scores = {
            "healthy": 100,
            "degraded": 50,
            "unhealthy": 0
        }
        
        total_score = 0
        component_count = 0
        
        for component, status in self._check_results.items():
            if component != "overall":
                total_score += scores.get(status.status, 0)
                component_count += 1
        
        return total_score / component_count if component_count > 0 else 0.0

# ============================================================================
# METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """
    Collects and aggregates system metrics
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self._metrics_history: Dict[str, List[MetricSnapshot]] = {}
        self._aggregation_window = timedelta(minutes=5)
        self._retention_period = timedelta(hours=24)
    
    def record_metric(self, metric_name: str, value: float, 
                     unit: str = "", labels: Dict[str, str] = None):
        """
        Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            labels: Additional labels
        """
        snapshot = MetricSnapshot(
            metric_name=metric_name,
            value=value,
            unit=unit,
            labels=labels or {}
        )
        
        if metric_name not in self._metrics_history:
            self._metrics_history[metric_name] = []
        
        self._metrics_history[metric_name].append(snapshot)
        
        # Clean old metrics
        self._clean_old_metrics(metric_name)
    
    def get_metric_history(self, metric_name: str, 
                          duration: Optional[timedelta] = None) -> List[MetricSnapshot]:
        """
        Get metric history
        
        Args:
            metric_name: Name of the metric
            duration: How far back to look
            
        Returns:
            List of metric snapshots
        """
        if metric_name not in self._metrics_history:
            return []
        
        if not duration:
            return self._metrics_history[metric_name]
        
        cutoff = datetime.utcnow() - duration
        return [
            m for m in self._metrics_history[metric_name]
            if m.timestamp >= cutoff
        ]
    
    def calculate_aggregates(self, metric_name: str) -> Dict[str, float]:
        """
        Calculate aggregates for a metric
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Dictionary of aggregates (min, max, avg, p50, p95, p99)
        """
        history = self.get_metric_history(metric_name, self._aggregation_window)
        
        if not history:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0
            }
        
        values = sorted([m.value for m in history])
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": self._percentile(values, 50),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99)
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0
        
        index = int(len(values) * percentile / 100)
        return values[min(index, len(values) - 1)]
    
    def _clean_old_metrics(self, metric_name: str):
        """Clean metrics older than retention period"""
        cutoff = datetime.utcnow() - self._retention_period
        
        self._metrics_history[metric_name] = [
            m for m in self._metrics_history[metric_name]
            if m.timestamp >= cutoff
        ]

# ============================================================================
# MONITORING SERVICE
# ============================================================================

class MonitoringService:
    """
    Main monitoring service that coordinates health checks and metrics
    """
    
    def __init__(self,
                 agents: Dict[str, BaseAgent],
                 task_queue: TaskQueue,
                 message_bus: MessageBus,
                 llama_client: LLaMAClient):
        """
        Initialize monitoring service
        
        Args:
            agents: Dictionary of agents
            task_queue: Task queue instance
            message_bus: Message bus instance
            llama_client: LLaMA client instance
        """
        self.health_checker = HealthChecker(agents, task_queue, message_bus, llama_client)
        self.metrics_collector = MetricsCollector()
        
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start monitoring service"""
        logger.info("Starting monitoring service")
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop monitoring service"""
        logger.info("Stopping monitoring service")
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                # Perform health check
                health_results = await self.health_checker.check_health()
                
                # Record health metrics
                for component, status in health_results.items():
                    health_score = 100 if status.status == "healthy" else 50 if status.status == "degraded" else 0
                    self.metrics_collector.record_metric(
                        f"health_{component}",
                        health_score,
                        unit="score",
                        labels={"component": component}
                    )
                
                # Sleep until next check
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status
        
        Returns:
            Dictionary containing health and metrics
        """
        # Get latest health check results
        health = self.health_checker._check_results
        
        # Get key metrics
        metrics = {}
        for metric_name in ["health_overall", "health_agents", "health_task_queue"]:
            aggregates = self.metrics_collector.calculate_aggregates(metric_name)
            metrics[metric_name] = aggregates
        
        return {
            "health": {k: v.to_dict() for k, v in health.items()},
            "metrics": metrics,
            "last_check": self.health_checker._last_check.isoformat()
        }
    
    def get_prometheus_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format
        
        Returns:
            Prometheus formatted metrics
        """
        return generate_latest()