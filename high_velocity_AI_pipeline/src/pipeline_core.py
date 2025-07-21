#!/usr/bin/env python3
"""
High-Velocity AI Pipeline - Core Implementation
Production-grade neural coordination system with adaptive hot-swapping

This module implements the core pipeline logic including:
- Adaptive hot-swap controller for agent switching
- High-velocity message processing
- Performance-based agent selection
- Circuit breaker integration
- Comprehensive monitoring and observability
"""

import asyncio
import time
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path

from .agent_manager import AgentManager, AgentType, AgentResponse
from .synthetic_market_data import MarketDataGenerator, MarketMessage
from .performance_monitor import PerformanceMonitor, LatencyTracker
from .config_manager import PipelineConfig
from .circuit_breaker import SystemCircuitBreaker


class SwapTrigger(Enum):
    """Reasons for agent swapping"""
    LATENCY_THRESHOLD = "latency_threshold_exceeded"
    THROUGHPUT_DEGRADATION = "throughput_degradation"
    ERROR_RATE_HIGH = "error_rate_high"
    MANUAL_TRIGGER = "manual_trigger"
    RECOVERY_COMPLETE = "recovery_complete"
    CIRCUIT_BREAKER = "circuit_breaker_triggered"


@dataclass
class SwapEvent:
    """Agent swap event details"""
    timestamp: datetime
    from_agent: AgentType
    to_agent: AgentType
    trigger: SwapTrigger
    metrics_snapshot: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


