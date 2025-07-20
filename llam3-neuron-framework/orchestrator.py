#!/usr/bin/env python3
"""
Orchestration Engine for LLaMA3 Neuron Framework
Coordinates agent execution based on different patterns
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from collections import defaultdict

from config import (
    OrchestrationPattern,
    MessagePriority,
    AgentType,
    get_logger,
    FEATURES
)
from models import (
    Task,
    TaskStatus,
    Message,
    OrchestrationEvent,
    ProcessingRequest,
    ProcessingResponse,
    PatternMetrics
)
from agents import BaseAgent, AgentFactory
from message_bus import MessageBus
from task_queue import TaskQueue

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# ORCHESTRATION STRATEGIES
# ============================================================================

class OrchestrationStrategy:
    """
    Base class for orchestration strategies
    """
    
    def __init__(self, agents: Dict[str, BaseAgent], message_bus: MessageBus):
        """
        Initialize orchestration strategy
        
        Args:
            agents: Dictionary of available agents
            message_bus: Message bus for inter-agent communication
        """
        self.agents = agents
        self.message_bus = message_bus
        self.metrics = PatternMetrics(pattern=self.pattern)
    
    @property
    def pattern(self) -> OrchestrationPattern:
        """Get the orchestration pattern"""
        raise NotImplementedError
    
    async def execute(self, task: Task) -> ProcessingResponse:
        """
        Execute the orchestration strategy
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        raise NotImplementedError
    
    def _record_event(self, 
                     event_type: str,
                     source: str,
                     target: Optional[str] = None,
                     task_id: Optional[str] = None,
                     success: bool = True,
                     latency_ms: Optional[float] = None) -> OrchestrationEvent:
        """
        Record an orchestration event
        
        Args:
            event_type: Type of event
            source: Source agent/component
            target: Target agent/component
            task_id: Associated task ID
            success: Whether event was successful
            latency_ms: Event latency
            
        Returns:
            Orchestration event
        """
        event = OrchestrationEvent(
            event_type=event_type,
            source=source,
            target=target,
            pattern=self.pattern,
            task_id=task_id,
            success=success,
            latency_ms=latency_ms
        )
        
        # Could persist to database here
        logger.debug(f"Orchestration event: {event.event_type} from {source} to {target}")
        
        return event

# ============================================================================
# SEQUENTIAL STRATEGY
# ============================================================================

