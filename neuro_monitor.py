"""
neuro_monitor.py - Monitoring System for Neuron Framework

This module implements the monitoring and observability functionality for the
Neuron framework. It collects metrics from agents, circuits, and system
components, providing insights into performance, resource usage, and behavior.

The monitoring system is inspired by how neuroscientists observe and measure
brain activity to understand neural circuits and diagnose issues.
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .config import config
from .exceptions import MonitoringError
from .types import AgentID, CircuitID

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """
    Types of metrics collected by the monitoring system.
    
    This categorizes metrics based on what they measure and how
    they should be processed and visualized.
    """
    COUNTER = "counter"       # Monotonically increasing value
    GAUGE = "gauge"           # Value that can go up and down
    HISTOGRAM = "histogram"   # Distribution of values
    TIMER = "timer"           # Duration of operations
    EVENT = "event"           # Discrete event occurrence


@dataclass
class Metric:
    """
    Represents a collected metric.
    
    A metric includes metadata about what it measures and how it
    should be interpreted, along with the actual measured values.
    """
    name: str                     # Metric name
    metric_type: MetricType       # Type of metric
    value: Any                    # Measured value
    tags: Dict[str, str] = field(default_factory=dict)  # Tags for filtering/grouping
    timestamp: float = field(default_factory=time.time)  # When the metric was collected
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "tags": self.tags,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Metric':
        """Create from dictionary representation."""
        return cls(
            name=data["name"],
            metric_type=MetricType(data["type"]),
            value=data["value"],
            tags=data.get("tags", {}),
            timestamp=data.get("timestamp", time.time())
        )


class AlertLevel(Enum):
    """
    Severity levels for monitoring alerts.
    
    This defines how urgent and important an alert is, influencing
    how it's presented and processed.
    """
    INFO = "info"         # Informational, no action required
    WARNING = "warning"   # Potential issue, may require attention
    ERROR = "error"       # Significant issue, requires attention
    CRITICAL = "critical" # Severe issue, requires immediate attention


@dataclass
class Alert:
    """
    Represents a monitoring alert.
    
    Alerts are generated when metrics or events indicate a potential
    issue or noteworthy condition in the system.
    """
    name: str                 # Alert name
    level: AlertLevel         # Severity level
    message: str              # Alert message
    source: str               # Component that generated the alert
    tags: Dict[str, str] = field(default_factory=dict)  # Tags for filtering/grouping
    timestamp: float = field(default_factory=time.time)  # When the alert was generated
    related_metrics: List[str] = field(default_factory=list)  # Related metric names
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "related_metrics": self.related_metrics
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        """Create from dictionary representation."""
        return cls(
            name=data["name"],
            level=AlertLevel(data["level"]),
            message=data["message"],
            source=data["source"],
            tags=data.get("tags", {}),
            timestamp=data.get("timestamp", time.time()),
            related_metrics=data.get("related_metrics", [])
        )


@dataclass
class HealthStatus:
    """
    Represents the health status of a component.
    
    Health status provides a high-level assessment of a component's
    condition, indicating whether it's functioning properly.
    """
    component: str               # Component name
    status: str                  # Status string (e.g., "healthy", "degraded", "failing")
    details: Dict[str, Any] = field(default_factory=dict)  # Additional details
    timestamp: float = field(default_factory=time.time)  # When the status was assessed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "component": self.component,
            "status": self.status,
            "details": self.details,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HealthStatus':
        """Create from dictionary representation."""
        return cls(
            component=data["component"],
            status=data["status"],
            details=data.get("details", {}),
            timestamp=data.get("timestamp", time.time())
        )


class AlertRule:
    """
    Rule for generating alerts based on metrics.
    
    Alert rules define conditions under which metrics or events
    should trigger alerts, allowing for automated monitoring.
    """
    
    def __init__(self, name: str, metric_pattern: str, 
                condition: Callable[[Any], bool], alert_level: AlertLevel,
                message_template: str, cooldown: float = 300.0):
        """
        Initialize an alert rule.
        
        Args:
            name: Name of the rule
            metric_pattern: Pattern for matching metric names
            condition: Function that takes a metric value and returns True if the rule should trigger
            alert_level: Severity level for generated alerts
            message_template: Template for alert messages
            cooldown: Minimum time between alerts from this rule (seconds)
        """
        self.name = name
        self.metric_pattern = metric_pattern
        self.condition = condition
        self.alert_level = alert_level
        self.message_template = message_template
        self.cooldown = cooldown
        self.last_triggered = 0.0
    
    def matches_metric(self, metric_name: str) -> bool:
        """
        Check if a metric matches this rule's pattern.
        
        Args:
            metric_name: Name of the metric to check
            
        Returns:
            True if the metric matches, False otherwise
        """
        # Simple wildcard matching (can be enhanced with regex)
        if self.metric_pattern.endswith('*'):
            prefix = self.metric_pattern[:-1]
            return metric_name.startswith(prefix)
        return metric_name == self.metric_pattern
    
    def check_condition(self, metric: Metric) -> bool:
        """
        Check if a metric's value triggers this rule.
        
        Args:
            metric: Metric to check
            
        Returns:
            True if the rule is triggered, False otherwise
        """
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_triggered < self.cooldown:
            return False
        
        # Check condition
        try:
            if self.condition(metric.value):
                self.last_triggered = current_time
                return True
        except Exception as e:
            logger.error(f"Error checking alert condition for {metric.name}: {e}")
        
        return False
    
    def generate_alert(self, metric: Metric) -> Alert:
        """
        Generate an alert for a triggering metric.
        
        Args:
            metric: Metric that triggered the rule
            
        Returns:
            Generated alert
        """
        # Replace placeholders in message template
        message = self.message_template
        message = message.replace("{metric_name}", metric.name)
        message = message.replace("{value}", str(metric.value))
        
        for tag_key, tag_value in metric.tags.items():
            message = message.replace(f"{{{tag_key}}}", str(tag_value))
        
        # Create the alert
        alert = Alert(
            name=self.name,
            level=self.alert_level,
            message=message,
            source=metric.tags.get("component", "unknown"),
            tags=metric.tags,
            related_metrics=[metric.name]
        )
        
        return alert


class MetricStore:
    """
    Stores and manages collected metrics.
    
    The MetricStore is responsible for storing metrics, handling
    retention policies, and providing efficient query capabilities.
    """
    
    def __init__(self, max_retention: int = 86400):
        """
        Initialize a metric store.
        
        Args:
            max_retention: Maximum retention period in seconds
        """
        self._metrics = {}  # metric_name -> List of (timestamp, value) pairs
        self._tags = {}  # metric_name -> Dict of tag_name -> tag_value
        self._max_retention = max_retention
        self._lock = threading.RLock()
        
        # Storage for recent metric values
        self._latest_values = {}  # metric_name -> (timestamp, value) pair
        
        logger.debug(f"Initialized MetricStore with {max_retention}s retention")
    
    def store_metric(self, metric: Metric) -> None:
        """
        Store a metric.
        
        Args:
            metric: Metric to store
        """
        with self._lock:
            # Store the metric value
            if metric.name not in self._metrics:
                self._metrics[metric.name] = []
            
            self._metrics[metric.name].append((metric.timestamp, metric.value))
            
            # Store tags
            self._tags[metric.name] = metric.tags
            
            # Update latest value
            self._latest_values[metric.name] = (metric.timestamp, metric.value)
            
            # Apply retention policy
            self._apply_retention(metric.name)
    
    def _apply_retention(self, metric_name: str) -> None:
        """
        Apply retention policy to a metric.
        
        Args:
            metric_name: Name of the metric to apply retention to
        """
        if metric_name not in self._metrics:
            return
        
        # Get the current time
        current_time = time.time()
        
        # Remove values older than max_retention
        cutoff_time = current_time - self._max_retention
        self._metrics[metric_name] = [
            (ts, val) for ts, val in self._metrics[metric_name]
            if ts >= cutoff_time
        ]
        
        # If all values were removed, clean up
        if not self._metrics[metric_name]:
            del self._metrics[metric_name]
            if metric_name in self._tags:
                del self._tags[metric_name]
            if metric_name in self._latest_values:
                del self._latest_values[metric_name]
    
    def get_metric_value(self, metric_name: str, 
                       time_range: Optional[Tuple[float, float]] = None,
                       aggregation: Optional[str] = None) -> Optional[Any]:
        """
        Get a metric value.
        
        Args:
            metric_name: Name of the metric
            time_range: Optional (start, end) time range
            aggregation: Optional aggregation function (mean, max, min, etc.)
            
        Returns:
            Metric value or aggregated values, or None if not found
        """
        with self._lock:
            if metric_name not in self._metrics:
                return None
            
            # Get values in the specified time range
            values = self._metrics[metric_name]
            
            if time_range:
                start_time, end_time = time_range
                values = [
                    (ts, val) for ts, val in values
                    if start_time <= ts <= end_time
                ]
            
            if not values:
                return None
            
            # Return values based on aggregation
            if aggregation:
                if aggregation == "latest":
                    return values[-1][1]
                
                value_list = [val for _, val in values]
                
                if aggregation == "mean":
                    return sum(value_list) / len(value_list)
                elif aggregation == "max":
                    return max(value_list)
                elif aggregation == "min":
                    return min(value_list)
                elif aggregation == "sum":
                    return sum(value_list)
                elif aggregation == "count":
                    return len(value_list)
            
            # Default: return all values
            return values
    
    def get_latest_value(self, metric_name: str) -> Optional[Any]:
        """
        Get the latest value of a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Latest value of the metric, or None if not found
        """
        with self._lock:
            if metric_name in self._latest_values:
                return self._latest_values[metric_name][1]
            return None
    
    def get_metrics_by_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        Get metrics matching a name pattern.
        
        Args:
            pattern: Pattern to match metric names against
            
        Returns:
            Dictionary of metric_name -> latest_value
        """
        with self._lock:
            results = {}
            
            # Simple wildcard matching
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                for name, (_, value) in self._latest_values.items():
                    if name.startswith(prefix):
                        results[name] = value
            else:
                # Exact match
                if pattern in self._latest_values:
                    results[pattern] = self._latest_values[pattern][1]
            
            return results
    
    def get_metrics_by_tags(self, tags: Dict[str, str]) -> Dict[str, Any]:
        """
        Get metrics with matching tags.
        
        Args:
            tags: Tags to match
            
        Returns:
            Dictionary of metric_name -> latest_value
        """
        with self._lock:
            results = {}
            
            for name, metric_tags in self._tags.items():
                # Check if all specified tags match
                match = True
                for tag_key, tag_value in tags.items():
                    if tag_key not in metric_tags or metric_tags[tag_key] != tag_value:
                        match = False
                        break
                
                if match and name in self._latest_values:
                    results[name] = self._latest_values[name][1]
            
            return results
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        with self._lock:
            self._metrics.clear()
            self._tags.clear()
            self._latest_values.clear()