@dataclass
class ProcessingResult:
    """Result of message processing"""
    success: bool
    response_data: Optional[Dict[str, Any]]
    processing_time_ms: float
    agent_used: AgentType
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class AdaptiveHotSwapController:
    """
    Intelligent agent hot-swap controller
    
    Monitors performance metrics and adaptively switches between agents
    based on latency, throughput, and error rate thresholds.
    """
    
    def __init__(self, config: PipelineConfig, performance_monitor: PerformanceMonitor):
        self.config = config
        self.performance_monitor = performance_monitor
        self.logger = logging.getLogger(__name__)
        
        # Current state
        self.current_agent = AgentType(config.default_agent)
        self.swap_count = 0
        self.last_swap_time = datetime.now()
        self.swap_history: List[SwapEvent] = []
        
        # Swap control
        self.swap_lock = threading.Lock()
        self.cooldown_active = False
        self.max_swaps = config.max_agent_swaps
        
        # Performance tracking for swap decisions
        self.decision_window_size = 10  # Last N measurements
        self.consecutive_violations = 0
        self.recovery_confirmation_count = 0
        
        # Callbacks for swap events
        self.swap_callbacks: List[Callable[[SwapEvent], None]] = []
        
        self.logger.info(f"Initialized AdaptiveHotSwapController with {self.current_agent.value} agent")
    
    def register_swap_callback(self, callback: Callable[[SwapEvent], None]):
        """Register callback for swap events"""
        self.swap_callbacks.append(callback)
    
    def should_swap_to_ultra_fast(self) -> Tuple[bool, SwapTrigger]:
        """Check if should swap to ultra-fast agent"""
        if self.current_agent == AgentType.ULTRA_FAST:
            return False, None
        
        if self.cooldown_active:
            return False, None
        
        if self.swap_count >= self.max_swaps:
            self.logger.warning(f"Max swaps ({self.max_swaps}) reached")
            return False, None
        
        # Check latency threshold
        recent_latency = self.performance_monitor.get_recent_p99_latency()
        if recent_latency > self.config.latency_threshold_ms:
            self.consecutive_violations += 1
            if self.consecutive_violations >= 3:  # Require 3 consecutive violations
                return True, SwapTrigger.LATENCY_THRESHOLD
        else:
            self.consecutive_violations = 0
        
        # Check error rate
        error_rate = self.performance_monitor.get_recent_error_rate()
        if error_rate > 0.1:  # 10% error rate
            return True, SwapTrigger.ERROR_RATE_HIGH
        
        # Check throughput degradation
        current_throughput = self.performance_monitor.get_current_throughput()
        if current_throughput < self.config.safe_throughput_threshold * 0.5:  # 50% of safe threshold
            return True, SwapTrigger.THROUGHPUT_DEGRADATION
        
        return False, None
    
    def should_swap_to_standard(self) -> Tuple[bool, SwapTrigger]:
        """Check if should swap back to standard agent"""
        if self.current_agent == AgentType.STANDARD:
            return False, None
        
        if self.cooldown_active:
            return False, None
        
        # Check if conditions are favorable for standard agent
        recent_latency = self.performance_monitor.get_recent_p99_latency()
        current_throughput = self.performance_monitor.get_current_throughput()
        error_rate = self.performance_monitor.get_recent_error_rate()
        
        conditions_met = (
            recent_latency < self.config.safe_latency_threshold_ms and
            current_throughput > self.config.safe_throughput_threshold and
            error_rate < 0.05  # 5% error rate
        )
        
        if conditions_met:
            self.recovery_confirmation_count += 1
            if self.recovery_confirmation_count >= 5:  # Require 5 consecutive confirmations
                return True, SwapTrigger.RECOVERY_COMPLETE
        else:
            self.recovery_confirmation_count = 0
        
        return False, None
    
    async def execute_swap(self, to_agent: AgentType, trigger: SwapTrigger) -> SwapEvent:
        """Execute agent swap with proper coordination"""
        with self.swap_lock:
            if self.cooldown_active:
                raise RuntimeError("Swap attempted during cooldown period")
            
            from_agent = self.current_agent
            metrics_snapshot = self.performance_monitor.get_current_metrics()
            
            # Create swap event
            swap_event = SwapEvent(
                timestamp=datetime.now(),
                from_agent=from_agent,
                to_agent=to_agent,
                trigger=trigger,
                metrics_snapshot=metrics_snapshot
            )
            
            # Perform the swap
            self.current_agent = to_agent
            self.swap_count += 1
            self.last_swap_time = datetime.now()
            self.swap_history.append(swap_event)
            
            # Reset counters
            self.consecutive_violations = 0
            self.recovery_confirmation_count = 0
            
            # Activate cooldown
            await self._activate_cooldown()
            
            # Log swap
            self.logger.info(
                f"Agent swap #{self.swap_count}: {from_agent.value} → {to_agent.value} "
                f"(trigger: {trigger.value})"
            )
            
            # Notify callbacks
            for callback in self.swap_callbacks:
                try:
                    callback(swap_event)
                except Exception as e:
                    self.logger.error(f"Swap callback failed: {e}")
            
            return swap_event
    
    async def _activate_cooldown(self):
        """Activate cooldown period to prevent rapid swapping"""
        self.cooldown_active = True
        
        async def cooldown_task():
            await asyncio.sleep(self.config.cooldown_period_seconds)
            self.cooldown_active = False
            self.logger.debug("Cooldown period ended")
        
        asyncio.create_task(cooldown_task())
    
    async def evaluate_and_swap(self) -> Optional[SwapEvent]:
        """Evaluate current conditions and swap if necessary"""
        try:
            # Check for swap to ultra-fast
            should_swap, trigger = self.should_swap_to_ultra_fast()
            if should_swap:
                return await self.execute_swap(AgentType.ULTRA_FAST, trigger)
            
            # Check for swap back to standard
            should_swap, trigger = self.should_swap_to_standard()
            if should_swap:
                return await self.execute_swap(AgentType.STANDARD, trigger)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in swap evaluation: {e}")
            return None
    
    def get_current_agent(self) -> AgentType:
        """Get currently active agent type"""
        return self.current_agent
    
    def get_swap_statistics(self) -> Dict[str, Any]:
        """Get swap statistics"""
        return {
            "total_swaps": self.swap_count,
            "current_agent": self.current_agent.value,
            "max_swaps": self.max_swaps,
            "swaps_remaining": self.max_swaps - self.swap_count,
            "cooldown_active": self.cooldown_active,
            "last_swap_time": self.last_swap_time.isoformat() if self.swap_history else None,
            "swap_history": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "from_agent": event.from_agent.value,
                    "to_agent": event.to_agent.value,
                    "trigger": event.trigger.value,
                    "event_id": event.event_id
                }
                for event in self.swap_history[-10:]  # Last 10 swaps
            ]
        }