class SequentialStrategy(OrchestrationStrategy):
    """
    Sequential orchestration - agents process in order
    """
    
    @property
    def pattern(self) -> OrchestrationPattern:
        return OrchestrationPattern.SEQUENTIAL
    
    async def execute(self, task: Task) -> ProcessingResponse:
        """
        Execute sequential processing
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        self.metrics.total_executions += 1
        
        # Define processing pipeline
        pipeline = [
            ("intake_01", AgentType.INTAKE),
            ("analysis_01", AgentType.ANALYSIS),
            ("synthesis_01", AgentType.SYNTHESIS),
            ("output_01", AgentType.OUTPUT),
            ("qc_01", AgentType.QUALITY_CONTROL)
        ]
        
        current_task = task
        agents_involved = []
        total_tokens = 0
        
        try:
            # Process through pipeline
            for agent_id, agent_type in pipeline:
                if agent_id not in self.agents:
                    logger.warning(f"Agent {agent_id} not available, skipping")
                    continue
                
                agent = self.agents[agent_id]
                agents_involved.append(agent_id)
                
                # Record handoff event
                if agents_involved:
                    self._record_event(
                        "sequential_handoff",
                        agents_involved[-2] if len(agents_involved) > 1 else "orchestrator",
                        agent_id,
                        task.id
                    )
                
                # Process with agent
                agent_start = time.time()
                response = await agent.process_task(current_task)
                agent_latency = (time.time() - agent_start) * 1000
                
                # Record processing event
                self._record_event(
                    "agent_processing",
                    agent_id,
                    task_id=task.id,
                    success=response.status == TaskStatus.COMPLETED,
                    latency_ms=agent_latency
                )
                
                # Check for failures
                if response.status != TaskStatus.COMPLETED:
                    raise Exception(f"Agent {agent_id} failed: {response.error}")
                
                # Update task with results for next agent
                current_task = Task(
                    task_type=task.task_type,
                    payload={**task.payload, **response.result},
                    priority=task.priority,
                    pattern=task.pattern,
                    parent_task_id=task.id
                )
                
                total_tokens += response.total_tokens
            
            # Success
            self.metrics.successful_executions += 1
            total_time = (time.time() - start_time) * 1000
            self.metrics.total_latency_ms += total_time
            
            return ProcessingResponse(
                request_id=task.id,
                status=TaskStatus.COMPLETED,
                result=current_task.payload,
                pattern_used=self.pattern,
                agents_involved=agents_involved,
                total_tokens=total_tokens,
                processing_time_ms=total_time
            )
            
        except Exception as e:
            # Failure
            self.metrics.failed_executions += 1
            total_time = (time.time() - start_time) * 1000
            
            return ProcessingResponse(
                request_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                pattern_used=self.pattern,
                agents_involved=agents_involved,
                total_tokens=total_tokens,
                processing_time_ms=total_time
            )

# ============================================================================
# PARALLEL STRATEGY
# ============================================================================

class ParallelStrategy(OrchestrationStrategy):
    """
    Parallel orchestration - multiple agents process simultaneously
    """
    
    @property
    def pattern(self) -> OrchestrationPattern:
        return OrchestrationPattern.PARALLEL
    
    async def execute(self, task: Task) -> ProcessingResponse:
        """
        Execute parallel processing
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        self.metrics.total_executions += 1
        
        agents_involved = []
        total_tokens = 0
        
        try:
            # Phase 1: Intake
            intake_agent = self.agents.get("intake_01")
            if not intake_agent:
                raise Exception("Intake agent not available")
            
            intake_response = await intake_agent.process_task(task)
            if intake_response.status != TaskStatus.COMPLETED:
                raise Exception(f"Intake failed: {intake_response.error}")
            
            agents_involved.append("intake_01")
            total_tokens += intake_response.total_tokens
            
            # Phase 2: Parallel Analysis
            analysis_tasks = []
            analysis_agents = ["analysis_01", "analysis_02", "analysis_03"]
            
            for agent_id in analysis_agents:
                if agent_id in self.agents:
                    agent = self.agents[agent_id]
                    analysis_task = Task(
                        task_type="analysis",
                        payload={**task.payload, **intake_response.result},
                        priority=task.priority,
                        parent_task_id=task.id
                    )
                    analysis_tasks.append((agent_id, agent.process_task(analysis_task)))
            
            # Wait for all analyses to complete
            analysis_results = await asyncio.gather(
                *[task for _, task in analysis_tasks],
                return_exceptions=True
            )
            
            # Collect successful analyses
            successful_analyses = []
            for (agent_id, _), result in zip(analysis_tasks, analysis_results):
                if isinstance(result, Exception):
                    logger.warning(f"Analysis agent {agent_id} failed: {result}")
                elif result.status == TaskStatus.COMPLETED:
                    successful_analyses.append(result.result)
                    agents_involved.append(agent_id)
                    total_tokens += result.total_tokens
            
            if not successful_analyses:
                raise Exception("All analysis agents failed")
            
            # Phase 3: Synthesis
            synthesis_agent = self.agents.get("synthesis_01")
            if not synthesis_agent:
                raise Exception("Synthesis agent not available")
            
            synthesis_task = Task(
                task_type="synthesis",
                payload={
                    "analyses": successful_analyses,
                    **task.payload
                },
                priority=task.priority,
                parent_task_id=task.id
            )
            
            synthesis_response = await synthesis_agent.process_task(synthesis_task)
            if synthesis_response.status != TaskStatus.COMPLETED:
                raise Exception(f"Synthesis failed: {synthesis_response.error}")
            
            agents_involved.append("synthesis_01")
            total_tokens += synthesis_response.total_tokens
            
            # Phase 4: Output formatting
            output_agent = self.agents.get("output_01")
            if not output_agent:
                raise Exception("Output agent not available")
            
            output_task = Task(
                task_type="output",
                payload={**synthesis_response.result, **task.payload},
                priority=task.priority,
                parent_task_id=task.id
            )
            
            output_response = await output_agent.process_task(output_task)
            if output_response.status != TaskStatus.COMPLETED:
                raise Exception(f"Output formatting failed: {output_response.error}")
            
            agents_involved.append("output_01")
            total_tokens += output_response.total_tokens
            
            # Success
            self.metrics.successful_executions += 1
            total_time = (time.time() - start_time) * 1000
            self.metrics.total_latency_ms += total_time
            
            return ProcessingResponse(
                request_id=task.id,
                status=TaskStatus.COMPLETED,
                result=output_response.result,
                pattern_used=self.pattern,
                agents_involved=agents_involved,
                total_tokens=total_tokens,
                processing_time_ms=total_time
            )
            
        except Exception as e:
            # Failure
            self.metrics.failed_executions += 1
            total_time = (time.time() - start_time) * 1000
            
            return ProcessingResponse(
                request_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                pattern_used=self.pattern,
                agents_involved=agents_involved,
                total_tokens=total_tokens,
                processing_time_ms=total_time
            )

# ============================================================================
# ADAPTIVE STRATEGY
# ============================================================================