class AlertManager:
    """
    Manages alert rules and generated alerts.
    
    The AlertManager is responsible for defining alert rules,
    checking metrics against those rules, and handling triggered alerts.
    """
    
    def __init__(self, max_alerts: int = 1000):
        """
        Initialize an alert manager.
        
        Args:
            max_alerts: Maximum number of alerts to store
        """
        self._rules = []  # List of AlertRule objects
        self._alerts = []  # List of Alert objects
        self._alert_handlers = []  # List of alert handler functions
        self._max_alerts = max_alerts
        self._lock = threading.RLock()
        
        logger.debug(f"Initialized AlertManager with {max_alerts} max alerts")
    
    def add_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule.
        
        Args:
            rule: Alert rule to add
        """
        with self._lock:
            self._rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove an alert rule.
        
        Args:
            rule_name: Name of the rule to remove
            
        Returns:
            True if the rule was removed, False if not found
        """
        with self._lock:
            for i, rule in enumerate(self._rules):
                if rule.name == rule_name:
                    del self._rules[i]
                    return True
            return False
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        Add an alert handler function.
        
        Args:
            handler: Function to call when an alert is triggered
        """
        with self._lock:
            self._alert_handlers.append(handler)
    
    def check_metric(self, metric: Metric) -> List[Alert]:
        """
        Check a metric against all alert rules.
        
        Args:
            metric: Metric to check
            
        Returns:
            List of triggered alerts
        """
        triggered_alerts = []
        
        with self._lock:
            for rule in self._rules:
                if rule.matches_metric(metric.name) and rule.check_condition(metric):
                    alert = rule.generate_alert(metric)
                    self._alerts.append(alert)
                    triggered_alerts.append(alert)
                    
                    # Call alert handlers
                    for handler in self._alert_handlers:
                        try:
                            handler(alert)
                        except Exception as e:
                            logger.error(f"Error in alert handler: {e}")
            
            # Trim alerts if needed
            if len(self._alerts) > self._max_alerts:
                self._alerts = self._alerts[-self._max_alerts:]
        
        return triggered_alerts
    
    def get_alerts(self, level: Optional[AlertLevel] = None, 
                 time_range: Optional[Tuple[float, float]] = None,
                 max_alerts: Optional[int] = None) -> List[Alert]:
        """
        Get stored alerts.
        
        Args:
            level: Optional filter by alert level
            time_range: Optional (start, end) time range
            max_alerts: Maximum number of alerts to return
            
        Returns:
            List of matching alerts
        """
        with self._lock:
            # Filter alerts
            filtered_alerts = self._alerts
            
            if level:
                filtered_alerts = [a for a in filtered_alerts if a.level == level]
            
            if time_range:
                start_time, end_time = time_range
                filtered_alerts = [
                    a for a in filtered_alerts
                    if start_time <= a.timestamp <= end_time
                ]
            
            # Sort by timestamp (newest first)
            filtered_alerts = sorted(filtered_alerts, key=lambda a: a.timestamp, reverse=True)
            
            # Apply limit
            if max_alerts is not None:
                filtered_alerts = filtered_alerts[:max_alerts]
            
            return filtered_alerts
    
    def clear_alerts(self) -> None:
        """Clear all stored alerts."""
        with self._lock:
            self._alerts.clear()


class HealthChecker:
    """
    Monitors the health of system components.
    
    The HealthChecker assesses the health of various components
    based on their metrics and behavior, providing a high-level
    view of system status.
    """
    
    def __init__(self, metric_store: MetricStore):
        """
        Initialize a health checker.
        
        Args:
            metric_store: MetricStore to use for health assessment
        """
        self._metric_store = metric_store
        self._health_checks = {}  # component_name -> health check function
        self._health_status = {}  # component_name -> HealthStatus
        self._lock = threading.RLock()
        
        logger.debug("Initialized HealthChecker")
    
    def add_health_check(self, component: str, 
                       check_function: Callable[[MetricStore], HealthStatus]) -> None:
        """
        Add a health check function.
        
        Args:
            component: Name of the component to check
            check_function: Function that assesses component health
        """
        with self._lock:
            self._health_checks[component] = check_function
    
    def remove_health_check(self, component: str) -> bool:
        """
        Remove a health check function.
        
        Args:
            component: Name of the component to remove
            
        Returns:
            True if the check was removed, False if not found
        """
        with self._lock:
            if component in self._health_checks:
                del self._health_checks[component]
                return True
            return False
    
    def run_health_checks(self) -> Dict[str, HealthStatus]:
        """
        Run all health checks.
        
        Returns:
            Dictionary of component -> HealthStatus
        """
        with self._lock:
            for component, check_function in self._health_checks.items():
                try:
                    status = check_function(self._metric_store)
                    self._health_status[component] = status
                except Exception as e:
                    logger.error(f"Error in health check for {component}: {e}")
                    
                    # Create a failing status
                    self._health_status[component] = HealthStatus(
                        component=component,
                        status="failing",
                        details={"error": str(e)}
                    )
            
            return self._health_status.copy()
    
    def get_health_status(self, component: Optional[str] = None) -> Union[Dict[str, HealthStatus], Optional[HealthStatus]]:
        """
        Get health status.
        
        Args:
            component: Optional component name to get status for
            
        Returns:
            Health status for the component, or dictionary of all statuses
        """
        with self._lock:
            if component:
                return self._health_status.get(component)
            return self._health_status.copy()
    
    def clear_health_status(self) -> None:
        """Clear all health status records."""
        with self._lock:
            self._health_status.clear()


class MetricCollector:
    """
    Collects metrics from system components.
    
    The MetricCollector is responsible for gathering metrics from
    various sources, preprocessing them, and storing them for analysis.
    """
    
    def __init__(self, metric_store: MetricStore, alert_manager: AlertManager):
        """
        Initialize a metric collector.
        
        Args:
            metric_store: MetricStore to store collected metrics
            alert_manager: AlertManager to check metrics against rules
        """
        self._metric_store = metric_store
        self._alert_manager = alert_manager
        self._collection_tasks = {}  # task_name -> (interval, collector_function)
        self._stop_event = threading.Event()
        self._collection_threads = {}  # task_name -> thread
        
        logger.debug("Initialized MetricCollector")
    
    def add_collection_task(self, task_name: str, interval: float, 
                          collector: Callable[[], List[Metric]]) -> None:
        """
        Add a metric collection task.
        
        Args:
            task_name: Name of the collection task
            interval: Collection interval in seconds
            collector: Function that collects metrics
        """
        self._collection_tasks[task_name] = (interval, collector)
        logger.debug(f"Added collection task: {task_name} (interval: {interval}s)")
    
    def remove_collection_task(self, task_name: str) -> bool:
        """
        Remove a collection task.
        
        Args:
            task_name: Name of the task to remove
            
        Returns:
            True if the task was removed, False if not found
        """
        if task_name in self._collection_tasks:
            del self._collection_tasks[task_name]
            
            # Stop the collection thread if running
            if task_name in self._collection_threads:
                self._collection_threads[task_name].join(timeout=1.0)
                del self._collection_threads[task_name]
            
            logger.debug(f"Removed collection task: {task_name}")
            return True
        return False
    
    def start_collection(self) -> None:
        """
        Start metric collection.
        
        This starts the collection threads for all registered tasks.
        """
        self._stop_event.clear()
        
        # Start collection threads
        for task_name, (interval, collector) in self._collection_tasks.items():
            thread = threading.Thread(
                target=self._collection_loop,
                args=(task_name, interval, collector),
                name=f"MetricCollector-{task_name}",
                daemon=True
            )
            thread.start()
            self._collection_threads[task_name] = thread
        
        logger.info(f"Started metric collection for {len(self._collection_tasks)} tasks")
    
    def stop_collection(self) -> None:
        """
        Stop metric collection.
        
        This stops all collection threads.
        """
        self._stop_event.set()
        
        # Wait for threads to finish
        for task_name, thread in list(self._collection_threads.items()):
            thread.join(timeout=1.0)
            if thread.is_alive():
                logger.warning(f"Collection thread for {task_name} did not stop cleanly")
            del self._collection_threads[task_name]
        
        logger.info("Stopped metric collection")
    
    def collect_metric(self, metric: Metric) -> List[Alert]:
        """
        Collect and process a single metric.
        
        Args:
            metric: Metric to collect
            
        Returns:
            List of triggered alerts
        """
        # Store the metric
        self._metric_store.store_metric(metric)
        
        # Check for alerts
        alerts = self._alert_manager.check_metric(metric)
        
        return alerts
    
    def _collection_loop(self, task_name: str, interval: float, 
                       collector: Callable[[], List[Metric]]) -> None:
        """
        Collection loop for a task.
        
        This runs in a separate thread and periodically collects
        metrics using the provided collector function.
        
        Args:
            task_name: Name of the collection task
            interval: Collection interval in seconds
            collector: Function that collects metrics
        """
        logger.debug(f"Starting collection loop for {task_name}")
        
        while not self._stop_event.is_set():
            try:
                # Collect metrics
                metrics = collector()
                
                # Process each metric
                for metric in metrics:
                    self.collect_metric(metric)
                
                logger.debug(f"Collected {len(metrics)} metrics for {task_name}")
            except Exception as e:
                logger.error(f"Error collecting metrics for {task_name}: {e}")
            
            # Wait for next collection cycle
            if self._stop_event.wait(interval):
                break
        
        logger.debug(f"Stopped collection loop for {task_name}")


class NeuroMonitor:
    """
    Main monitoring system for the Neuron framework.
    
    The NeuroMonitor integrates the various monitoring components
    and provides a unified interface for monitoring and observability.
    """
    
    def __init__(self):
        """Initialize the monitoring system."""
        self._metric_store = None
        self._alert_manager = None
        self._health_checker = None
        self._metric_collector = None
        
        self._agent_manager = None
        self._synaptic_bus = None
        self._circuit_designer = None
        
        self._system_metrics_interval = 10.0
        self._health_check_interval = 60.0
        
        self._initialized = False
        self._running = False
        self._lock = threading.RLock()
        
        logger.info("Initialized NeuroMonitor")
    
    def initialize(self, agent_manager: Any, synaptic_bus: Any, 
                 circuit_designer: Any) -> None:
        """
        Initialize the monitoring system with dependencies.
        
        Args:
            agent_manager: AgentManager for monitoring agents
            synaptic_bus: SynapticBus for monitoring communication
            circuit_designer: CircuitDesigner for monitoring circuits
        """
        with self._lock:
            if self._initialized:
                logger.warning("NeuroMonitor is already initialized")
                return
            
            # Save dependencies
            self._agent_manager = agent_manager
            self._synaptic_bus = synaptic_bus
            self._circuit_designer = circuit_designer
            
            # Get configuration
            self._system_metrics_interval = config.get(
                "monitoring", "metrics_interval", 10.0
            )
            self._health_check_interval = config.get(
                "monitoring", "health_check_interval", 60.0
            )
            retention_period = config.get(
                "monitoring", "retention_period", 86400
            )
            
            # Create monitoring components
            self._metric_store = MetricStore(max_retention=retention_period)
            self._alert_manager = AlertManager()
            self._health_checker = HealthChecker(self._metric_store)
            self._metric_collector = MetricCollector(
                self._metric_store, self._alert_manager
            )
            
            # Set up collection tasks
            self._setup_collection_tasks()
            
            # Set up health checks
            self._setup_health_checks()
            
            # Set up alert rules
            self._setup_alert_rules()
            
            self._initialized = True
            logger.info("NeuroMonitor initialized with dependencies")
    
    def _setup_collection_tasks(self) -> None:
        """Set up metric collection tasks."""
        # System metrics collection
        self._metric_collector.add_collection_task(
            "system_metrics",
            self._system_metrics_interval,
            self._collect_system_metrics
        )
        
        # Agent metrics collection
        self._metric_collector.add_collection_task(
            "agent_metrics",
            self._system_metrics_interval,
            self._collect_agent_metrics
        )
        
        # Communication metrics collection
        self._metric_collector.add_collection_task(
            "communication_metrics",
            self._system_metrics_interval,
            self._collect_communication_metrics
        )
        
        # Circuit metrics collection
        self._metric_collector.add_collection_task(
            "circuit_metrics",
            self._system_metrics_interval,
            self._collect_circuit_metrics
        )
    
    def _setup_health_checks(self) -> None:
        """Set up health check functions."""
        # System health check
        self._health_checker.add_health_check(
            "system",
            self._check_system_health
        )
        
        # Agent health check
        self._health_checker.add_health_check(
            "agents",
            self._check_agent_health
        )
        
        # Communication health check
        self._health_checker.add_health_check(
            "communication",
            self._check_communication_health
        )
        
        # Circuit health check
        self._health_checker.add_health_check(
            "circuits",
            self._check_circuit_health
        )
    
    def _setup_alert_rules(self) -> None:
        """Set up alert rules."""
        # High memory usage alert
        self._alert_manager.add_rule(
            AlertRule(
                name="high_memory_usage",
                metric_pattern="system.memory.usage",
                condition=lambda x: x > 0.9,  # >90% memory usage
                alert_level=AlertLevel.WARNING,
                message_template="High memory usage: {value}%"
            )
        )
        
        # High CPU usage alert
        self._alert_manager.add_rule(
            AlertRule(
                name="high_cpu_usage",
                metric_pattern="system.cpu.usage",
                condition=lambda x: x > 0.9,  # >90% CPU usage
                alert_level=AlertLevel.WARNING,
                message_template="High CPU usage: {value}%"
            )
        )
        
        # High message queue alert
        self._alert_manager.add_rule(
            AlertRule(
                name="high_message_queue",
                metric_pattern="synaptic_bus.queue_size",
                condition=lambda x: x > 1000,  # >1000 messages in queue
                alert_level=AlertLevel.WARNING,
                message_template="High message queue size: {value}"
            )
        )
        
        # Agent error rate alert
        self._alert_manager.add_rule(
            AlertRule(
                name="high_agent_error_rate",
                metric_pattern="agent.*.error_count",
                condition=lambda x: x > 10,  # >10 errors
                alert_level=AlertLevel.ERROR,
                message_template="High error count for agent: {value} errors"
            )
        )
    
    def start(self) -> None:
        """
        Start the monitoring system.
        
        This begins collecting metrics and running health checks.
        """
        with self._lock:
            if not self._initialized:
                raise MonitoringError("NeuroMonitor is not initialized")
            
            if self._running:
                logger.warning("NeuroMonitor is already running")
                return
            
            # Start metric collection
            self._metric_collector.start_collection()
            
            # Run initial health checks
            self._health_checker.run_health_checks()
            
            # Start periodic health check task
            self._start_health_check_task()
            
            self._running = True
            logger.info("NeuroMonitor started")
    
    def stop(self) -> None:
        """
        Stop the monitoring system.
        
        This stops metric collection and health checks.
        """
        with self._lock:
            if not self._running:
                return
            
            # Stop metric collection
            self._metric_collector.stop_collection()
            
            # Stop health check task
            self._stop_health_check_task()
            
            self._running = False
            logger.info("NeuroMonitor stopped")
    
    def _start_health_check_task(self) -> None:
        """Start the periodic health check task."""
        # This is a simplified implementation
        # In a real system, this would use a proper scheduling mechanism
        
        self._health_check_stop_event = threading.Event()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            name="HealthCheckTask",
            daemon=True
        )
        self._health_check_thread.start()
    
    def _stop_health_check_task(self) -> None:
        """Stop the periodic health check task."""
        if hasattr(self, '_health_check_stop_event'):
            self._health_check_stop_event.set()
            
            if hasattr(self, '_health_check_thread') and self._health_check_thread.is_alive():
                self._health_check_thread.join(timeout=1.0)
    
    def _health_check_loop(self) -> None:
        """
        Health check loop.
        
        This runs in a separate thread and periodically runs health checks.
        """
        logger.debug("Starting health check loop")
        
        while not self._health_check_stop_event.is_set():
            try:
                # Run health checks
                self._health_checker.run_health_checks()
                logger.debug("Ran health checks")
            except Exception as e:
                logger.error(f"Error running health checks: {e}")
            
            # Wait for next check cycle
            if self._health_check_stop_event.wait(self._health_check_interval):
                break
        
        logger.debug("Stopped health check loop")
    
    def _collect_system_metrics(self) -> List[Metric]:
        """
        Collect system metrics.
        
        Returns:
            List of collected metrics
        """
        metrics = []
        
        try:
            # This is a simplified implementation
            # In a real system, this would use platform-specific APIs
            
            # Memory usage (simulated)
            import psutil
            memory = psutil.virtual_memory()
            metrics.append(Metric(
                name="system.memory.usage",
                metric_type=MetricType.GAUGE,
                value=memory.percent / 100.0,
                tags={"component": "system", "resource": "memory"}
            ))
            
            # CPU usage (simulated)
            cpu_percent = psutil.cpu_percent() / 100.0
            metrics.append(Metric(
                name="system.cpu.usage",
                metric_type=MetricType.GAUGE,
                value=cpu_percent,
                tags={"component": "system", "resource": "cpu"}
            ))
            
            # Thread count
            thread_count = threading.active_count()
            metrics.append(Metric(
                name="system.threads.count",
                metric_type=MetricType.GAUGE,
                value=thread_count,
                tags={"component": "system", "resource": "threads"}
            ))
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
        
        return metrics
    
    def _collect_agent_metrics(self) -> List[Metric]:
        """
        Collect agent metrics.
        
        Returns:
            List of collected metrics
        """
        metrics = []
        
        try:
            if not self._agent_manager:
                return metrics
            
            # Get all agent metrics
            agent_metrics = self._agent_manager.get_all_agent_metrics()
            
            for agent_id, agent_metrics_obj in agent_metrics.items():
                # Convert each metric to a Metric object
                agent_metrics_dict = agent_metrics_obj.to_dict()
                
                # Message count
                metrics.append(Metric(
                    name=f"agent.{agent_id}.message_count",
                    metric_type=MetricType.COUNTER,
                    value=agent_metrics_dict["message_count"],
                    tags={"component": "agent", "agent_id": agent_id}
                ))
                
                # Processing time
                metrics.append(Metric(
                    name=f"agent.{agent_id}.processing_time",
                    metric_type=MetricType.COUNTER,
                    value=agent_metrics_dict["processing_time"],
                    tags={"component": "agent", "agent_id": agent_id}
                ))
                
                # Error count
                metrics.append(Metric(
                    name=f"agent.{agent_id}.error_count",
                    metric_type=MetricType.COUNTER,
                    value=agent_metrics_dict["error_count"],
                    tags={"component": "agent", "agent_id": agent_id}
                ))
                
                # Memory usage
                metrics.append(Metric(
                    name=f"agent.{agent_id}.memory_usage",
                    metric_type=MetricType.GAUGE,
                    value=agent_metrics_dict["memory_usage"],
                    tags={"component": "agent", "agent_id": agent_id}
                ))
                
                # CPU usage
                metrics.append(Metric(
                    name=f"agent.{agent_id}.cpu_usage",
                    metric_type=MetricType.GAUGE,
                    value=agent_metrics_dict["cpu_usage"],
                    tags={"component": "agent", "agent_id": agent_id}
                ))
                
                # Last active
                if agent_metrics_dict["last_active"]:
                    metrics.append(Metric(
                        name=f"agent.{agent_id}.last_active",
                        metric_type=MetricType.GAUGE,
                        value=time.time() - agent_metrics_dict["last_active"],
                        tags={"component": "agent", "agent_id": agent_id}
                    ))
                
                # Custom metrics
                for key, value in agent_metrics_dict.get("custom_metrics", {}).items():
                    metrics.append(Metric(
                        name=f"agent.{agent_id}.{key}",
                        metric_type=MetricType.GAUGE,
                        value=value,
                        tags={"component": "agent", "agent_id": agent_id, "metric_type": "custom"}
                    ))
        except Exception as e:
            logger.error(f"Error collecting agent metrics: {e}")
        
        return metrics
    
    def _collect_communication_metrics(self) -> List[Metric]:
        """
        Collect communication metrics.
        
        Returns:
            List of collected metrics
        """
        metrics = []
        
        try:
            if not self._synaptic_bus:
                return metrics
            
            # Get bus statistics
            stats = asyncio.run(self._synaptic_bus.get_statistics())
            
            # Queue size
            metrics.append(Metric(
                name="synaptic_bus.queue_size",
                metric_type=MetricType.GAUGE,
                value=stats["queue_size"],
                tags={"component": "synaptic_bus"}
            ))
            
            # Registered agents
            metrics.append(Metric(
                name="synaptic_bus.registered_agents",
                metric_type=MetricType.GAUGE,
                value=stats["registered_agents"],
                tags={"component": "synaptic_bus"}
            ))
            
            # Channel metrics
            for channel_name, channel_stats in stats.get("channels", {}).items():
                # Subscribers
                metrics.append(Metric(
                    name=f"synaptic_bus.channel.{channel_name}.subscribers",
                    metric_type=MetricType.GAUGE,
                    value=channel_stats["subscribers"],
                    tags={"component": "synaptic_bus", "channel": channel_name}
                ))
                
                # Messages
                metrics.append(Metric(
                    name=f"synaptic_bus.channel.{channel_name}.messages",
                    metric_type=MetricType.GAUGE,
                    value=channel_stats["messages"],
                    tags={"component": "synaptic_bus", "channel": channel_name}
                ))
        except Exception as e:
            logger.error(f"Error collecting communication metrics: {e}")
        
        return metrics
    
    def _collect_circuit_metrics(self) -> List[Metric]:
        """
        Collect circuit metrics.
        
        Returns:
            List of collected metrics
        """
        metrics = []
        
        try:
            if not self._circuit_designer:
                return metrics
            
            # Get all circuits
            circuits = self._circuit_designer.get_all_circuits()
            
            # Circuit count
            metrics.append(Metric(
                name="circuits.count",
                metric_type=MetricType.GAUGE,
                value=len(circuits),
                tags={"component": "circuits"}
            ))
            
            # Metrics for each circuit
            for circuit_id, circuit in circuits.items():
                # Circuit status
                status = circuit.get_status()
                metrics.append(Metric(
                    name=f"circuit.{circuit_id}.status",
                    metric_type=MetricType.GAUGE,
                    value={"deployed": 1, "paused": 0.5, "terminated": 0}.get(status, 0),
                    tags={"component": "circuit", "circuit_id": circuit_id, "status": status}
                ))
                
                # Agent count
                agent_mapping = circuit.get_agent_mapping()
                metrics.append(Metric(
                    name=f"circuit.{circuit_id}.agent_count",
                    metric_type=MetricType.GAUGE,
                    value=len(agent_mapping),
                    tags={"component": "circuit", "circuit_id": circuit_id}
                ))
        except Exception as e:
            logger.error(f"Error collecting circuit metrics: {e}")
        
        return metrics
    
    def _check_system_health(self, metric_store: MetricStore) -> HealthStatus:
        """
        Check system health.
        
        Args:
            metric_store: MetricStore to use for health assessment
            
        Returns:
            Health status of the system
        """
        details = {}
        
        # Check memory usage
        memory_usage = metric_store.get_latest_value("system.memory.usage")
        if memory_usage is not None:
            details["memory_usage"] = memory_usage
        
        # Check CPU usage
        cpu_usage = metric_store.get_latest_value("system.cpu.usage")
        if cpu_usage is not None:
            details["cpu_usage"] = cpu_usage
        
        # Determine status
        if memory_usage is not None and memory_usage > 0.9:
            status = "degraded"
            details["reason"] = "High memory usage"
        elif cpu_usage is not None and cpu_usage > 0.9:
            status = "degraded"
            details["reason"] = "High CPU usage"
        else:
            status = "healthy"
        
        return HealthStatus(
            component="system",
            status=status,
            details=details
        )
    
    def _check_agent_health(self, metric_store: MetricStore) -> HealthStatus:
        """
        Check agent health.
        
        Args:
            metric_store: MetricStore to use for health assessment
            
        Returns:
            Health status of the agent system
        """
        details = {}
        
        # Get agent metrics
        agent_metrics = metric_store.get_metrics_by_pattern("agent.*")
        
        # Count agents by status
        active_agents = 0
        inactive_agents = 0
        error_agents = 0
        
        for name, value in agent_metrics.items():
            if "error_count" in name and value > 0:
                error_agents += 1
            elif "last_active" in name:
                if value < 60:  # active in the last minute
                    active_agents += 1
                else:
                    inactive_agents += 1
        
        details["active_agents"] = active_agents
        details["inactive_agents"] = inactive_agents
        details["error_agents"] = error_agents
        
        # Determine status
        if error_agents > 0:
            status = "degraded"
            details["reason"] = f"{error_agents} agents with errors"
        elif inactive_agents > active_agents:
            status = "warning"
            details["reason"] = f"{inactive_agents} inactive agents"
        else:
            status = "healthy"
        
        return HealthStatus(
            component="agents",
            status=status,
            details=details
        )
    
    def _check_communication_health(self, metric_store: MetricStore) -> HealthStatus:
        """
        Check communication health.
        
        Args:
            metric_store: MetricStore to use for health assessment
            
        Returns:
            Health status of the communication system
        """
        details = {}
        
        # Check message queue size
        queue_size = metric_store.get_latest_value("synaptic_bus.queue_size")
        if queue_size is not None:
            details["queue_size"] = queue_size
        
        # Check channel metrics
        channel_metrics = metric_store.get_metrics_by_pattern("synaptic_bus.channel.*")
        
        # Count channels with messages
        channels_with_messages = 0
        for name, value in channel_metrics.items():
            if "messages" in name and value > 0:
                channels_with_messages += 1
        
        details["channels_with_messages"] = channels_with_messages
        
        # Determine status
        if queue_size is not None and queue_size > 5000:
            status = "degraded"
            details["reason"] = "High message queue size"
        elif queue_size is not None and queue_size > 1000:
            status = "warning"
            details["reason"] = "Elevated message queue size"
        else:
            status = "healthy"
        
        return HealthStatus(
            component="communication",
            status=status,
            details=details
        )
    
    def _check_circuit_health(self, metric_store: MetricStore) -> HealthStatus:
        """
        Check circuit health.
        
        Args:
            metric_store: MetricStore to use for health assessment
            
        Returns:
            Health status of the circuit system
        """
        details = {}
        
        # Count circuits by status
        circuit_metrics = metric_store.get_metrics_by_pattern("circuit.*.status")
        
        deployed_circuits = 0
        paused_circuits = 0
        failing_circuits = 0
        
        for name, value in circuit_metrics.items():
            if value == 1:  # deployed
                deployed_circuits += 1
            elif value == 0.5:  # paused
                paused_circuits += 1
            else:  # other status, potentially failing
                failing_circuits += 1
        
        details["deployed_circuits"] = deployed_circuits
        details["paused_circuits"] = paused_circuits
        details["failing_circuits"] = failing_circuits
        
        # Determine status
        if failing_circuits > 0:
            status = "degraded"
            details["reason"] = f"{failing_circuits} failing circuits"
        elif paused_circuits > deployed_circuits:
            status = "warning"
            details["reason"] = f"{paused_circuits} paused circuits"
        else:
            status = "healthy"
        
        return HealthStatus(
            component="circuits",
            status=status,
            details=details
        )
    
    def get_metrics(self, pattern: Optional[str] = None,
                  time_range: Optional[Tuple[float, float]] = None,
                  aggregation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metrics.
        
        Args:
            pattern: Optional pattern to filter metrics by name
            time_range: Optional (start, end) time range
            aggregation: Optional aggregation function
            
        Returns:
            Dictionary of metric_name -> value(s)
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        if pattern:
            # Get metrics matching pattern
            return self._metric_store.get_metrics_by_pattern(pattern)
        else:
            # Get all metrics (latest values)
            return {
                name: self._metric_store.get_metric_value(name, time_range, aggregation or "latest")
                for name in self._metric_store._latest_values.keys()
            }
    
    def get_alerts(self, level: Optional[str] = None,
                 time_range: Optional[Tuple[float, float]] = None,
                 max_alerts: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get alerts.
        
        Args:
            level: Optional alert level to filter by
            time_range: Optional (start, end) time range
            max_alerts: Maximum number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        # Convert level string to enum
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel(level)
            except ValueError:
                raise ValueError(f"Invalid alert level: {level}")
        
        # Get alerts
        alerts = self._alert_manager.get_alerts(alert_level, time_range, max_alerts)
        
        # Convert to dictionaries
        return [alert.to_dict() for alert in alerts]
    
    def get_health_status(self, component: Optional[str] = None) -> Dict[str, Any]:
        """
        Get health status.
        
        Args:
            component: Optional component name to get status for
            
        Returns:
            Dictionary of component -> status
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        # Get health status
        status = self._health_checker.get_health_status(component)
        
        # Convert to dictionary
        if component:
            return status.to_dict() if status else {}
        else:
            return {comp: stat.to_dict() for comp, stat in status.items()}
    
    def add_alert_rule(self, name: str, metric_pattern: str,
                     condition_expression: str, level: str,
                     message_template: str) -> None:
        """
        Add an alert rule.
        
        Args:
            name: Name of the rule
            metric_pattern: Pattern for matching metric names
            condition_expression: Expression for the condition function
            level: Alert level (info, warning, error, critical)
            message_template: Template for alert messages
            
        Raises:
            ValueError: If the level is invalid
            MonitoringError: If the rule cannot be created
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        try:
            # Convert level string to enum
            alert_level = AlertLevel(level)
            
            # Create condition function
            condition = eval(f"lambda x: {condition_expression}")
            
            # Create rule
            rule = AlertRule(
                name=name,
                metric_pattern=metric_pattern,
                condition=condition,
                alert_level=alert_level,
                message_template=message_template
            )
            
            # Add rule
            self._alert_manager.add_rule(rule)
            
            logger.info(f"Added alert rule: {name}")
        except Exception as e:
            raise MonitoringError(f"Error adding alert rule: {e}") from e
    
    def run_health_checks(self) -> Dict[str, Any]:
        """
        Run health checks.
        
        Returns:
            Dictionary of component -> status
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        # Run health checks
        status = self._health_checker.run_health_checks()
        
        # Convert to dictionary
        return {comp: stat.to_dict() for comp, stat in status.items()}
    
    def create_metric(self, name: str, metric_type: str, value: Any,
                    tags: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Create and collect a custom metric.
        
        Args:
            name: Metric name
            metric_type: Type of metric (counter, gauge, histogram, timer, event)
            value: Metric value
            tags: Optional tags for the metric
            
        Returns:
            List of triggered alert dictionaries
            
        Raises:
            ValueError: If the metric type is invalid
            MonitoringError: If the metric cannot be created
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        try:
            # Convert type string to enum
            metric_type_enum = MetricType(metric_type)
            
            # Create metric
            metric = Metric(
                name=name,
                metric_type=metric_type_enum,
                value=value,
                tags=tags or {}
            )
            
            # Collect metric
            alerts = self._metric_collector.collect_metric(metric)
            
            # Convert alerts to dictionaries
            return [alert.to_dict() for alert in alerts]
        except Exception as e:
            raise MonitoringError(f"Error creating metric: {e}") from e
    
    def export_metrics(self, file_path: Union[str, Path],
                     start_time: Optional[float] = None,
                     end_time: Optional[float] = None,
                     pattern: Optional[str] = None) -> int:
        """
        Export metrics to a file.
        
        Args:
            file_path: Path to export metrics to
            start_time: Optional start time for export range
            end_time: Optional end time for export range
            pattern: Optional pattern to filter metrics by name
            
        Returns:
            Number of exported metrics
            
        Raises:
            MonitoringError: If export fails
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        try:
            # Get metrics
            time_range = None
            if start_time is not None and end_time is not None:
                time_range = (start_time, end_time)
            
            metrics_data = self.get_metrics(pattern, time_range)
            
            # Export to file
            with open(file_path, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            logger.info(f"Exported {len(metrics_data)} metrics to {file_path}")
            return len(metrics_data)
        except Exception as e:
            raise MonitoringError(f"Error exporting metrics: {e}") from e
    
    def visualize_metrics(self, metrics: List[str],
                        output_file: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Visualize metrics.
        
        Note: This is a simplified implementation that just returns data
        for visualization. In a real implementation, this would generate
        actual visualizations.
        
        Args:
            metrics: List of metric names to visualize
            output_file: Optional path to save visualization to
            
        Returns:
            Visualization data
            
        Raises:
            MonitoringError: If visualization fails
        """
        if not self._initialized:
            raise MonitoringError("NeuroMonitor is not initialized")
        
        try:
            # Collect data for visualization
            visualization_data = {}
            
            for metric_name in metrics:
                values = self._metric_store.get_metric_value(metric_name)
                if values:
                    visualization_data[metric_name] = values
            
            # If output file is specified, save data
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(visualization_data, f, indent=2)
                logger.info(f"Saved visualization data to {output_file}")
            
            return visualization_data
        except Exception as e:
            raise MonitoringError(f"Error visualizing metrics: {e}") from e
"""
