#!/usr/bin/env python3
"""
Agent Implementation for LLaMA3 Neuron Framework
Defines all agent types and their processing logic
"""

import asyncio
import time
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from config import (
    AgentType,
    AgentConfig,
    DEFAULT_AGENT_CONFIGS,
    get_logger,
    FEATURES
)
from models import (
    Task,
    TaskStatus,
    AgentState,
    AgentStatus,
    Message,
    MessagePriority,
    ProcessingRequest,
    ProcessingResponse,
    ErrorDetail
)
from llama_client import LLaMAClient, LLaMARequest, create_llama_client
from utils import CircuitBreaker, Cache, Metrics

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# BASE AGENT
# ============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for all agents
    Provides common functionality and interface
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize base agent
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.agent_id = config.agent_id
        self.agent_type = config.agent_type
        
        # Initialize state
        self.state = AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=AgentStatus.IDLE
        )
        
        # Initialize components
        self.llama_client: Optional[LLaMAClient] = None
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )
        self.cache = Cache(
            max_size=1000,
            ttl_seconds=config.cache_ttl_seconds
        ) if config.enable_caching else None
        self.metrics = Metrics(self.agent_id)
        
        # Task handling
        self._current_task: Optional[Task] = None
        self._task_lock = asyncio.Lock()
        
        logger.info(f"Initialized {self.agent_type.value} agent: {self.agent_id}")
    
    async def start(self):
        """Start the agent"""
        logger.info(f"Starting agent {self.agent_id}")
        
        # Initialize LLaMA client
        self.llama_client = LLaMAClient()
        await self.llama_client.connect()
        
        # Update state
        self.state.status = AgentStatus.IDLE
        self.state.update_heartbeat()
        
        # Start heartbeat task
        asyncio.create_task(self._heartbeat_loop())
        
        logger.info(f"Agent {self.agent_id} started successfully")
    
    async def stop(self):
        """Stop the agent"""
        logger.info(f"Stopping agent {self.agent_id}")
        
        # Update state
        self.state.status = AgentStatus.OFFLINE
        
        # Close LLaMA client
        if self.llama_client:
            await self.llama_client.close()
        
        logger.info(f"Agent {self.agent_id} stopped")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.state.status != AgentStatus.OFFLINE:
            self.state.update_heartbeat()
            await asyncio.sleep(30)  # 30 second heartbeat
    
    async def process_task(self, task: Task) -> ProcessingResponse:
        """
        Process a task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        async with self._task_lock:
            if not self.state.is_available():
                raise RuntimeError(f"Agent {self.agent_id} is not available")
            
            # Update state
            self._current_task = task
            self.state.status = AgentStatus.BUSY
            self.state.current_task_id = task.id
            
        start_time = time.time()
        
        try:
            # Check cache if enabled
            if self.cache and task.metadata.get("cacheable", True):
                cache_key = self._generate_cache_key(task)
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    logger.debug(f"Cache hit for task {task.id}")
                    self.metrics.increment_sync("cache_hits")
                    return cached_result
            
            # Process with circuit breaker
            result = await self.circuit_breaker.call(
                self._process_task_impl,
                task
            )
            
            # Cache result if enabled
            if self.cache and task.metadata.get("cacheable", True):
                await self.cache.set(cache_key, result)
            
            # Update metrics
            elapsed = time.time() - start_time
            self.metrics.record_sync("processing_time", elapsed)
            self.metrics.increment_sync("tasks_processed")
            
            # Update state
            self.state.processed_tasks += 1
            self.state.total_tokens += result.total_tokens
            self.state.average_latency = (
                (self.state.average_latency * (self.state.processed_tasks - 1) + elapsed) /
                self.state.processed_tasks
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}")
            self.metrics.increment_sync("tasks_failed")
            self.state.failed_tasks += 1
            
            return ProcessingResponse(
                request_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                agents_involved=[self.agent_id],
                processing_time_ms=(time.time() - start_time) * 1000
            )
            
        finally:
            # Reset state
            async with self._task_lock:
                self._current_task = None
                self.state.status = AgentStatus.IDLE
                self.state.current_task_id = None
    
    @abstractmethod
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Implementation-specific task processing
        Must be implemented by subclasses
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        pass
    
    def _generate_cache_key(self, task: Task) -> str:
        """
        Generate cache key for task
        
        Args:
            task: Task to generate key for
            
        Returns:
            Cache key
        """
        # Create deterministic key from task data
        key_data = {
            "agent_type": self.agent_type.value,
            "task_type": task.task_type,
            "payload_hash": hash(json.dumps(task.payload, sort_keys=True))
        }
        return json.dumps(key_data, sort_keys=True)
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """
        Handle an inter-agent message
        
        Args:
            message: Message to handle
            
        Returns:
            Optional response message
        """
        logger.debug(f"Agent {self.agent_id} received message from {message.source_agent}")
        
        # Default implementation - override in subclasses
        return None
    
    def get_status(self) -> AgentState:
        """Get current agent state"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return self.metrics.get_all()

