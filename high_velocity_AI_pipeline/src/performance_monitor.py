#!/usr/bin/env python3
"""
Performance Monitor - Comprehensive Pipeline Performance Tracking
Advanced monitoring system for high-velocity pipeline performance

This module provides:
- Real-time latency tracking with percentile calculations
- Throughput monitoring and trend analysis
- Agent performance comparison
- CSV export for analysis
- Weave tracing integration
- Health metrics and alerting
"""

import asyncio
import time
import statistics
import logging
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import threading
from pathlib import Path
import sys

from .config_manager import PipelineConfig
from .agent_manager import AgentType

# Optional Weave integration
try:
    import weave
    WEAVE_AVAILABLE = True
except ImportError:
    WEAVE_AVAILABLE = False


@dataclass
class LatencyMeasurement:
    """Individual latency measurement"""
    timestamp: datetime
    latency_ms: float
    agent_type: AgentType
    success: bool
    message_id: Optional[str] = None


@dataclass
class ThroughputMeasurement:
    """Throughput measurement over time window"""
    timestamp: datetime
    messages_per_second: float
    window_size_seconds: float
    total_messages: int


@dataclass
class PerformanceSnapshot:
    """Point-in-time performance snapshot"""
    timestamp: datetime
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    current_throughput: float
    average_throughput: float
    success_rate: float
    active_agent: AgentType
    agent_swaps: int


class LatencyTracker:
    """Advanced latency tracking with percentile calculations"""
    
    def __init__(self, max_measurements: int = 10000):
        self.max_measurements = max_measurements
        self.measurements: deque = deque(maxlen=max_measurements)
        self.lock = threading.Lock()
        
        # Pre-calculate percentiles for efficiency
        self._cached_percentiles: Optional[Dict[str, float]] = None
        self._cache_timestamp = 0
        self._cache_duration = 1.0  # Cache for 1 second
    
    def record_latency(self, latency_ms: float, agent_type: AgentType, 
                      success: bool = True, message_id: Optional[str] = None):
        """Record a latency measurement"""
        with self.lock:
            measurement = LatencyMeasurement(
                timestamp=datetime.now(),
                latency_ms=latency_ms,
                agent_type=agent_type,
                success=success,
                message_id=message_id
            )
            self.measurements.append(measurement)
            
            # Invalidate cache
            self._cached_percentiles = None
    
    def get_percentiles(self, time_window_minutes: Optional[float] = None) -> Dict[str, float]:
        """Get latency percentiles with optional time window"""
        
        # Check cache first
        current_time = time.time()
        if (self._cached_percentiles and 
            current_time - self._cache_timestamp < self._cache_duration and
            time_window_minutes is None):
            return self._cached_percentiles
        
        with self.lock:
            measurements = list(self.measurements)
        
        if not measurements:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}
        
        # Filter by time window if specified
        if time_window_minutes:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            measurements = [m for m in measurements if m.timestamp >= cutoff_time]
        
        if not measurements:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}
        
        # Extract latencies (only successful requests for accurate percentiles)
        successful_latencies = [m.latency_ms for m in measurements if m.success]
        all_latencies = [m.latency_ms for m in measurements]
        
        if not successful_latencies:
            successful_latencies = all_latencies
        
        if not successful_latencies:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}
        
        # Calculate percentiles
        sorted_latencies = sorted(successful_latencies)
        n = len(sorted_latencies)
        
        percentiles = {
            "p50": sorted_latencies[int(0.50 * n)] if n > 0 else 0.0,
            "p95": sorted_latencies[int(0.95 * n)] if n > 0 else 0.0,
            "p99": sorted_latencies[int(0.99 * n)] if n > 0 else 0.0,
            "mean": statistics.mean(successful_latencies)
        }
        
        # Cache result if no time window specified
        if time_window_minutes is None:
            self._cached_percentiles = percentiles
            self._cache_timestamp = current_time
        
        return percentiles
    
    def get_agent_performance_comparison(self) -> Dict[AgentType, Dict[str, float]]:
        """Compare performance across different agents"""
        with self.lock:
            measurements = list(self.measurements)
        
        agent_performance = {}
        
        for agent_type in AgentType:
            agent_measurements = [m for m in measurements if m.agent_type == agent_type and m.success]
            
            if agent_measurements:
                latencies = [m.latency_ms for m in agent_measurements]
                agent_performance[agent_type] = {
                    "count": len(agent_measurements),
                    "mean_latency": statistics.mean(latencies),
                    "p95_latency": sorted(latencies)[int(0.95 * len(latencies))] if latencies else 0.0,
                    "p99_latency": sorted(latencies)[int(0.99 * len(latencies))] if latencies else 0.0,
                    "success_rate": len([m for m in measurements if m.agent_type == agent_type and m.success]) / 
                                   max(len([m for m in measurements if m.agent_type == agent_type]), 1)
                }
            else:
                agent_performance[agent_type] = {
                    "count": 0,
                    "mean_latency": 0.0,
                    "p95_latency": 0.0,
                    "p99_latency": 0.0,
                    "success_rate": 0.0
                }
        
        return agent_performance
    
    def get_recent_measurements(self, count: int = 100) -> List[LatencyMeasurement]:
        """Get most recent measurements"""
        with self.lock:
            return list(self.measurements)[-count:]
    
    def clear_measurements(self):
        """Clear all measurements"""
        with self.lock:
            self.measurements.clear()
            self._cached_percentiles = None


