"""
metrics.py - Metrics Collection and Reporting

Comprehensive metrics collection, analysis, and reporting for chaos tests.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import statistics
from pathlib import Path

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


@dataclass
class TestResult:
    """Overall test result"""
    test_id: str
    scenario: str
    start_time: datetime
    end_time: datetime
    success: bool
    
    # Key metrics
    failure_detection_time: float
    recovery_time: float
    data_integrity: float
    
    # Thresholds
    detection_threshold: float
    recovery_threshold: float
    integrity_threshold: float
    
    # Detailed metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time
    
    @property
    def detection_passed(self) -> bool:
        return self.failure_detection_time <= self.detection_threshold
    
    @property
    def recovery_passed(self) -> bool:
        return self.recovery_time <= self.recovery_threshold
    
    @property
    def integrity_passed(self) -> bool:
        return self.data_integrity >= self.integrity_threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "test_id": self.test_id,
            "scenario": self.scenario,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration.total_seconds(),
            "success": self.success,
            "failure_detection_time": self.failure_detection_time,
            "recovery_time": self.recovery_time,
            "data_integrity": self.data_integrity,
            "thresholds": {
                "detection": self.detection_threshold,
                "recovery": self.recovery_threshold,
                "integrity": self.integrity_threshold
            },
            "passed": {
                "detection": self.detection_passed,
                "recovery": self.recovery_passed,
                "integrity": self.integrity_passed
            },
            "metrics": self.metrics,
            "events": self.events
        }


class MetricsCollector:
    """
    Collects and aggregates metrics during chaos tests.
    """
    
    def __init__(self, export_interval: float = 5.0):
        self.export_interval = export_interval
        self._metrics: List[Metric] = []
        self._lock = asyncio.Lock()
        self._export_task: Optional[asyncio.Task] = None
        self._start_time = time.time()
        
        # Metric aggregations
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        
        logger.info("MetricsCollector initialized")
    
    async def start(self):
        """Start metrics collection"""
        self._export_task = asyncio.create_task(self._export_loop())
        logger.info("MetricsCollector started")
    
    async def stop(self):
        """Stop metrics collection"""
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass
        logger.info("MetricsCollector stopped")
    
    async def record_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Record a counter metric (always increasing)"""
        async with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self._counters[key] = self._counters.get(key, 0) + value
            
            metric = Metric(
                name=name,
                type=MetricType.COUNTER,
                value=self._counters[key],
                timestamp=datetime.utcnow(),
                labels=labels or {}
            )
            self._metrics.append(metric)
    
    async def record_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a gauge metric (can go up or down)"""
        async with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self._gauges[key] = value
            
            metric = Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {}
            )
            self._metrics.append(metric)
    
    async def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric (for distributions)"""
        async with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            
            metric = Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {}
            )
            self._metrics.append(metric)
    
    async def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        async with self._lock:
            summary = {
                "collection_duration": time.time() - self._start_time,
                "total_metrics": len(self._metrics),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {}
            }
            
            # Calculate histogram statistics
            for key, values in self._histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "min": min(values),
                        "max": max(values),
                        "p95": self._percentile(values, 0.95),
                        "p99": self._percentile(values, 0.99)
                    }
            
            return summary
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    async def _export_loop(self):
        """Periodically export metrics"""
        while True:
            try:
                await asyncio.sleep(self.export_interval)
                await self._export_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics export error: {e}")
    
    async def _export_metrics(self):
        """Export metrics (override for custom exporters)"""
        summary = await self.get_summary()
        logger.debug(f"Metrics summary: {summary}")


class TestReporter:
    """
    Generates comprehensive test reports.
    """
    
    def __init__(self, output_dir: str = "chaos_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"TestReporter initialized, output: {self.output_dir}")
    
    def generate_report(self, result: TestResult) -> Path:
        """Generate a comprehensive test report"""
        # Create report filename
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"chaos_report_{result.scenario}_{timestamp}.json"
        report_path = self.output_dir / filename
        
        # Generate report content
        report = {
            "summary": {
                "test_id": result.test_id,
                "scenario": result.scenario,
                "duration": str(result.duration),
                "success": result.success,
                "timestamp": result.start_time.isoformat()
            },
            "results": {
                "failure_detection": {
                    "value": result.failure_detection_time,
                    "threshold": result.detection_threshold,
                    "passed": result.detection_passed,
                    "unit": "seconds"
                },
                "recovery_time": {
                    "value": result.recovery_time,
                    "threshold": result.recovery_threshold,
                    "passed": result.recovery_passed,
                    "unit": "seconds"
                },
                "data_integrity": {
                    "value": result.data_integrity,
                    "threshold": result.integrity_threshold,
                    "passed": result.integrity_passed,
                    "unit": "percentage"
                }
            },
            "detailed_metrics": result.metrics,
            "events": result.events
        }
        
        # Write report
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Report generated: {report_path}")
        
        # Also generate human-readable summary
        self._print_summary(result)
        
        return report_path
    
    def _print_summary(self, result: TestResult):
        """Print human-readable summary to console"""
        print("\n" + "="*50)
        print("         CHAOS TEST RESILIENCE REPORT")
        print("="*50)
        print(f"\nScenario: {result.scenario}")
        print(f"Duration: {result.duration}")
        print(f"Overall: {'PASSED' if result.success else 'FAILED'}")
        
        print("\n┌───────────────────────────────────┐")
        print("│         RESILIENCE REPORT         │")
        print("└───────────────────────────────────┘")
        
        # Failure Detection
        detection_status = "[PASSED]" if result.detection_passed else "[FAILED]"
        print(f" • Failure Detection: {result.failure_detection_time:.4f}s "
              f"(Threshold: < {result.detection_threshold}s) {detection_status}")
        
        # Recovery Time
        recovery_status = "[PASSED]" if result.recovery_passed else "[FAILED]"
        print(f" • Recovery Time:     {result.recovery_time:.4f}s "
              f"(Threshold: < {result.recovery_threshold}s) {recovery_status}")
        
        # Data Integrity
        integrity_status = "[PASSED]" if result.integrity_passed else "[FAILED]"
        print(f" • Data Integrity:   {result.data_integrity:.2%} preserved "
              f"(Threshold: {result.integrity_threshold:.0%}) {integrity_status}")
        
        # Additional metrics
        if "total_processed" in result.metrics:
            print(f" • Total Processed:   {result.metrics['total_processed']} tasks")
        if "total_lost" in result.metrics:
            print(f" • Total Lost:        {result.metrics['total_lost']} tasks")
        
        print("\n" + "="*50 + "\n")