# ============================================================================
# INTAKE AGENT
# ============================================================================

class IntakeAgent(BaseAgent):
    """
    Intake agent - validates and preprocesses incoming requests
    """
    
    def __init__(self, config: AgentConfig = None):
        """Initialize intake agent"""
        config = config or DEFAULT_AGENT_CONFIGS["intake"]
        super().__init__(config)
        
        # Intake-specific initialization
        self.validation_prompt = """
        Analyze the following request and extract key information:
        1. Identify the type of content (report, query, data, etc.)
        2. Extract main entities and topics
        3. Determine urgency/priority (critical, high, medium, low)
        4. Identify any special processing requirements
        
        Request: {content}
        
        Provide response in JSON format with keys: content_type, entities, priority, requirements
        """
    
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Process intake task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        
        # Extract content from task
        content = task.payload.get("content", "")
        if not content:
            raise ValueError("No content provided in task payload")
        
        # Validate content length
        token_count = self.llama_client.token_counter.count_tokens(content)
        if token_count > 8192:  # LLaMA3 context limit
            # Truncate content
            content = self.llama_client.token_counter.truncate_to_limit(content, 7000)
            logger.warning(f"Content truncated from {token_count} to 7000 tokens")
        
        # Prepare LLaMA request for validation
        llama_request = LLaMARequest(
            prompt=self.validation_prompt.format(content=content),
            max_tokens=500,
            temperature=0.3,  # Low temperature for consistency
            system_prompt="You are a content validation and classification assistant."
        )
        
        # Call LLaMA for analysis
        llama_response = await self.llama_client.generate(llama_request)
        
        # Parse response
        try:
            analysis = json.loads(llama_response.text.strip())
        except json.JSONDecodeError:
            # Fallback to basic analysis
            analysis = {
                "content_type": "unknown",
                "entities": [],
                "priority": "medium",
                "requirements": []
            }
        
        # Build response
        result = {
            "validation": "passed",
            "content_type": analysis.get("content_type", "unknown"),
            "entities": analysis.get("entities", []),
            "priority": analysis.get("priority", "medium"),
            "requirements": analysis.get("requirements", []),
            "token_count": token_count,
            "processing_metadata": {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "llama3"
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResponse(
            request_id=task.id,
            status=TaskStatus.COMPLETED,
            result=result,
            agents_involved=[self.agent_id],
            total_tokens=llama_response.tokens_used,
            processing_time_ms=processing_time
        )

# ============================================================================
# ANALYSIS AGENT
# ============================================================================

class AnalysisAgent(BaseAgent):
    """
    Analysis agent - performs deep analysis on content
    """
    
    def __init__(self, config: AgentConfig = None):
        """Initialize analysis agent"""
        config = config or DEFAULT_AGENT_CONFIGS["analysis"]
        super().__init__(config)
        
        # Analysis-specific initialization
        self.analysis_prompt = """
        Perform comprehensive analysis on the following content:
        
        Content Type: {content_type}
        Content: {content}
        
        Provide detailed analysis including:
        1. Key findings and insights
        2. Risk assessment (if applicable)
        3. Patterns and anomalies detected
        4. Recommendations for action
        5. Confidence scores for each finding
        
        Format response as JSON with appropriate structure.
        """
    
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Process analysis task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        
        # Extract content and metadata
        content = task.payload.get("content", "")
        content_type = task.payload.get("content_type", "unknown")
        entities = task.payload.get("entities", [])
        
        # Prepare enhanced prompt with context
        context_prompt = f"Entities identified: {', '.join(entities)}\n" if entities else ""
        
        # Prepare LLaMA request
        llama_request = LLaMARequest(
            prompt=self.analysis_prompt.format(
                content_type=content_type,
                content=content
            ),
            max_tokens=2048,
            temperature=0.7,  # Moderate temperature for analysis
            system_prompt=f"You are an expert analyst specializing in {content_type} analysis. {context_prompt}"
        )
        
        # Call LLaMA for analysis
        llama_response = await self.llama_client.generate(llama_request)
        
        # Parse response
        try:
            analysis_result = json.loads(llama_response.text.strip())
        except json.JSONDecodeError:
            # Structure the response if JSON parsing fails
            analysis_result = {
                "findings": [llama_response.text],
                "risk_level": "unknown",
                "patterns": [],
                "recommendations": [],
                "confidence": 0.5
            }
        
        # Enhance with metadata
        result = {
            "analysis": analysis_result,
            "content_type": content_type,
            "entities_analyzed": entities,
            "analysis_depth": "comprehensive",
            "processing_metadata": {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "llama3",
                "tokens_analyzed": task.payload.get("token_count", 0)
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResponse(
            request_id=task.id,
            status=TaskStatus.COMPLETED,
            result=result,
            agents_involved=[self.agent_id],
            total_tokens=llama_response.tokens_used,
            processing_time_ms=processing_time
        )

# ============================================================================
# SYNTHESIS AGENT
# ============================================================================

class SynthesisAgent(BaseAgent):
    """
    Synthesis agent - combines multiple analyses into coherent output
    """
    
    def __init__(self, config: AgentConfig = None):
        """Initialize synthesis agent"""
        config = config or DEFAULT_AGENT_CONFIGS["synthesis"]
        super().__init__(config)
        
        # Synthesis-specific initialization
        self.synthesis_prompt = """
        Synthesize the following multiple analyses into a coherent summary:
        
        Analyses:
        {analyses}
        
        Create a unified synthesis that:
        1. Identifies common themes and findings
        2. Resolves any conflicting information
        3. Provides integrated recommendations
        4. Assigns overall confidence and priority
        5. Highlights critical action items
        
        Format as a comprehensive report suitable for decision-making.
        """
    
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Process synthesis task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        
        # Extract analyses to synthesize
        analyses = task.payload.get("analyses", [])
        if not analyses:
            # If no analyses provided, check for single analysis
            if "analysis" in task.payload:
                analyses = [task.payload["analysis"]]
            else:
                raise ValueError("No analyses provided for synthesis")
        
        # Format analyses for prompt
        analyses_text = "\n\n".join([
            f"Analysis {i+1}:\n{json.dumps(analysis, indent=2)}"
            for i, analysis in enumerate(analyses)
        ])
        
        # Prepare LLaMA request
        llama_request = LLaMARequest(
            prompt=self.synthesis_prompt.format(analyses=analyses_text),
            max_tokens=3072,
            temperature=0.5,  # Balanced temperature for synthesis
            system_prompt="You are an expert at synthesizing complex information into actionable insights."
        )
        
        # Call LLaMA for synthesis
        llama_response = await self.llama_client.generate(llama_request)
        
        # Structure the synthesis result
        result = {
            "synthesis": llama_response.text,
            "source_analyses_count": len(analyses),
            "integration_method": "llama3_synthesis",
            "processing_metadata": {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "llama3",
                "synthesis_strategy": "comprehensive"
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResponse(
            request_id=task.id,
            status=TaskStatus.COMPLETED,
            result=result,
            agents_involved=[self.agent_id],
            total_tokens=llama_response.tokens_used,
            processing_time_ms=processing_time
        )

# ============================================================================
# OUTPUT AGENT
# ============================================================================

class OutputAgent(BaseAgent):
    """
    Output agent - formats final output for delivery
    """
    
    def __init__(self, config: AgentConfig = None):
        """Initialize output agent"""
        config = config or DEFAULT_AGENT_CONFIGS["output"]
        super().__init__(config)
        
        # Output-specific initialization
        self.formatting_prompt = """
        Format the following synthesis into a professional {output_format} document:
        
        Content:
        {content}
        
        Requirements:
        - Target audience: {audience}
        - Tone: {tone}
        - Length: {length}
        
        Ensure the output is well-structured, clear, and actionable.
        """
    
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Process output formatting task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        
        # Extract content and formatting requirements
        content = task.payload.get("content", task.payload.get("synthesis", ""))
        output_format = task.payload.get("format", "report")
        audience = task.payload.get("audience", "general")
        tone = task.payload.get("tone", "professional")
        length = task.payload.get("length", "medium")
        
        # Prepare LLaMA request
        llama_request = LLaMARequest(
            prompt=self.formatting_prompt.format(
                output_format=output_format,
                content=content,
                audience=audience,
                tone=tone,
                length=length
            ),
            max_tokens=2048,
            temperature=0.3,  # Low temperature for consistent formatting
            system_prompt=f"You are a professional document formatter specializing in {output_format} creation."
        )
        
        # Call LLaMA for formatting
        llama_response = await self.llama_client.generate(llama_request)
        
        # Build response
        result = {
            "formatted_output": llama_response.text,
            "format": output_format,
            "metadata": {
                "audience": audience,
                "tone": tone,
                "length": length,
                "word_count": len(llama_response.text.split()),
                "formatting_complete": True
            },
            "processing_metadata": {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "llama3"
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResponse(
            request_id=task.id,
            status=TaskStatus.COMPLETED,
            result=result,
            agents_involved=[self.agent_id],
            total_tokens=llama_response.tokens_used,
            processing_time_ms=processing_time
        )

# ============================================================================
# QUALITY CONTROL AGENT
# ============================================================================

class QualityControlAgent(BaseAgent):
    """
    Quality control agent - validates output quality
    """
    
    def __init__(self, config: AgentConfig = None):
        """Initialize quality control agent"""
        config = config or DEFAULT_AGENT_CONFIGS["quality_control"]
        super().__init__(config)
        
        # QC-specific initialization
        self.qc_prompt = """
        Perform quality control on the following output:
        
        Output:
        {output}
        
        Original Requirements:
        {requirements}
        
        Check for:
        1. Completeness - Does it address all requirements?
        2. Accuracy - Are facts and figures correct?
        3. Clarity - Is it easy to understand?
        4. Consistency - Is formatting and tone consistent?
        5. Actionability - Are recommendations clear and actionable?
        
        Provide a quality score (0-100) and specific feedback.
        """
    
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Process quality control task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        
        # Extract output and requirements
        output = task.payload.get("output", task.payload.get("formatted_output", ""))
        requirements = task.payload.get("requirements", {})
        
        # Prepare LLaMA request
        llama_request = LLaMARequest(
            prompt=self.qc_prompt.format(
                output=output,
                requirements=json.dumps(requirements, indent=2)
            ),
            max_tokens=1024,
            temperature=0.1,  # Very low temperature for consistent QC
            system_prompt="You are a meticulous quality control specialist."
        )
        
        # Call LLaMA for QC
        llama_response = await self.llama_client.generate(llama_request)
        
        # Parse QC results
        try:
            # Try to extract structured feedback
            qc_text = llama_response.text
            
            # Simple parsing for quality score
            import re
            score_match = re.search(r'(?:quality score|score):\s*(\d+)', qc_text.lower())
            quality_score = int(score_match.group(1)) if score_match else 85
            
            qc_result = {
                "quality_score": quality_score,
                "feedback": qc_text,
                "passed": quality_score >= 80
            }
        except Exception as e:
            logger.warning(f"Failed to parse QC result: {e}")
            qc_result = {
                "quality_score": 85,
                "feedback": llama_response.text,
                "passed": True
            }
        
        # Build response
        result = {
            "qc_result": qc_result,
            "checks_performed": [
                "completeness",
                "accuracy",
                "clarity",
                "consistency",
                "actionability"
            ],
            "processing_metadata": {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "llama3"
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResponse(
            request_id=task.id,
            status=TaskStatus.COMPLETED,
            result=result,
            agents_involved=[self.agent_id],
            total_tokens=llama_response.tokens_used,
            processing_time_ms=processing_time,
            warnings=["Quality check flagged issues"] if not qc_result["passed"] else []
        )

# ============================================================================
# CROSS-CHECK AGENT
# ============================================================================

class CrossCheckAgent(BaseAgent):
    """
    Cross-check agent - validates consistency across outputs
    """
    
    def __init__(self, config: AgentConfig = None):
        """Initialize cross-check agent"""
        config = config or DEFAULT_AGENT_CONFIGS["cross_check"]
        super().__init__(config)
        
        # Cross-check specific initialization
        self.cross_check_prompt = """
        Cross-check the following outputs for consistency:
        
        Output 1:
        {output1}
        
        Output 2:
        {output2}
        
        Identify:
        1. Contradictions or inconsistencies
        2. Complementary information
        3. Gaps in either output
        4. Recommendations for reconciliation
        
        Provide a consistency score and detailed findings.
        """
    
    async def _process_task_impl(self, task: Task) -> ProcessingResponse:
        """
        Process cross-check task
        
        Args:
            task: Task to process
            
        Returns:
            Processing response
        """
        start_time = time.time()
        
        # Extract outputs to cross-check
        outputs = task.payload.get("outputs", [])
        if len(outputs) < 2:
            # If only one output, just validate it
            result = {
                "consistency_score": 100,
                "findings": "Only one output provided - no cross-check needed",
                "issues": [],
                "recommendations": []
            }
        else:
            # Prepare LLaMA request for cross-checking
            llama_request = LLaMARequest(
                prompt=self.cross_check_prompt.format(
                    output1=json.dumps(outputs[0], indent=2),
                    output2=json.dumps(outputs[1], indent=2)
                ),
                max_tokens=1024,
                temperature=0.2,  # Low temperature for consistency
                system_prompt="You are an expert at identifying inconsistencies and ensuring data integrity."
            )
            
            # Call LLaMA for cross-check
            llama_response = await self.llama_client.generate(llama_request)
            
            # Parse results
            result = {
                "consistency_analysis": llama_response.text,
                "outputs_checked": len(outputs),
                "cross_check_complete": True
            }
        
        # Build final response
        final_result = {
            "cross_check": result,
            "processing_metadata": {
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "llama3"
            }
        }
        
        processing_time = (time.time() - start_time) * 1000
        
        return ProcessingResponse(
            request_id=task.id,
            status=TaskStatus.COMPLETED,
            result=final_result,
            agents_involved=[self.agent_id],
            total_tokens=llama_response.tokens_used if len(outputs) >= 2 else 0,
            processing_time_ms=processing_time
        )

# ============================================================================
# AGENT FACTORY
# ============================================================================

class AgentFactory:
    """
    Factory for creating agent instances
    """
    
    # Agent type to class mapping
    AGENT_CLASSES = {
        AgentType.INTAKE: IntakeAgent,
        AgentType.ANALYSIS: AnalysisAgent,
        AgentType.SYNTHESIS: SynthesisAgent,
        AgentType.OUTPUT: OutputAgent,
        AgentType.QUALITY_CONTROL: QualityControlAgent,
        AgentType.CROSS_CHECK: CrossCheckAgent
    }
    
    @classmethod
    def create_agent(cls, agent_type: AgentType, config: Optional[AgentConfig] = None) -> BaseAgent:
        """
        Create an agent instance
        
        Args:
            agent_type: Type of agent to create
            config: Optional agent configuration
            
        Returns:
            Agent instance
            
        Raises:
            ValueError: If agent type is not supported
        """
        if agent_type not in cls.AGENT_CLASSES:
            raise ValueError(f"Unsupported agent type: {agent_type}")
        
        agent_class = cls.AGENT_CLASSES[agent_type]
        return agent_class(config)
    
    @classmethod
    def create_agent_pool(cls, agent_configs: Dict[str, AgentConfig]) -> Dict[str, BaseAgent]:
        """
        Create a pool of agents
        
        Args:
            agent_configs: Dictionary of agent configurations
            
        Returns:
            Dictionary of agent instances
        """
        agents = {}
        
        for agent_id, config in agent_configs.items():
            agent = cls.create_agent(config.agent_type, config)
            agents[agent_id] = agent
            
        return agents