class AdaptiveStrategy(OrchestrationStrategy):
    """
    Adaptive orchestration - dynamically selects processing path
    """
    
    @property
    def pattern(self) -> OrchestrationPattern:
        return OrchestrationPattern.ADAPTIVE
    
    async def execute(self, task: Task) -> ProcessingResponse:
        """
        Execute adaptive processing
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        self.metrics.total_executions += 1
        
        # Analyze task to determine best strategy
        strategy = await self._select_strategy(task)
        
        # Execute selected strategy
        if strategy == OrchestrationPattern.SEQUENTIAL:
            delegate = SequentialStrategy(self.agents, self.message_bus)
        elif strategy == OrchestrationPattern.PARALLEL:
            delegate = ParallelStrategy(self.agents, self.message_bus)
        else:
            # Default to sequential
            delegate = SequentialStrategy(self.agents, self.message_bus)
        
        # Execute and record metrics
        response = await delegate.execute(task)
        
        # Update our metrics
        if response.status == TaskStatus.COMPLETED:
            self.metrics.successful_executions += 1
        else:
            self.metrics.failed_executions += 1
        
        self.metrics.total_latency_ms += response.processing_time_ms
        self.metrics.total_tokens += response.total_tokens
        
        # Record adaptive decision
        self._record_event(
            "adaptive_decision",
            "orchestrator",
            target=strategy.value,
            task_id=task.id,
            success=response.status == TaskStatus.COMPLETED
        )
        
        return response
    
    async def _select_strategy(self, task: Task) -> OrchestrationPattern:
        """
        Select best strategy for task
        
        Args:
            task: Task to analyze
            
        Returns:
            Selected orchestration pattern
        """
        # Simple heuristics for strategy selection
        
        # Check task complexity
        content = task.payload.get("content", "")
        token_estimate = len(content) // 4  # Rough estimate
        
        # Check available agents
        available_agents = len([a for a in self.agents.values() if a.state.is_available()])
        
        # Decision logic
        if token_estimate > 2000 and available_agents >= 3:
            # Large task with multiple agents available - use parallel
            return OrchestrationPattern.PARALLEL
        elif task.priority == MessagePriority.CRITICAL:
            # Critical tasks - use sequential for reliability
            return OrchestrationPattern.SEQUENTIAL
        elif available_agents < 2:
            # Few agents available - use sequential
            return OrchestrationPattern.SEQUENTIAL
        else:
            # Default to parallel for better performance
            return OrchestrationPattern.PARALLEL

# ============================================================================
# ORCHESTRATION ENGINE
# ============================================================================

class OrchestrationEngine:
    """
    Main orchestration engine that manages all strategies
    """
    
    def __init__(self, 
                 agents: Dict[str, BaseAgent],
                 message_bus: MessageBus,
                 task_queue: TaskQueue):
        """
        Initialize orchestration engine
        
        Args:
            agents: Dictionary of available agents
            message_bus: Message bus for communication
            task_queue: Task queue for processing
        """
        self.agents = agents
        self.message_bus = message_bus
        self.task_queue = task_queue
        
        # Initialize strategies
        self.strategies = {
            OrchestrationPattern.SEQUENTIAL: SequentialStrategy(agents, message_bus),
            OrchestrationPattern.PARALLEL: ParallelStrategy(agents, message_bus),
            OrchestrationPattern.ADAPTIVE: AdaptiveStrategy(agents, message_bus)
        }
        
        # Metrics
        self._pattern_usage = defaultdict(int)
        self._pattern_success = defaultdict(int)
        self._pattern_latency = defaultdict(list)
        
        logger.info("Orchestration engine initialized")
    
    async def process_request(self, request: ProcessingRequest) -> ProcessingResponse:
        """
        Process a request using appropriate orchestration
        
        Args:
            request: Processing request
            
        Returns:
            Processing response
        """
        # Create task from request
        task = Task(
            task_type="process",
            payload={
                "content": request.get_content_as_text(),
                "content_type": request.content_type,
                "processing_options": request.processing_options
            },
            priority=request.priority,
            pattern=request.pattern or OrchestrationPattern.ADAPTIVE,
            metadata=request.metadata
        )
        
        # Submit to queue
        task_id = await self.task_queue.submit_task(task)
        
        # Get strategy
        pattern = task.pattern
        if pattern not in self.strategies:
            pattern = OrchestrationPattern.SEQUENTIAL
        
        strategy = self.strategies[pattern]
        
        # Execute strategy
        response = await strategy.execute(task)
        
        # Update metrics
        self._pattern_usage[pattern] += 1
        if response.status == TaskStatus.COMPLETED:
            self._pattern_success[pattern] += 1
        self._pattern_latency[pattern].append(response.processing_time_ms)
        
        # Complete task in queue
        await self.task_queue.complete_task(task_id, response)
        
        return response
    
    async def get_pattern_metrics(self) -> Dict[OrchestrationPattern, PatternMetrics]:
        """
        Get metrics for all patterns
        
        Returns:
            Dictionary of pattern metrics
        """
        metrics = {}
        
        for pattern, strategy in self.strategies.items():
            metrics[pattern] = strategy.metrics
        
        return metrics
    
    async def get_engine_stats(self) -> Dict[str, Any]:
        """
        Get engine statistics
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            "pattern_usage": dict(self._pattern_usage),
            "pattern_success_rate": {
                pattern: (self._pattern_success[pattern] / usage if usage > 0 else 0)
                for pattern, usage in self._pattern_usage.items()
            },
            "pattern_avg_latency": {
                pattern.value: (sum(latencies) / len(latencies) if latencies else 0)
                for pattern, latencies in self._pattern_latency.items()
            },
            "available_agents": len([a for a in self.agents.values() if a.state.is_available()]),
            "total_agents": len(self.agents)
        }
        
        return stats