class ThroughputTracker:
    """Real-time throughput tracking"""
    
    def __init__(self, window_size_seconds: float = 60.0):
        self.window_size_seconds = window_size_seconds
        self.message_timestamps: deque = deque()
        self.throughput_history: deque = deque(maxlen=1000)  # Keep 1000 measurements
        self.lock = threading.Lock()
        
        # Running statistics
        self.total_messages = 0
        self.start_time = datetime.now()
    
    def record_message(self, count: int = 1):
        """Record processed message(s)"""
        current_time = time.time()
        
        with self.lock:
            # Add timestamps for each message
            for _ in range(count):
                self.message_timestamps.append(current_time)
                self.total_messages += 1
            
            # Remove old timestamps outside window
            cutoff_time = current_time - self.window_size_seconds
            while self.message_timestamps and self.message_timestamps[0] < cutoff_time:
                self.message_timestamps.popleft()
    
    def get_current_throughput(self) -> float:
        """Get current throughput (messages per second)"""
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - self.window_size_seconds
            
            # Remove old timestamps
            while self.message_timestamps and self.message_timestamps[0] < cutoff_time:
                self.message_timestamps.popleft()
            
            # Calculate throughput
            messages_in_window = len(self.message_timestamps)
            actual_window = min(self.window_size_seconds, 
                              current_time - (self.message_timestamps[0] if self.message_timestamps else current_time))
            
            if actual_window > 0:
                throughput = messages_in_window / actual_window
            else:
                throughput = 0.0
            
            # Store in history
            measurement = ThroughputMeasurement(
                timestamp=datetime.now(),
                messages_per_second=throughput,
                window_size_seconds=actual_window,
                total_messages=self.total_messages
            )
            self.throughput_history.append(measurement)
            
            return throughput
    
    def get_average_throughput(self) -> float:
        """Get average throughput since start"""
        with self.lock:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 0:
                return self.total_messages / elapsed
            return 0.0
    
    def get_throughput_trend(self, minutes: int = 5) -> List[ThroughputMeasurement]:
        """Get throughput trend over specified minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            return [m for m in self.throughput_history if m.timestamp >= cutoff_time]


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system
    
    Tracks latency, throughput, agent performance, and system health
    with export capabilities and optional Weave tracing.
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Core trackers
        self.latency_tracker = LatencyTracker()
        self.throughput_tracker = ThroughputTracker()
        
        # Performance snapshots for trend analysis
        self.performance_snapshots: deque = deque(maxlen=1000)
        
        # Agent swap tracking
        self.agent_swaps = 0
        self.swap_history: List[Dict[str, Any]] = []
        
        # System health metrics
        self.circuit_breaker_trips = 0
        self.error_count = 0
        self.last_error_time: Optional[datetime] = None
        
        # Weave integration
        self.weave_enabled = config.enable_weave_tracing and WEAVE_AVAILABLE
        if self.weave_enabled:
            try:
                # Initialize Weave if API key is available
                if hasattr(config, 'wandb_api_key') and config.wandb_api_key:
                    weave.init('high-velocity-pipeline')
                    self.logger.info("Weave tracing initialized")
                else:
                    self.weave_enabled = False
                    self.logger.warning("Weave tracing disabled - no API key")
            except Exception as e:
                self.weave_enabled = False
                self.logger.warning(f"Weave initialization failed: {e}")
        
        # Monitoring task
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        self.logger.info("PerformanceMonitor initialized")
    
    async def start(self):
        """Start performance monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Performance monitoring started")
    
    async def stop(self):
        """Stop performance monitoring"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        try:
            while self.is_monitoring:
                await asyncio.sleep(self.config.metrics_update_interval_seconds)
                
                # Take performance snapshot
                snapshot = self._create_performance_snapshot()
                self.performance_snapshots.append(snapshot)
                
                # Log performance periodically
                if len(self.performance_snapshots) % 10 == 0:  # Every 10 snapshots
                    self._log_performance_summary(snapshot)
                
        except asyncio.CancelledError:
            self.logger.debug("Monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Monitoring loop error: {e}")
    
    def _create_performance_snapshot(self) -> PerformanceSnapshot:
        """Create current performance snapshot"""
        percentiles = self.latency_tracker.get_percentiles()
        current_throughput = self.throughput_tracker.get_current_throughput()
        average_throughput = self.throughput_tracker.get_average_throughput()
        
        # Calculate success rate
        recent_measurements = self.latency_tracker.get_recent_measurements(100)
        if recent_measurements:
            success_rate = len([m for m in recent_measurements if m.success]) / len(recent_measurements)
        else:
            success_rate = 1.0
        
        # Determine active agent (most recent)
        active_agent = AgentType.STANDARD  # Default
        if recent_measurements:
            active_agent = recent_measurements[-1].agent_type
        
        return PerformanceSnapshot(
            timestamp=datetime.now(),
            latency_p50_ms=percentiles["p50"],
            latency_p95_ms=percentiles["p95"],
            latency_p99_ms=percentiles["p99"],
            current_throughput=current_throughput,
            average_throughput=average_throughput,
            success_rate=success_rate,
            active_agent=active_agent,
            agent_swaps=self.agent_swaps
        )
    
    def _log_performance_summary(self, snapshot: PerformanceSnapshot):
        """Log performance summary"""
        self.logger.info(
            f"Performance: P99={snapshot.latency_p99_ms:.1f}ms, "
            f"Throughput={snapshot.current_throughput:.1f}msg/s, "
            f"Success={snapshot.success_rate:.1%}, "
            f"Agent={snapshot.active_agent.value}, "
            f"Swaps={snapshot.agent_swaps}"
        )
    
    def record_latency(self, latency_ms: float, agent_type: AgentType = AgentType.STANDARD, 
                      success: bool = True, message_id: Optional[str] = None):
        """Record latency measurement"""
        self.latency_tracker.record_latency(latency_ms, agent_type, success, message_id)
        
        # Weave tracing
        if self.weave_enabled and WEAVE_AVAILABLE:
            try:
                weave.track("latency", {
                    "latency_ms": latency_ms,
                    "agent_type": agent_type.value,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.debug(f"Weave tracking failed: {e}")
    
    def record_batch_completion(self, batch_size: int, successful_count: int, 
                               failed_count: int, batch_duration_ms: float, 
                               agent_type: AgentType):
        """Record batch processing completion"""
        
        # Record throughput
        self.throughput_tracker.record_message(batch_size)
        
        # Record errors
        self.error_count += failed_count
        if failed_count > 0:
            self.last_error_time = datetime.now()
        
        # Average latency per message in batch
        if batch_size > 0:
            avg_latency_per_message = batch_duration_ms / batch_size
            
            # Record latency for successful messages
            for _ in range(successful_count):
                self.record_latency(avg_latency_per_message, agent_type, True)
            
            # Record latency for failed messages
            for _ in range(failed_count):
                self.record_latency(avg_latency_per_message, agent_type, False)
        
        # Weave tracing for batch
        if self.weave_enabled and WEAVE_AVAILABLE:
            try:
                weave.track("batch_completion", {
                    "batch_size": batch_size,
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "batch_duration_ms": batch_duration_ms,
                    "agent_type": agent_type.value,
                    "success_rate": successful_count / batch_size if batch_size > 0 else 0,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.logger.debug(f"Weave batch tracking failed: {e}")
    
    def record_agent_swap(self, swap_event: Any):
        """Record agent swap event"""
        self.agent_swaps += 1
        
        swap_record = {
            "swap_number": self.agent_swaps,
            "timestamp": swap_event.timestamp.isoformat(),
            "from_agent": swap_event.from_agent.value,
            "to_agent": swap_event.to_agent.value,
            "trigger": swap_event.trigger.value,
            "event_id": swap_event.event_id
        }
        
        self.swap_history.append(swap_record)
        
        # Keep limited history
        if len(self.swap_history) > 100:
            self.swap_history = self.swap_history[-50:]
        
        # Weave tracing
        if self.weave_enabled and WEAVE_AVAILABLE:
            try:
                weave.track("agent_swap", swap_record)
            except Exception as e:
                self.logger.debug(f"Weave swap tracking failed: {e}")
        
        self.logger.info(f"Agent swap recorded: {swap_record}")
    
    async def update_metrics(self, total_messages: int, error_count: int, 
                           agent_swaps: int, circuit_breaker_trips: int):
        """Update overall system metrics"""
        self.error_count = error_count
        self.agent_swaps = agent_swaps
        self.circuit_breaker_trips = circuit_breaker_trips
        
        # Update throughput tracker's total
        self.throughput_tracker.total_messages = total_messages
    
    def get_recent_p99_latency(self, minutes: float = 2.0) -> float:
        """Get recent P99 latency for swap decisions"""
        percentiles = self.latency_tracker.get_percentiles(minutes)
        return percentiles["p99"]
    
    def get_recent_error_rate(self, minutes: float = 5.0) -> float:
        """Get recent error rate"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_measurements = [
            m for m in self.latency_tracker.get_recent_measurements(1000)
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_measurements:
            return 0.0
        
        failed_count = len([m for m in recent_measurements if not m.success])
        return failed_count / len(recent_measurements)
    
    def get_current_throughput(self) -> float:
        """Get current throughput"""
        return self.throughput_tracker.get_current_throughput()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get comprehensive current metrics"""
        percentiles = self.latency_tracker.get_percentiles()
        agent_performance = self.latency_tracker.get_agent_performance_comparison()
        
        # Convert agent performance for JSON serialization
        agent_perf_serializable = {
            agent.value: stats for agent, stats in agent_performance.items()
        }
        
        return {
            "latency": {
                "p50_ms": percentiles["p50"],
                "p95_ms": percentiles["p95"], 
                "p99_ms": percentiles["p99"],
                "mean_ms": percentiles["mean"]
            },
            "throughput": {
                "current_msg_per_sec": self.throughput_tracker.get_current_throughput(),
                "average_msg_per_sec": self.throughput_tracker.get_average_throughput(),
                "total_messages": self.throughput_tracker.total_messages
            },
            "health": {
                "success_rate_percent": (1 - self.get_recent_error_rate()) * 100,
                "error_count": self.error_count,
                "agent_swaps": self.agent_swaps,
                "circuit_breaker_trips": self.circuit_breaker_trips,
                "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None
            },
            "agent_performance": agent_perf_serializable,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_performance_trends(self, minutes: int = 30) -> Dict[str, Any]:
        """Get performance trends over time"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        # Filter snapshots
        recent_snapshots = [
            s for s in self.performance_snapshots 
            if s.timestamp >= cutoff_time
        ]
        
        if not recent_snapshots:
            return {"error": "No data available for specified time range"}
        
        # Calculate trends
        latency_trend = [s.latency_p99_ms for s in recent_snapshots]
        throughput_trend = [s.current_throughput for s in recent_snapshots]
        success_rate_trend = [s.success_rate for s in recent_snapshots]
        
        return {
            "time_range_minutes": minutes,
            "snapshots_count": len(recent_snapshots),
            "latency_trend": {
                "values": latency_trend,
                "min": min(latency_trend),
                "max": max(latency_trend),
                "avg": statistics.mean(latency_trend),
                "trend_direction": "increasing" if latency_trend[-1] > latency_trend[0] else "decreasing"
            },
            "throughput_trend": {
                "values": throughput_trend,
                "min": min(throughput_trend),
                "max": max(throughput_trend),
                "avg": statistics.mean(throughput_trend),
                "trend_direction": "increasing" if throughput_trend[-1] > throughput_trend[0] else "decreasing"
            },
            "success_rate_trend": {
                "values": success_rate_trend,
                "min": min(success_rate_trend),
                "max": max(success_rate_trend),
                "avg": statistics.mean(success_rate_trend)
            },
            "agent_swaps_in_period": len([s for s in recent_snapshots if s.agent_swaps > recent_snapshots[0].agent_swaps])
        }
    
    async def export_csv(self) -> Optional[str]:
        """Export performance data to CSV"""
        if not self.config.enable_csv_export:
            return None
        
        try:
            # Create export directory
            export_dir = Path(self.config.export_directory)
            export_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self.config.export_csv_filename:
                filename = self.config.export_csv_filename
            else:
                filename = f"pipeline_performance_{timestamp}.csv"
            
            filepath = export_dir / filename
            
            # Collect data for export
            measurements = self.latency_tracker.get_recent_measurements(10000)  # Last 10k measurements
            throughput_history = list(self.throughput_tracker.throughput_history)
            
            # Write CSV
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers
                writer.writerow([
                    'timestamp', 'measurement_type', 'value', 'unit', 
                    'agent_type', 'success', 'message_id'
                ])
                
                # Write latency measurements
                for measurement in measurements:
                    writer.writerow([
                        measurement.timestamp.isoformat(),
                        'latency',
                        measurement.latency_ms,
                        'ms',
                        measurement.agent_type.value,
                        measurement.success,
                        measurement.message_id or ''
                    ])
                
                # Write throughput measurements
                for measurement in throughput_history:
                    writer.writerow([
                        measurement.timestamp.isoformat(),
                        'throughput',
                        measurement.messages_per_second,
                        'msg/sec',
                        '',
                        True,
                        ''
                    ])
                
                # Write performance snapshots
                for snapshot in self.performance_snapshots:
                    # P99 latency
                    writer.writerow([
                        snapshot.timestamp.isoformat(),
                        'p99_latency',
                        snapshot.latency_p99_ms,
                        'ms',
                        snapshot.active_agent.value,
                        True,
                        ''
                    ])
                    
                    # Current throughput
                    writer.writerow([
                        snapshot.timestamp.isoformat(),
                        'current_throughput',
                        snapshot.current_throughput,
                        'msg/sec',
                        snapshot.active_agent.value,
                        True,
                        ''
                    ])
                    
                    # Success rate
                    writer.writerow([
                        snapshot.timestamp.isoformat(),
                        'success_rate',
                        snapshot.success_rate * 100,
                        'percent',
                        snapshot.active_agent.value,
                        True,
                        ''
                    ])
            
            self.logger.info(f"Performance data exported to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"CSV export failed: {e}")
            return None
    
    def export_agent_comparison(self) -> Dict[str, Any]:
        """Export detailed agent performance comparison"""
        agent_performance = self.latency_tracker.get_agent_performance_comparison()
        
        comparison = {
            "export_timestamp": datetime.now().isoformat(),
            "comparison_summary": {},
            "detailed_metrics": {}
        }
        
        # Convert for JSON serialization and add analysis
        for agent_type, metrics in agent_performance.items():
            agent_name = agent_type.value
            comparison["detailed_metrics"][agent_name] = {
                **metrics,
                "efficiency_score": self._calculate_efficiency_score(metrics)
            }
        
        # Generate comparison summary
        if len(agent_performance) >= 2:
            agents = list(agent_performance.keys())
            agent1, agent2 = agents[0], agents[1]
            
            perf1 = agent_performance[agent1]
            perf2 = agent_performance[agent2]
            
            comparison["comparison_summary"] = {
                "faster_agent": agent1.value if perf1["mean_latency"] < perf2["mean_latency"] else agent2.value,
                "more_reliable_agent": agent1.value if perf1["success_rate"] > perf2["success_rate"] else agent2.value,
                "latency_difference_ms": abs(perf1["mean_latency"] - perf2["mean_latency"]),
                "success_rate_difference": abs(perf1["success_rate"] - perf2["success_rate"]) * 100
            }
        
        return comparison
    
    def _calculate_efficiency_score(self, metrics: Dict[str, float]) -> float:
        """Calculate overall efficiency score for an agent"""
        if metrics["count"] == 0:
            return 0.0
        
        # Weighted score: 40% latency, 60% success rate
        latency_score = max(0, 100 - metrics["mean_latency"] / 10)  # Lower latency = higher score
        success_score = metrics["success_rate"] * 100
        
        efficiency = (latency_score * 0.4) + (success_score * 0.6)
        return round(efficiency, 2)
    
    def reset_statistics(self):
        """Reset all performance statistics"""
        self.latency_tracker.clear_measurements()
        self.throughput_tracker = ThroughputTracker()
        self.performance_snapshots.clear()
        
        self.agent_swaps = 0
        self.swap_history.clear()
        self.circuit_breaker_trips = 0
        self.error_count = 0
        self.last_error_time = None
        
        self.logger.info("Performance statistics reset")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        recent_p99 = self.get_recent_p99_latency()
        current_throughput = self.get_current_throughput()
        error_rate = self.get_recent_error_rate()
        
        # Determine health status
        health_score = 100
        issues = []
        
        # Check latency
        if recent_p99 > self.config.latency_threshold_ms * 1.5:
            health_score -= 30
            issues.append(f"High P99 latency: {recent_p99:.1f}ms")
        elif recent_p99 > self.config.latency_threshold_ms:
            health_score -= 15
            issues.append(f"Elevated P99 latency: {recent_p99:.1f}ms")
        
        # Check throughput
        target_throughput = self.config.target_throughput
        if current_throughput < target_throughput * 0.5:
            health_score -= 25
            issues.append(f"Low throughput: {current_throughput:.1f}msg/s")
        elif current_throughput < target_throughput * 0.8:
            health_score -= 10
            issues.append(f"Reduced throughput: {current_throughput:.1f}msg/s")
        
        # Check error rate
        if error_rate > 0.1:  # 10%
            health_score -= 35
            issues.append(f"High error rate: {error_rate:.1%}")
        elif error_rate > 0.05:  # 5%
            health_score -= 15
            issues.append(f"Elevated error rate: {error_rate:.1%}")
        
        # Check circuit breaker
        if self.circuit_breaker_trips > 0:
            health_score -= 20
            issues.append(f"Circuit breaker trips: {self.circuit_breaker_trips}")
        
        # Determine status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "degraded"
        elif health_score >= 50:
            status = "unhealthy"
        else:
            status = "critical"
        
        return {
            "status": status,
            "health_score": max(0, health_score),
            "issues": issues,
            "metrics": {
                "p99_latency_ms": recent_p99,
                "current_throughput": current_throughput,
                "error_rate_percent": error_rate * 100,
                "circuit_breaker_trips": self.circuit_breaker_trips
            },
            "timestamp": datetime.now().isoformat()
        }