class HighVelocityPipeline:
    """
    High-Velocity AI Pipeline for Financial Trading
    
    Production-grade pipeline with:
    - Adaptive agent hot-swapping
    - High-throughput message processing
    - Comprehensive monitoring
    - Circuit breaker protection
    - Export capabilities
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.agent_manager = AgentManager(config)
        self.market_data_generator = MarketDataGenerator(config)
        self.performance_monitor = PerformanceMonitor(config)
        self.circuit_breaker = SystemCircuitBreaker(config)
        
        # Hot-swap controller
        self.swap_controller = AdaptiveHotSwapController(config, self.performance_monitor)
        
        # Pipeline state
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.total_messages_processed = 0
        self.processing_queue: asyncio.Queue = None
        
        # Message batching
        self.message_batch: List[MarketMessage] = []
        self.batch_lock = threading.Lock()
        
        # Statistics
        self.processing_results: List[ProcessingResult] = []
        self.error_count = 0
        
        # Setup callbacks
        self.swap_controller.register_swap_callback(self._on_agent_swap)
        
        self.logger.info("HighVelocityPipeline initialized")
    
    def _on_agent_swap(self, swap_event: SwapEvent):
        """Handle agent swap events"""
        self.performance_monitor.record_agent_swap(swap_event)
        self.logger.info(f"Agent swap completed: {swap_event.event_id}")
    
    async def start(self):
        """Start the pipeline"""
        if self.is_running:
            raise RuntimeError("Pipeline is already running")
        
        self.logger.info("Starting High-Velocity Pipeline...")
        
        # Initialize components
        await self.agent_manager.initialize()
        await self.performance_monitor.start()
        
        # Create processing queue
        self.processing_queue = asyncio.Queue(maxsize=self.config.max_message_queue_size)
        
        # Reset state
        self.is_running = True
        self.start_time = datetime.now()
        self.total_messages_processed = 0
        self.processing_results.clear()
        self.error_count = 0
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._message_generation_loop()),
            asyncio.create_task(self._message_processing_loop()),
            asyncio.create_task(self._batch_processing_loop()),
            asyncio.create_task(self._monitoring_loop()),
            asyncio.create_task(self._swap_evaluation_loop())
        ]
        
        self.logger.info("Pipeline started successfully")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            self.logger.info("Pipeline tasks cancelled")
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
            raise
        finally:
            await self._cleanup()
    
    async def stop(self):
        """Stop the pipeline gracefully"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping pipeline...")
        self.is_running = False
        
        # Allow time for graceful shutdown
        await asyncio.sleep(1.0)
    
    async def _cleanup(self):
        """Cleanup pipeline resources"""
        self.is_running = False
        
        try:
            await self.performance_monitor.stop()
            await self.agent_manager.cleanup()
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    async def _message_generation_loop(self):
        """Generate market data messages"""
        self.logger.debug("Starting message generation loop")
        
        try:
            async for message in self.market_data_generator.generate_realtime_stream():
                if not self.is_running:
                    break
                
                try:
                    await self.processing_queue.put(message)
                except asyncio.QueueFull:
                    self.logger.warning("Processing queue full, dropping message")
                    
        except Exception as e:
            self.logger.error(f"Message generation error: {e}")
    
    async def _message_processing_loop(self):
        """Process messages from the queue"""
        self.logger.debug("Starting message processing loop")
        
        while self.is_running:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=1.0
                )
                
                # Add to batch
                with self.batch_lock:
                    self.message_batch.append(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")
    
    async def _batch_processing_loop(self):
        """Process message batches"""
        self.logger.debug("Starting batch processing loop")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.config.batch_interval_seconds)
                
                # Get current batch
                with self.batch_lock:
                    if not self.message_batch:
                        continue
                    
                    current_batch = self.message_batch[:self.config.message_batch_size]
                    self.message_batch = self.message_batch[self.config.message_batch_size:]
                
                # Process batch
                if current_batch:
                    await self._process_message_batch(current_batch)
                
            except Exception as e:
                self.logger.error(f"Batch processing error: {e}")
    
    async def _process_message_batch(self, messages: List[MarketMessage]):
        """Process a batch of messages"""
        current_agent = self.swap_controller.get_current_agent()
        
        # Check circuit breaker
        if not self.circuit_breaker.can_proceed():
            self.logger.warning("Circuit breaker open, skipping batch")
            return
        
        batch_start_time = time.time()
        batch_results = []
        
        try:
            # Process messages in parallel (limited concurrency)
            semaphore = asyncio.Semaphore(10)  # Max 10 concurrent
            
            async def process_single_message(message: MarketMessage) -> ProcessingResult:
                async with semaphore:
                    return await self._process_single_message(message, current_agent)
            
            # Create tasks for all messages
            tasks = [process_single_message(msg) for msg in messages]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Record batch metrics
            successful_results = [r for r in batch_results if isinstance(r, ProcessingResult) and r.success]
            failed_results = [r for r in batch_results if isinstance(r, ProcessingResult) and not r.success]
            exceptions = [r for r in batch_results if isinstance(r, Exception)]
            
            batch_duration = (time.time() - batch_start_time) * 1000  # ms
            
            # Update performance monitor
            self.performance_monitor.record_batch_completion(
                batch_size=len(messages),
                successful_count=len(successful_results),
                failed_count=len(failed_results) + len(exceptions),
                batch_duration_ms=batch_duration,
                agent_type=current_agent
            )
            
            # Update circuit breaker
            success_rate = len(successful_results) / len(messages)
            if success_rate < 0.5:  # Less than 50% success
                self.circuit_breaker.record_failure()
            else:
                self.circuit_breaker.record_success()
            
            # Store results
            self.processing_results.extend([r for r in batch_results if isinstance(r, ProcessingResult)])
            self.total_messages_processed += len(messages)
            self.error_count += len(failed_results) + len(exceptions)
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            self.circuit_breaker.record_failure()
    
    async def _process_single_message(self, message: MarketMessage, agent_type: AgentType) -> ProcessingResult:
        """Process a single message"""
        start_time = time.time()
        
        try:
            # Get agent response
            agent_response = await self.agent_manager.process_message(message, agent_type)
            
            processing_time = (time.time() - start_time) * 1000  # ms
            
            # Record latency
            self.performance_monitor.record_latency(processing_time)
            
            return ProcessingResult(
                success=agent_response.success,
                response_data=agent_response.data,
                processing_time_ms=processing_time,
                agent_used=agent_type,
                error_message=agent_response.error_message
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(f"Message processing failed: {e}")
            
            return ProcessingResult(
                success=False,
                response_data=None,
                processing_time_ms=processing_time,
                agent_used=agent_type,
                error_message=str(e)
            )
    
    async def _monitoring_loop(self):
        """Monitoring and metrics collection loop"""
        self.logger.debug("Starting monitoring loop")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.config.metrics_update_interval_seconds)
                
                # Update performance metrics
                await self.performance_monitor.update_metrics(
                    total_messages=self.total_messages_processed,
                    error_count=self.error_count,
                    agent_swaps=self.swap_controller.swap_count,
                    circuit_breaker_trips=self.circuit_breaker.trip_count
                )
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
    
    async def _swap_evaluation_loop(self):
        """Agent swap evaluation loop"""
        self.logger.debug("Starting swap evaluation loop")
        
        while self.is_running:
            try:
                await asyncio.sleep(1.0)  # Check every second
                
                # Evaluate swap conditions
                swap_event = await self.swap_controller.evaluate_and_swap()
                
                if swap_event:
                    self.logger.info(f"Agent swap executed: {swap_event.event_id}")
                
            except Exception as e:
                self.logger.error(f"Swap evaluation error: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.start_time:
            return {"status": "not_started"}
        
        duration = datetime.now() - self.start_time
        
        # Calculate rates
        duration_seconds = duration.total_seconds()
        messages_per_second = self.total_messages_processed / duration_seconds if duration_seconds > 0 else 0
        error_rate = (self.error_count / self.total_messages_processed) if self.total_messages_processed > 0 else 0
        
        # Get performance metrics
        performance_metrics = self.performance_monitor.get_current_metrics()
        
        # Get swap statistics
        swap_stats = self.swap_controller.get_swap_statistics()
        
        return {
            "pipeline_summary": {
                "status": "running" if self.is_running else "stopped",
                "duration_seconds": duration_seconds,
                "total_messages_processed": self.total_messages_processed,
                "messages_per_second": messages_per_second,
                "error_count": self.error_count,
                "error_rate_percent": error_rate * 100,
                "success_rate_percent": (1 - error_rate) * 100
            },
            "performance_metrics": performance_metrics,
            "agent_swap_stats": swap_stats,
            "circuit_breaker_status": {
                "state": self.circuit_breaker.state.value,
                "trip_count": self.circuit_breaker.trip_count,
                "can_proceed": self.circuit_breaker.can_proceed()
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def export_results(self) -> Dict[str, str]:
        """Export pipeline results"""
        try:
            # Generate performance summary
            summary = self.get_performance_summary()
            
            # Export CSV data
            csv_file = None
            if self.config.enable_csv_export:
                csv_file = await self.performance_monitor.export_csv()
            
            # Export JSON report
            json_file = None
            if self.config.export_json_reports:
                json_file = await self._export_json_report(summary)
            
            return {
                "csv_file": csv_file,
                "json_file": json_file,
                "summary": summary
            }
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            raise
    
    async def _export_json_report(self, summary: Dict[str, Any]) -> str:
        """Export comprehensive JSON report"""
        export_dir = Path(self.config.export_directory)
        export_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pipeline_report_{timestamp}.json"
        filepath = export_dir / filename
        
        # Enhanced report data
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "pipeline_version": "1.0.0",
                "config_summary": {
                    "latency_threshold_ms": self.config.latency_threshold_ms,
                    "target_throughput": self.config.target_throughput,
                    "default_agent": self.config.default_agent,
                    "max_agent_swaps": self.config.max_agent_swaps
                }
            },
            **summary
        }
        
        # Write report
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        self.logger.info(f"JSON report exported: {filepath}")
        return str(filepath)