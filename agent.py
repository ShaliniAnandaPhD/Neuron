"""
agent.py - Agent System for Neuron Framework

This module defines the core agent abstractions and functionality for the
Neuron framework. It includes the BaseAgent class that all agents inherit from,
the AgentManager for lifecycle management, and specialized agent templates.

The agent system is analogous to specialized brain regions, with each agent
type having specific capabilities and responsibilities within the larger network.
"""

import asyncio
import inspect
import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from .config import config
from .exceptions import (
    AgentCapabilityError,
    AgentInitializationError,
    AgentProcessingError,
    ValidationError,
)
from .types import (
    AgentCapability,
    AgentID,
    AgentMetrics,
    AgentState,
    Message,
    MessageID,
    MessagePriority,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the Neuron framework.
    
    This abstract class defines the core functionality and interfaces
    that all agents must implement. It handles message processing,
    state management, and provides common utilities.
    
    Conceptually, a BaseAgent is like a specialized brain region that
    has specific capabilities and processes information in a unique way.
    """
    
    def __init__(self, agent_id: Optional[AgentID] = None, name: str = "",
                 description: str = "", metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a new agent.
        
        Args:
            agent_id: Unique identifier for this agent (generated if not provided)
            name: Human-readable name for this agent
            description: Detailed description of this agent's purpose and capabilities
            metadata: Additional contextual information about this agent
        """
        # Core identification
        self.id = agent_id or str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.description = description
        self.metadata = metadata or {}
        
        # State management
        self._state = AgentState.INITIALIZING
        self._state_lock = threading.RLock()
        
        # Processing resources
        self._message_queue = asyncio.Queue()
        self._processing_thread = None
        self._stop_event = threading.Event()
        
        # Metrics and monitoring
        self._metrics = AgentMetrics()
        self._last_metric_update = time.time()
        
        # Capabilities
        self._capabilities = self._discover_capabilities()
        
        # Dependencies
        self._synaptic_bus = None
        self._memory_manager = None
        
        logger.debug(f"Initialized agent: {self.name} ({self.id})")
    
    def initialize(self, synaptic_bus: Any, memory_manager: Any) -> None:
        """
        Initialize the agent with necessary dependencies.
        
        Args:
            synaptic_bus: Communication system for sending/receiving messages
            memory_manager: Memory system for storing/retrieving information
            
        Raises:
            AgentInitializationError: If initialization fails
        """
        with self._state_lock:
            if self._state != AgentState.INITIALIZING:
                raise AgentInitializationError(f"Agent {self.id} is already initialized")
            
            try:
                self._synaptic_bus = synaptic_bus
                self._memory_manager = memory_manager
                
                # Run agent-specific initialization
                self._initialize()
                
                # Update state to ready
                self._state = AgentState.READY
                logger.info(f"Agent {self.name} ({self.id}) initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize agent {self.id}: {e}")
                self._state = AgentState.TERMINATED
                raise AgentInitializationError(f"Failed to initialize agent: {e}") from e
    
    @abstractmethod
    def _initialize(self) -> None:
        """
        Agent-specific initialization.
        
        This method should be implemented by subclasses to perform any
        specialized initialization logic. It is called after the basic
        initialization but before the agent is marked as ready.
        
        Raises:
            AgentInitializationError: If agent-specific initialization fails
        """
        pass
    
    def start(self) -> None:
        """
        Start the agent's message processing.
        
        This begins the agent's processing loop, enabling it to receive
        and handle messages.
        
        Raises:
            AgentInitializationError: If the agent hasn't been initialized
            RuntimeError: If the agent is already started
        """
        with self._state_lock:
            if self._state == AgentState.INITIALIZING:
                raise AgentInitializationError(f"Agent {self.id} hasn't been initialized yet")
            
            if self._state == AgentState.PROCESSING:
                logger.warning(f"Agent {self.id} is already processing")
                return
            
            # Reset the stop event
            self._stop_event.clear()
            
            # Start processing thread
            self._processing_thread = threading.Thread(
                target=self._processing_loop,
                name=f"Agent-{self.id}",
                daemon=True
            )
            self._processing_thread.start()
            
            self._state = AgentState.PROCESSING
            logger.info(f"Agent {self.name} ({self.id}) started processing")
    
    def stop(self) -> None:
        """
        Stop the agent's message processing.
        
        This gracefully terminates the agent's processing loop,
        allowing any in-progress work to complete.
        """
        with self._state_lock:
            if self._state != AgentState.PROCESSING:
                return
            
            # Signal the processing loop to stop
            self._stop_event.set()
            
            # Wait for the processing thread to terminate
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5.0)
                if self._processing_thread.is_alive():
                    logger.warning(f"Agent {self.id} processing thread did not terminate within timeout")
            
            self._state = AgentState.PAUSED
            logger.info(f"Agent {self.name} ({self.id}) stopped processing")
    
    def terminate(self) -> None:
        """
        Permanently terminate the agent.
        
        This stops the agent and releases all resources. After termination,
        the agent cannot be restarted.
        """
        self.stop()
        
        with self._state_lock:
            # Perform cleanup
            self._cleanup()
            
            # Update state
            self._state = AgentState.TERMINATED
            logger.info(f"Agent {self.name} ({self.id}) terminated")
    
    def _cleanup(self) -> None:
        """
        Perform cleanup when the agent is terminated.
        
        This method can be overridden by subclasses to release resources
        or perform other cleanup tasks when the agent is terminated.
        """
        pass
    
    async def receive_message(self, message: Message) -> None:
        """
        Receive a message for processing.
        
        This method places the message in the agent's processing queue.
        
        Args:
            message: The message to process
        """
        if self._state not in (AgentState.READY, AgentState.PROCESSING):
            logger.warning(f"Agent {self.id} received message while not in ready/processing state")
            return
        
        # Add message to the queue
        await self._message_queue.put(message)
        logger.debug(f"Agent {self.id} queued message {message.id} from {message.sender}")
    
    async def send_message(self, recipients: Union[AgentID, List[AgentID]], content: Any,
                          priority: MessagePriority = MessagePriority.NORMAL,
                          metadata: Optional[Dict[str, Any]] = None,
                          trace_id: Optional[str] = None) -> Message:
        """
        Send a message to other agents.
        
        This is the primary way for agents to communicate with each other.
        
        Args:
            recipients: ID or list of IDs of the recipient agents
            content: Message content/payload
            priority: Message priority level
            metadata: Additional context for the message
            trace_id: Optional trace ID for message chains
            
        Returns:
            The sent message
            
        Raises:
            AgentProcessingError: If the message cannot be sent
        """
        if not self._synaptic_bus:
            raise AgentProcessingError("Agent not properly initialized with SynapticBus")
        
        # Normalize recipients to a list
        if isinstance(recipients, str):
            recipients = [recipients]
        
        # Create the message
        message = Message.create(
            sender=self.id,
            recipients=recipients,
            content=content,
            priority=priority,
            metadata=metadata or {},
            trace_id=trace_id
        )
        
        # Send via SynapticBus
        try:
            await self._synaptic_bus.send(message)
            self._metrics.increment_message_count()
            return message
        except Exception as e:
            logger.error(f"Agent {self.id} failed to send message: {e}")
            raise AgentProcessingError(f"Failed to send message: {e}") from e
    
    @abstractmethod
    async def process_message(self, message: Message) -> None:
        """
        Process a received message.
        
        This is the core message handling method that must be implemented
        by all agent subclasses.
        
        Args:
            message: The message to process
            
        Raises:
            AgentProcessingError: If message processing fails
        """
        pass
    
    async def _process_message_with_metrics(self, message: Message) -> None:
        """
        Process a message with metric collection.
        
        This wrapper method measures processing time and collects
        error metrics.
        
        Args:
            message: The message to process
        """
        start_time = time.time()
        try:
            # Process the message
            await self.process_message(message)
            
            # Update metrics
            self._metrics.update_processing_time(time.time() - start_time)
        except Exception as e:
            # Record the error
            self._metrics.increment_error_count()
            processing_time = time.time() - start_time
            self._metrics.update_processing_time(processing_time)
            
            logger.error(f"Agent {self.id} error processing message {message.id}: {e}")
    
    def _processing_loop(self) -> None:
        """
        Main processing loop for the agent.
        
        This method runs in a separate thread and continuously processes
        messages from the agent's message queue until stopped.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async processing loop
            loop.run_until_complete(self._async_processing_loop())
        except Exception as e:
            logger.error(f"Error in agent {self.id} processing loop: {e}")
        finally:
            # Clean up the event loop
            loop.close()
    
    async def _async_processing_loop(self) -> None:
        """
        Asynchronous processing loop implementation.
        
        This continuously processes messages from the queue in an
        asynchronous manner, respecting priority.
        """
        while not self._stop_event.is_set():
            try:
                # Get the next message with a timeout
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    # No message within timeout, check stop condition
                    continue
                
                # Process the message
                await self._process_message_with_metrics(message)
                
                # Mark the message as processed
                self._message_queue.task_done()
                
                # Update monitoring metrics periodically
                current_time = time.time()
                if current_time - self._last_metric_update > 5.0:
                    self._update_metrics()
                    self._last_metric_update = current_time
            except Exception as e:
                logger.error(f"Unexpected error in agent {self.id} processing loop: {e}")
    
    def _update_metrics(self) -> None:
        """Update agent metrics for monitoring."""
        # Update memory usage estimate (simple implementation)
        import sys
        self._metrics.memory_usage = sys.getsizeof(self) / 1024  # KB
        
        # Add agent-specific metrics updates here
    
    def get_metrics(self) -> AgentMetrics:
        """
        Get the current agent metrics.
        
        Returns:
            Current metrics for this agent
        """
        self._update_metrics()
        return self._metrics
    
    def get_state(self) -> AgentState:
        """
        Get the current agent state.
        
        Returns:
            Current state of this agent
        """
        with self._state_lock:
            return self._state
    
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Get the capabilities of this agent.
        
        Returns:
            List of capabilities this agent provides
        """
        return list(self._capabilities.values())
    
    def has_capability(self, capability_name: str) -> bool:
        """
        Check if this agent has a specific capability.
        
        Args:
            capability_name: Name of the capability to check
            
        Returns:
            True if the agent has the capability, False otherwise
        """
        return capability_name in self._capabilities
    
    def _discover_capabilities(self) -> Dict[str, AgentCapability]:
        """
        Discover agent capabilities from method annotations.
        
        This examines methods decorated with @capability to build
        a map of the agent's capabilities.
        
        Returns:
            Dictionary mapping capability names to capabilities
        """
        capabilities = {}
        
        # Search for methods with capability decorator
        for name, method in inspect.getmembers(self, inspect.ismethod):
            if hasattr(method, '_capability'):
                capability = method._capability
                capabilities[capability.name] = capability
        
        return capabilities
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert agent to a dictionary representation.
        
        Returns:
            Dictionary representation of the agent
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.get_state().name,
            "metrics": self.get_metrics().to_dict(),
            "capabilities": [cap.to_dict() for cap in self.get_capabilities()],
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.name} ({self.id})"


def capability(name: str, description: str,
              input_schema: Optional[Dict] = None,
              output_schema: Optional[Dict] = None,
              **parameters: Any) -> Callable:
    """
    Decorator to mark a method as an agent capability.
    
    This decorator is used to define the capabilities of an agent,
    which are discoverable and can be used for agent composition.
    
    Args:
        name: Name of the capability
        description: Detailed description of what the capability does
        input_schema: Optional schema defining expected inputs
        output_schema: Optional schema defining produced outputs
        **parameters: Additional capability parameters
        
    Returns:
        Decorator function
    """
    def decorator(method: Callable) -> Callable:
        # Create the capability definition
        method._capability = AgentCapability(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            parameters=parameters
        )
        return method
    return decorator


# Agent lifecycle management system

@dataclass
class AgentConfig:
    """
    Configuration for creating an agent.
    
    This dataclass encapsulates all the parameters needed to create
    and initialize an agent instance.
    """
    agent_type: Type[BaseAgent]
    agent_id: Optional[AgentID] = None
    name: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    config_params: Dict[str, Any] = field(default_factory=dict)


class AgentManager:
    """
    Manages the lifecycle of all agents in the system.
    
    The AgentManager is responsible for creating, initializing, starting,
    stopping, and terminating agents, as well as providing access to
    agent instances.
    
    Conceptually, the AgentManager is like the brain's regulatory systems
    that control the activation and deactivation of different brain regions.
    """
    
    def __init__(self):
        """Initialize the agent manager."""
        self._agents = {}  # AgentID -> Agent
        self._agent_types = {}  # Agent type name -> Agent class
        self._lock = threading.RLock()
        self._synaptic_bus = None
        self._memory_manager = None
        
        logger.info("Initialized AgentManager")
    
    def initialize(self, synaptic_bus: Any, memory_manager: Any) -> None:
        """
        Initialize the agent manager with required dependencies.
        
        Args:
            synaptic_bus: Communication system for agents
            memory_manager: Memory system for agents
        """
        self._synaptic_bus = synaptic_bus
        self._memory_manager = memory_manager
        
        # Register built-in agent types
        self._register_built_in_agent_types()
        
        logger.info("AgentManager initialized with dependencies")
    
    def start(self) -> None:
        """Start the agent manager and any automatically started agents."""
        with self._lock:
            for agent in self._agents.values():
                if agent.get_state() == AgentState.READY:
                    agent.start()
        
        logger.info("AgentManager started")
    
    def stop(self) -> None:
        """Stop all agents managed by this agent manager."""
        with self._lock:
            for agent in self._agents.values():
                if agent.get_state() == AgentState.PROCESSING:
                    agent.stop()
        
        logger.info("AgentManager stopped all agents")
    
    def _register_built_in_agent_types(self) -> None:
        """Register built-in agent types with the manager."""
        # Register core agent types
        self.register_agent_type(ReflexAgent)
        self.register_agent_type(DeliberativeAgent)
        self.register_agent_type(LearningAgent)
        self.register_agent_type(CoordinatorAgent)
        
        logger.debug("Registered built-in agent types")
    
    def register_agent_type(self, agent_class: Type[BaseAgent]) -> None:
        """
        Register an agent type with the manager.
        
        Args:
            agent_class: Agent class to register
            
        Raises:
            TypeError: If the class doesn't inherit from BaseAgent
            ValueError: If an agent type with the same name is already registered
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"Agent class {agent_class.__name__} must inherit from BaseAgent")
        
        with self._lock:
            type_name = agent_class.__name__
            if type_name in self._agent_types:
                raise ValueError(f"Agent type {type_name} is already registered")
            
            self._agent_types[type_name] = agent_class
            logger.debug(f"Registered agent type: {type_name}")
    
    def create_agent(self, config: AgentConfig) -> AgentID:
        """
        Create a new agent based on the provided configuration.
        
        Args:
            config: Configuration for the agent
            
        Returns:
            ID of the created agent
            
        Raises:
            AgentInitializationError: If agent creation or initialization fails
        """
        with self._lock:
            try:
                # Create agent instance
                agent = config.agent_type(
                    agent_id=config.agent_id,
                    name=config.name,
                    description=config.description,
                    metadata=config.metadata
                )
                
                # Apply configuration parameters
                for key, value in config.config_params.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)
                
                # Initialize the agent
                agent.initialize(self._synaptic_bus, self._memory_manager)
                
                # Register the agent
                self._agents[agent.id] = agent
                logger.info(f"Created agent: {agent.name} ({agent.id})")
                
                return agent.id
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
                raise AgentInitializationError(f"Failed to create agent: {e}") from e
    
    def start_agent(self, agent_id: AgentID) -> None:
        """
        Start an agent by ID.
        
        Args:
            agent_id: ID of the agent to start
            
        Raises:
            ValueError: If the agent doesn't exist
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} does not exist")
            
            agent.start()
    
    def stop_agent(self, agent_id: AgentID) -> None:
        """
        Stop an agent by ID.
        
        Args:
            agent_id: ID of the agent to stop
            
        Raises:
            ValueError: If the agent doesn't exist
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} does not exist")
            
            agent.stop()
    
    def terminate_agent(self, agent_id: AgentID) -> None:
        """
        Terminate an agent by ID and remove it from management.
        
        Args:
            agent_id: ID of the agent to terminate
            
        Raises:
            ValueError: If the agent doesn't exist
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} does not exist")
            
            agent.terminate()
            del self._agents[agent_id]
    
    def get_agent(self, agent_id: AgentID) -> Optional[BaseAgent]:
        """
        Get an agent by ID.
        
        Args:
            agent_id: ID of the agent to get
            
        Returns:
            The agent instance, or None if not found
        """
        return self._agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[AgentID, BaseAgent]:
        """
        Get all managed agents.
        
        Returns:
            Dictionary mapping agent IDs to agent instances
        """
        with self._lock:
            return self._agents.copy()
    
    def get_agent_type(self, type_name: str) -> Optional[Type[BaseAgent]]:
        """
        Get an agent type by name.
        
        Args:
            type_name: Name of the agent type
            
        Returns:
            The agent class, or None if not found
        """
        return self._agent_types.get(type_name)
    
    def get_all_agent_types(self) -> Dict[str, Type[BaseAgent]]:
        """
        Get all registered agent types.
        
        Returns:
            Dictionary mapping type names to agent classes
        """
        with self._lock:
            return self._agent_types.copy()
    
    def find_agents_by_capability(self, capability_name: str) -> List[AgentID]:
        """
        Find agents that have a specific capability.
        
        Args:
            capability_name: Name of the capability to search for
            
        Returns:
            List of IDs of agents with the specified capability
        """
        matching_agents = []
        with self._lock:
            for agent_id, agent in self._agents.items():
                if agent.has_capability(capability_name):
                    matching_agents.append(agent_id)
        
        return matching_agents
    
    def get_agent_metrics(self, agent_id: AgentID) -> Optional[AgentMetrics]:
        """
        Get metrics for a specific agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent metrics, or None if the agent doesn't exist
        """
        agent = self.get_agent(agent_id)
        if agent:
            return agent.get_metrics()
        return None
    
    def get_all_agent_metrics(self) -> Dict[AgentID, AgentMetrics]:
        """
        Get metrics for all managed agents.
        
        Returns:
            Dictionary mapping agent IDs to their metrics
        """
        metrics = {}
        with self._lock:
            for agent_id, agent in self._agents.items():
                metrics[agent_id] = agent.get_metrics()
        
        return metrics


# Specialized Agent Types (Templates)

class ReflexAgent(BaseAgent):
    """
    Simple agent that responds to messages based on predefined rules.
    
    Inspired by reflex behaviors in the brain, a ReflexAgent processes
    inputs according to a set of condition-action rules, providing immediate
    responses without complex reasoning.
    """
    
    def __init__(self, agent_id: Optional[AgentID] = None, name: str = "",
                 description: str = "", metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a reflex agent.
        
        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name for this agent
            description: Detailed description of this agent's purpose
            metadata: Additional contextual information
        """
        super().__init__(agent_id, name or "ReflexAgent", 
                        description or "Agent that responds based on predefined rules",
                        metadata)
        
        # Reflex rules: condition -> action
        self.rules = {}
    
    def _initialize(self) -> None:
        """Agent-specific initialization."""
        # Load default rules if none are defined
        if not self.rules:
            self.rules = self._get_default_rules()
    
    def _get_default_rules(self) -> Dict[str, Callable]:
        """
        Get default reflex rules.
        
        This can be overridden by subclasses to provide
        domain-specific default rules.
        
        Returns:
            Dictionary mapping condition names to action functions
        """
        return {
            "echo": lambda msg: {"response": f"Echo: {msg.content}"}
        }
    
    def add_rule(self, condition_name: str, action: Callable) -> None:
        """
        Add a new reflex rule.
        
        Args:
            condition_name: Name/identifier for the condition
            action: Function that takes a message and returns a response
        """
        self.rules[condition_name] = action
    
    def remove_rule(self, condition_name: str) -> None:
        """
        Remove a reflex rule.
        
        Args:
            condition_name: Name/identifier for the condition to remove
        """
        if condition_name in self.rules:
            del self.rules[condition_name]
    
    @capability(
        name="process_reflex",
        description="Process input according to reflex rules",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    async def process_message(self, message: Message) -> None:
        """
        Process a message according to reflex rules.
        
        For each rule, check if the condition matches and execute
        the corresponding action.
        
        Args:
            message: The message to process
        """
        responses = {}
        
        # Process rules
        for condition_name, action in self.rules.items():
            # Check message content for condition (simple string matching for this example)
            if isinstance(message.content, dict) and condition_name in message.content.get("type", ""):
                # Execute the action
                try:
                    result = action(message)
                    responses[condition_name] = result
                except Exception as e:
                    logger.error(f"Error executing rule {condition_name}: {e}")
            elif isinstance(message.content, str) and condition_name in message.content:
                # String content handling
                try:
                    result = action(message)
                    responses[condition_name] = result
                except Exception as e:
                    logger.error(f"Error executing rule {condition_name}: {e}")
        
        # If any rules matched, send response
        if responses and message.sender != self.id:
            await self.send_message(
                recipients=message.sender,
                content=responses,
                metadata={"in_response_to": message.id}
            )


class DeliberativeAgent(BaseAgent):
    """
    Agent that performs deliberative reasoning to process messages.
    
    Inspired by the brain's prefrontal cortex, a DeliberativeAgent
    uses model-based reasoning to evaluate options and plan responses,
    allowing for more complex decision-making than reflex agents.
    """
    
    def __init__(self, agent_id: Optional[AgentID] = None, name: str = "",
                 description: str = "", metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a deliberative agent.
        
        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name for this agent
            description: Detailed description of this agent's purpose
            metadata: Additional contextual information
        """
        super().__init__(agent_id, name or "DeliberativeAgent", 
                         description or "Agent that uses deliberative reasoning",
                         metadata)
        
        # Processing model and strategies
        self.reasoning_model = None
        self.planning_depth = 3  # Default planning depth (steps ahead to consider)
        self.evaluation_criteria = {}  # Criteria for evaluating options
    
    def _initialize(self) -> None:
        """Agent-specific initialization."""
        # Initialize reasoning model and evaluation criteria
        self._setup_reasoning_model()
        
        if not self.evaluation_criteria:
            self.evaluation_criteria = self._get_default_evaluation_criteria()
    
    def _setup_reasoning_model(self) -> None:
        """
        Setup the reasoning model for this agent.
        
        This method should be overridden by subclasses to provide
        domain-specific reasoning models.
        """
        # Default simple reasoning model
        self.reasoning_model = {
            "process_steps": [
                "understand_request",
                "generate_options",
                "evaluate_options",
                "select_best_option",
                "execute_action"
            ]
        }
    
    def _get_default_evaluation_criteria(self) -> Dict[str, float]:
        """
        Get default criteria for evaluating options.
        
        Returns:
            Dictionary mapping criteria names to weights
        """
        return {
            "efficiency": 0.3,
            "completeness": 0.3,
            "reliability": 0.2,
            "innovation": 0.1,
            "simplicity": 0.1
        }
    
    def set_evaluation_criteria(self, criteria: Dict[str, float]) -> None:
        """
        Set the criteria for evaluating options.
        
        Args:
            criteria: Dictionary mapping criteria names to weights
        
        Raises:
            ValueError: If weights don't sum to 1.0
        """
        total_weight = sum(criteria.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Evaluation criteria weights must sum to 1.0, got {total_weight}")
        
        self.evaluation_criteria = criteria
    
    def set_planning_depth(self, depth: int) -> None:
        """
        Set the planning depth (steps ahead to consider).
        
        Args:
            depth: Number of steps ahead to consider
            
        Raises:
            ValueError: If depth is less than 1
        """
        if depth < 1:
            raise ValueError("Planning depth must be at least 1")
        
        self.planning_depth = depth
    
    @capability(
        name="deliberative_reasoning",
        description="Process input using deliberative reasoning",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    async def process_message(self, message: Message) -> None:
        """
        Process a message using deliberative reasoning.
        
        This implements a simple deliberative reasoning process:
        1. Understand the request
        2. Generate options
        3. Evaluate options
        4. Select the best option
        5. Execute the selected action
        
        Args:
            message: The message to process
        """
        # Skip processing messages from self
        if message.sender == self.id:
            return
        
        # Step 1: Understand the request
        request = self._understand_request(message)
        
        # Step 2: Generate options
        options = self._generate_options(request)
        
        # Step 3: Evaluate options
        evaluated_options = self._evaluate_options(options, request)
        
        # Step 4: Select the best option
        best_option = self._select_best_option(evaluated_options)
        
        # Step 5: Execute the selected action
        result = self._execute_action(best_option, request)
        
        # Send response
        await self.send_message(
            recipients=message.sender,
            content=result,
            metadata={"in_response_to": message.id, "reasoning_path": "deliberative"}
        )
    
    def _understand_request(self, message: Message) -> Dict[str, Any]:
        """
        Understand the request in the message.
        
        This method should be overridden by subclasses to provide
        domain-specific request understanding.
        
        Args:
            message: The message to understand
            
        Returns:
            Dictionary representing the understood request
        """
        # Default simple understanding
        request = {
            "original_message": message,
            "sender": message.sender,
            "timestamp": message.created_at,
            "understood_content": message.content
        }
        return request
    
    def _generate_options(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate options for responding to the request.
        
        This method should be overridden by subclasses to provide
        domain-specific option generation.
        
        Args:
            request: The understood request
            
        Returns:
            List of options (each as a dictionary)
        """
        # Default simple option generation
        options = [
            {"type": "direct_response", "content": request["understood_content"]},
            {"type": "elaborated_response", "content": f"Elaborated: {request['understood_content']}"},
            {"type": "minimal_response", "content": "Acknowledged"}
        ]
        return options
    
    def _evaluate_options(self, options: List[Dict[str, Any]], 
                         request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate options against criteria.
        
        This method should be overridden by subclasses to provide
        domain-specific option evaluation.
        
        Args:
            options: List of options to evaluate
            request: The understood request
            
        Returns:
            List of options with evaluation scores
        """
        # Default simple evaluation
        evaluated_options = []
        for option in options:
            # Assign default scores for each criterion
            scores = {
                "efficiency": 0.5,
                "completeness": 0.5,
                "reliability": 0.5,
                "innovation": 0.5,
                "simplicity": 0.5
            }
            
            # Adjust scores based on option type (just an example)
            if option["type"] == "direct_response":
                scores["efficiency"] = 0.8
                scores["simplicity"] = 0.9
            elif option["type"] == "elaborated_response":
                scores["completeness"] = 0.9
                scores["innovation"] = 0.7
            elif option["type"] == "minimal_response":
                scores["efficiency"] = 0.9
                scores["simplicity"] = 1.0
                scores["completeness"] = 0.2
            
            # Calculate total score
            total_score = sum(scores[criterion] * weight 
                             for criterion, weight in self.evaluation_criteria.items())
            
            evaluated_options.append({
                **option,
                "scores": scores,
                "total_score": total_score
            })
        
        return evaluated_options
    
    def _select_best_option(self, evaluated_options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select the best option based on evaluation.
        
        Args:
            evaluated_options: List of options with evaluation scores
            
        Returns:
            The best option
        """
        # Select the option with the highest total score
        best_option = max(evaluated_options, key=lambda x: x["total_score"])
        return best_option
    
    def _execute_action(self, option: Dict[str, Any], 
                       request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the selected action.
        
        This method should be overridden by subclasses to provide
        domain-specific action execution.
        
        Args:
            option: The selected option
            request: The understood request
            
        Returns:
            Result of executing the action
        """
        # Default simple execution
        result = {
            "type": option["type"],
            "content": option["content"],
            "confidence": option["total_score"],
            "request_understood": True
        }
        return result


class LearningAgent(BaseAgent):
    """
    Agent that learns from experience to improve performance.
    
    Inspired by the brain's ability to learn and adapt, a LearningAgent
    updates its behavior based on feedback and experience, allowing it
    to improve over time.
    """
    
    def __init__(self, agent_id: Optional[AgentID] = None, name: str = "",
                 description: str = "", metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a learning agent.
        
        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name for this agent
            description: Detailed description of this agent's purpose
            metadata: Additional contextual information
        """
        super().__init__(agent_id, name or "LearningAgent", 
                         description or "Agent that learns from experience",
                         metadata)
        
        # Learning parameters
        self.learning_rate = 0.1
        self.exploration_rate = 0.2
        self.discount_factor = 0.9
        
        # Knowledge base and learning model
        self.knowledge_base = {}
        self.learned_patterns = {}
        self.experience_history = []
        self.max_history_size = 1000
    
    def _initialize(self) -> None:
        """Agent-specific initialization."""
        # Initialize knowledge base and learning model
        self._setup_learning_model()
    
    def _setup_learning_model(self) -> None:
        """
        Setup the learning model for this agent.
        
        This method should be overridden by subclasses to provide
        domain-specific learning models.
        """
        # Default simple learning model
        self.knowledge_base = {
            "concepts": {},
            "patterns": {},
            "feedback": {}
        }
    
    def set_learning_parameters(self, learning_rate: float, 
                               exploration_rate: float,
                               discount_factor: float) -> None:
        """
        Set learning parameters.
        
        Args:
            learning_rate: Rate at which the agent learns (0.0 to 1.0)
            exploration_rate: Rate at which the agent explores new options (0.0 to 1.0)
            discount_factor: Factor for weighing future rewards (0.0 to 1.0)
            
        Raises:
            ValueError: If parameters are outside the valid range
        """
        if not 0.0 <= learning_rate <= 1.0:
            raise ValueError("Learning rate must be between 0.0 and 1.0")
        if not 0.0 <= exploration_rate <= 1.0:
            raise ValueError("Exploration rate must be between 0.0 and 1.0")
        if not 0.0 <= discount_factor <= 1.0:
            raise ValueError("Discount factor must be between 0.0 and 1.0")
        
        self.learning_rate = learning_rate
        self.exploration_rate = exploration_rate
        self.discount_factor = discount_factor
    
    def add_to_knowledge_base(self, concept: str, data: Any) -> None:
        """
        Add information to the knowledge base.
        
        Args:
            concept: Concept/category name
            data: Information to store
        """
        if concept not in self.knowledge_base["concepts"]:
            self.knowledge_base["concepts"][concept] = []
        
        self.knowledge_base["concepts"][concept].append(data)
    
    def record_experience(self, experience: Dict[str, Any]) -> None:
        """
        Record an experience for learning.
        
        Args:
            experience: Dictionary describing the experience
        """
        # Add timestamp if not present
        if "timestamp" not in experience:
            experience["timestamp"] = time.time()
        
        # Add to history
        self.experience_history.append(experience)
        
        # Trim history if it exceeds maximum size
        if len(self.experience_history) > self.max_history_size:
            self.experience_history = self.experience_history[-self.max_history_size:]
        
        # Learn from the new experience
        self._learn_from_experience(experience)
    
    def _learn_from_experience(self, experience: Dict[str, Any]) -> None:
        """
        Learn from a single experience.
        
        This method should be overridden by subclasses to provide
        domain-specific learning algorithms.
        
        Args:
            experience: Dictionary describing the experience
        """
        # Default simple pattern recognition
        if "pattern_key" in experience and "pattern_value" in experience:
            key = experience["pattern_key"]
            value = experience["pattern_value"]
            
            if key not in self.learned_patterns:
                self.learned_patterns[key] = {"values": [], "counts": {}}
            
            # Record the observed value
            self.learned_patterns[key]["values"].append(value)
            
            # Update counts
            if value not in self.learned_patterns[key]["counts"]:
                self.learned_patterns[key]["counts"][value] = 0
            self.learned_patterns[key]["counts"][value] += 1
    
    def receive_feedback(self, feedback_id: str, score: float, metadata: Dict[str, Any]) -> None:
        """
        Receive feedback on agent performance.
        
        Args:
            feedback_id: Identifier for what the feedback relates to
            score: Feedback score (-1.0 to 1.0)
            metadata: Additional information about the feedback
            
        Raises:
            ValueError: If score is outside the valid range
        """
        if not -1.0 <= score <= 1.0:
            raise ValueError("Feedback score must be between -1.0 and 1.0")
        
        # Store feedback
        if feedback_id not in self.knowledge_base["feedback"]:
            self.knowledge_base["feedback"][feedback_id] = []
        
        feedback_entry = {
            "score": score,
            "timestamp": time.time(),
            "metadata": metadata
        }
        self.knowledge_base["feedback"][feedback_id].append(feedback_entry)
        
        # Learn from feedback
        self._learn_from_feedback(feedback_id, score, metadata)
    
    def _learn_from_feedback(self, feedback_id: str, score: float, 
                           metadata: Dict[str, Any]) -> None:
        """
        Learn from feedback.
        
        This method should be overridden by subclasses to provide
        domain-specific feedback learning algorithms.
        
        Args:
            feedback_id: Identifier for what the feedback relates to
            score: Feedback score (-1.0 to 1.0)
            metadata: Additional information about the feedback
        """
        # Default simple reinforcement
        # Example: Adjust exploration rate based on feedback
        if score > 0.5:
            # Positive feedback, reduce exploration
            self.exploration_rate = max(0.05, self.exploration_rate * 0.9)
        elif score < -0.5:
            # Negative feedback, increase exploration
            self.exploration_rate = min(0.5, self.exploration_rate * 1.1)
    
    def predict_pattern(self, key: str) -> Optional[Any]:
        """
        Predict the next value in a pattern.
        
        Args:
            key: Pattern key
            
        Returns:
            Predicted value, or None if not enough data
        """
        if key not in self.learned_patterns:
            return None
        
        pattern = self.learned_patterns[key]
        if not pattern["values"]:
            return None
        
        # Simple prediction: most common value
        most_common = max(pattern["counts"].items(), key=lambda x: x[1])
        return most_common[0]
    
    @capability(
        name="learning_process",
        description="Process input using learning algorithms",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    async def process_message(self, message: Message) -> None:
        """
        Process a message using learning algorithms.
        
        This implements a learning-based processing approach:
        1. Extract features from the message
        2. Match against known patterns
        3. Generate a response based on learned patterns
        4. Update learning model based on the interaction
        
        Args:
            message: The message to process
        """
        # Skip processing messages from self
        if message.sender == self.id:
            return
        
        # Extract features from the message
        features = self._extract_features(message)
        
        # Decide whether to explore or exploit
        if random.random() < self.exploration_rate:
            # Exploration: try something new
            response = self._generate_exploratory_response(features)
            response_type = "exploratory"
        else:
            # Exploitation: use learned patterns
            response = self._generate_learned_response(features)
            response_type = "learned"
        
        # Record the experience
        experience = {
            "message_id": message.id,
            "sender": message.sender,
            "features": features,
            "response": response,
            "response_type": response_type
        }
        self.record_experience(experience)
        
        # Send response
        await self.send_message(
            recipients=message.sender,
            content=response,
            metadata={"in_response_to": message.id, "response_type": response_type}
        )
    
    def _extract_features(self, message: Message) -> Dict[str, Any]:
        """
        Extract features from a message.
        
        This method should be overridden by subclasses to provide
        domain-specific feature extraction.
        
        Args:
            message: The message to extract features from
            
        Returns:
            Dictionary of extracted features
        """
        # Default simple feature extraction
        features = {
            "length": len(str(message.content)),
            "timestamp": message.created_at,
            "has_metadata": bool(message.metadata)
        }
        
        # Extract more features based on content type
        if isinstance(message.content, dict):
            features["content_type"] = "dict"
            features["keys"] = list(message.content.keys())
        elif isinstance(message.content, list):
            features["content_type"] = "list"
            features["list_length"] = len(message.content)
        elif isinstance(message.content, str):
            features["content_type"] = "string"
            features["word_count"] = len(message.content.split())
        else:
            features["content_type"] = str(type(message.content))
        
        return features
    
    def _generate_exploratory_response(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an exploratory response to try something new.
        
        This method should be overridden by subclasses to provide
        domain-specific exploration strategies.
        
        Args:
            features: Extracted features from the message
            
        Returns:
            Response content
        """
        # Default simple exploration
        response_types = ["question", "reflection", "hypothesis", "random"]
        selected_type = random.choice(response_types)
        
        if selected_type == "question":
            response = {
                "type": "question",
                "content": "Can you provide more information about this?"
            }
        elif selected_type == "reflection":
            response = {
                "type": "reflection",
                "content": f"I notice this is a {features['content_type']} with {features.get('length', 'unknown')} characters."
            }
        elif selected_type == "hypothesis":
            response = {
                "type": "hypothesis",
                "content": "Based on limited data, I hypothesize this is about general information exchange."
            }
        else:  # random
            response = {
                "type": "experimental",
                "content": "I'm trying a new approach to process this information."
            }
        
        return response
    
    def _generate_learned_response(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a response based on learned patterns.
        
        This method should be overridden by subclasses to provide
        domain-specific learned response generation.
        
        Args:
            features: Extracted features from the message
            
        Returns:
            Response content
        """
        # Default simple learned response
        response = {"type": "learned"}
        
        # Look for matching patterns in experience history
        matching_experiences = []
        for exp in self.experience_history:
            if exp.get("features", {}).get("content_type") == features.get("content_type"):
                matching_experiences.append(exp)
        
        if matching_experiences:
            # Find the experience with the most similar features
            best_match = max(matching_experiences, 
                            key=lambda x: self._calculate_similarity(x["features"], features))
            
            # Base response on the best match
            response["content"] = f"Based on my learning, I'm responding similarly to a previous interaction."
            response["confidence"] = self._calculate_similarity(best_match["features"], features)
            response["pattern_recognized"] = True
        else:
            # No matching patterns found
            response["content"] = "I don't have enough experience with this type of input yet."
            response["confidence"] = 0.1
            response["pattern_recognized"] = False
        
        return response
    
    def _calculate_similarity(self, features1: Dict[str, Any], 
                            features2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two feature sets.
        
        This method should be overridden by subclasses to provide
        domain-specific similarity calculation.
        
        Args:
            features1: First feature set
            features2: Second feature set
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Default simple similarity calculation
        # Count matching features
        common_keys = set(features1.keys()) & set(features2.keys())
        if not common_keys:
            return 0.0
        
        matches = 0
        for key in common_keys:
            if features1[key] == features2[key]:
                matches += 1
        
        return matches / len(common_keys)


class CoordinatorAgent(BaseAgent):
    """
    Agent that coordinates multiple other agents.
    
    Inspired by the brain's executive functions, a CoordinatorAgent
    orchestrates the activities of other agents, delegating tasks and
    aggregating results to solve complex problems that require multiple
    specialized capabilities.
    """
    
    def __init__(self, agent_id: Optional[AgentID] = None, name: str = "",
                 description: str = "", metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a coordinator agent.
        
        Args:
            agent_id: Unique identifier for this agent
            name: Human-readable name for this agent
            description: Detailed description of this agent's purpose
            metadata: Additional contextual information
        """
        super().__init__(agent_id, name or "CoordinatorAgent", 
                         description or "Agent that coordinates multiple agents",
                         metadata)
        
        # Coordination resources
        self.managed_agents = []  # List of agent IDs this coordinator manages
        self.coordination_strategies = {}  # Strategy name -> coordination function
        self.task_registry = {}  # Task ID -> task metadata
        self.active_workflows = {}  # Workflow ID -> workflow state
    
    def _initialize(self) -> None:
        """Agent-specific initialization."""
        # Initialize coordination strategies
        self._setup_coordination_strategies()
    
    def _setup_coordination_strategies(self) -> None:
        """
        Setup coordination strategies.
        
        This method should be overridden by subclasses to provide
        domain-specific coordination strategies.
        """
        # Default coordination strategies
        self.coordination_strategies = {
            "sequential": self._sequential_coordination,
            "parallel": self._parallel_coordination,
            "hierarchical": self._hierarchical_coordination
        }
    
    def add_managed_agent(self, agent_id: AgentID) -> None:
        """
        Add an agent to be managed by this coordinator.
        
        Args:
            agent_id: ID of the agent to manage
        """
        if agent_id not in self.managed_agents:
            self.managed_agents.append(agent_id)
    
    def remove_managed_agent(self, agent_id: AgentID) -> None:
        """
        Remove an agent from this coordinator's management.
        
        Args:
            agent_id: ID of the agent to remove
        """
        if agent_id in self.managed_agents:
            self.managed_agents.remove(agent_id)
    
    def register_task(self, task_id: str, task_metadata: Dict[str, Any]) -> None:
        """
        Register a task with this coordinator.
        
        Args:
            task_id: Unique identifier for the task
            task_metadata: Metadata about the task
        """
        self.task_registry[task_id] = {
            **task_metadata,
            "registered_at": time.time(),
            "status": "registered"
        }
    
    def update_task_status(self, task_id: str, status: str,
                          result: Optional[Any] = None) -> None:
        """
        Update the status of a registered task.
        
        Args:
            task_id: ID of the task to update
            status: New status of the task
            result: Optional result of the task
            
        Raises:
            ValueError: If the task is not registered
        """
        if task_id not in self.task_registry:
            raise ValueError(f"Task {task_id} is not registered")
        
        self.task_registry[task_id]["status"] = status
        self.task_registry[task_id]["updated_at"] = time.time()
        
        if result is not None:
            self.task_registry[task_id]["result"] = result
    
    def start_workflow(self, workflow_id: str, workflow_type: str,
                      workflow_data: Dict[str, Any]) -> str:
        """
        Start a new coordination workflow.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_type: Type of workflow (e.g., "sequential", "parallel")
            workflow_data: Data needed for the workflow
            
        Returns:
            ID of the started workflow
            
        Raises:
            ValueError: If the workflow type is not supported
        """
        if workflow_type not in self.coordination_strategies:
            raise ValueError(f"Workflow type {workflow_type} is not supported")
        
        # Create workflow state
        workflow_state = {
            "id": workflow_id,
            "type": workflow_type,
            "data": workflow_data,
            "status": "started",
            "started_at": time.time(),
            "steps_completed": 0,
            "agent_results": {}
        }
        
        self.active_workflows[workflow_id] = workflow_state
        return workflow_id
    
    async def _sequential_coordination(self, workflow_id: str) -> Dict[str, Any]:
        """
        Implement sequential coordination strategy.
        
        In this strategy, agents are activated one after another in a sequence.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow result
            
        Raises:
            ValueError: If the workflow is not active
        """
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} is not active")
        
        workflow = self.active_workflows[workflow_id]
        sequence = workflow["data"].get("sequence", self.managed_agents)
        input_data = workflow["data"].get("input_data", {})
        
        result = input_data
        
        # Process agents in sequence
        for agent_id in sequence:
            # Skip agents not managed by this coordinator
            if agent_id not in self.managed_agents:
                continue
            
            # Prepare message for the agent
            message = Message.create(
                sender=self.id,
                recipients=[agent_id],
                content={
                    "workflow_id": workflow_id,
                    "step": workflow["steps_completed"] + 1,
                    "data": result
                }
            )
            
            # Send message to the agent
            await self._synaptic_bus.send(message)
            
            # Wait for response (simplified for example)
            # In a real implementation, this would use a proper async wait mechanism
            response_message = await self._wait_for_response(agent_id, message.id)
            
            # Update workflow state
            workflow["steps_completed"] += 1
            workflow["agent_results"][agent_id] = response_message.content
            
            # Update result for next agent in sequence
            result = response_message.content
        
        # Finalize workflow
        workflow["status"] = "completed"
        workflow["completed_at"] = time.time()
        workflow["result"] = result
        
        return result
    
    async def _parallel_coordination(self, workflow_id: str) -> Dict[str, Any]:
        """
        Implement parallel coordination strategy.
        
        In this strategy, all agents are activated simultaneously.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow result
            
        Raises:
            ValueError: If the workflow is not active
        """
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} is not active")
        
        workflow = self.active_workflows[workflow_id]
        agents = workflow["data"].get("agents", self.managed_agents)
        input_data = workflow["data"].get("input_data", {})
        
        # Send messages to all agents in parallel
        message_ids = {}
        for agent_id in agents:
            # Skip agents not managed by this coordinator
            if agent_id not in self.managed_agents:
                continue
            
            # Prepare message for the agent
            message = Message.create(
                sender=self.id,
                recipients=[agent_id],
                content={
                    "workflow_id": workflow_id,
                    "parallel": True,
                    "data": input_data
                }
            )
            
            # Send message to the agent
            await self._synaptic_bus.send(message)
            message_ids[agent_id] = message.id
        
        # Wait for all responses
        # In a real implementation, this would use something like asyncio.gather
        all_results = {}
        for agent_id, message_id in message_ids.items():
            response_message = await self._wait_for_response(agent_id, message_id)
            all_results[agent_id] = response_message.content
        
        # Update workflow state
        workflow["steps_completed"] = 1
        workflow["agent_results"] = all_results
        
        # Aggregate results (simple aggregation for example)
        aggregated_result = {
            "type": "parallel_aggregation",
            "results": all_results
        }
        
        # Finalize workflow
        workflow["status"] = "completed"
        workflow["completed_at"] = time.time()
        workflow["result"] = aggregated_result
        
        return aggregated_result
    
    async def _hierarchical_coordination(self, workflow_id: str) -> Dict[str, Any]:
        """
        Implement hierarchical coordination strategy.
        
        In this strategy, agents are organized in a hierarchy, with
        higher-level agents delegating to and aggregating from lower-level agents.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow result
            
        Raises:
            ValueError: If the workflow is not active
        """
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} is not active")
        
        workflow = self.active_workflows[workflow_id]
        hierarchy = workflow["data"].get("hierarchy", {})
        input_data = workflow["data"].get("input_data", {})
        
        if not hierarchy:
            # Fall back to sequential if no hierarchy defined
            return await self._sequential_coordination(workflow_id)
        
        # Process the hierarchy (simplified for example)
        # In a real implementation, this would be a more complex tree traversal
        result = await self._process_hierarchy_node(workflow_id, "root", hierarchy, input_data)
        
        # Finalize workflow
        workflow["status"] = "completed"
        workflow["completed_at"] = time.time()
        workflow["result"] = result
        
        return result
    
    async def _process_hierarchy_node(self, workflow_id: str, node_id: str,
                                    hierarchy: Dict[str, Any],
                                    input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a node in the hierarchy.
        
        Args:
            workflow_id: ID of the workflow
            node_id: ID of the hierarchy node
            hierarchy: Hierarchy definition
            input_data: Input data for this node
            
        Returns:
            Result from processing this node
        """
        node = hierarchy.get(node_id, {})
        agent_id = node.get("agent_id")
        children = node.get("children", [])
        
        # If this node has an agent, process with that agent
        if agent_id and agent_id in self.managed_agents:
            # Prepare message for the agent
            message = Message.create(
                sender=self.id,
                recipients=[agent_id],
                content={
                    "workflow_id": workflow_id,
                    "node_id": node_id,
                    "data": input_data
                }
            )
            
            # Send message to the agent
            await self._synaptic_bus.send(message)
            
            # Wait for response
            response_message = await self._wait_for_response(agent_id, message.id)
            node_result = response_message.content
        else:
            # No agent for this node, pass through the input
            node_result = input_data
        
        # If this node has children, process them
        if children:
            child_results = {}
            for child_id in children:
                child_result = await self._process_hierarchy_node(
                    workflow_id, child_id, hierarchy, node_result
                )
                child_results[child_id] = child_result
            
            # Aggregate child results (simple aggregation for example)
            return {
                "type": "hierarchical_aggregation",
                "node_id": node_id,
                "results": child_results
            }
        
        # Leaf node, return its result
        return node_result
    
    async def _wait_for_response(self, agent_id: AgentID, message_id: MessageID, 
                               timeout: float = 30.0) -> Message:
        """
        Wait for a response from an agent.
        
        This is a simplified implementation. In a real system, this would
        use a more sophisticated mechanism for waiting for responses.
        
        Args:
            agent_id: ID of the agent to wait for
            message_id: ID of the message we're waiting for a response to
            timeout: Maximum time to wait (seconds)
            
        Returns:
            Response message
            
        Raises:
            TimeoutError: If the response doesn't arrive within the timeout
        """
        # This is a placeholder implementation
        # In a real system, this would need a proper async mechanism
        # For example, registering a callback or using a future
        
        # For this example, we'll just simulate waiting
        await asyncio.sleep(0.1)
        
        # Simulate a response
        response = Message.create(
            sender=agent_id,
            recipients=[self.id],
            content={"status": "success", "data": {"result": f"Simulated response from {agent_id}"}},
            metadata={"in_response_to": message_id}
        )
        
        return response
    
    @capability(
        name="coordination",
        description="Coordinate multiple agents to solve complex tasks",
        input_schema={"type": "object"},
        output_schema={"type": "object"}
    )
    async def process_message(self, message: Message) -> None:
        """
        Process a message by coordinating multiple agents.
        
        This implementation handles several types of coordination requests:
        1. Start a new workflow
        2. Update an existing workflow
        3. Query workflow status
        4. Direct coordination commands
        
        Args:
            message: The message to process
        """
        # Skip processing messages from self
        if message.sender == self.id:
            return
        
        # Parse the message content
        if not isinstance(message.content, dict):
            # Respond with error for non-dict content
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": "Invalid message format. Expected dictionary."
                },
                metadata={"in_response_to": message.id}
            )
            return
        
        content = message.content
        
        # Handle different message types
        if "command" in content:
            # Process a coordination command
            await self._process_command(message)
        elif "workflow_start" in content:
            # Start a new workflow
            await self._handle_workflow_start(message)
        elif "workflow_query" in content:
            # Query workflow status
            await self._handle_workflow_query(message)
        elif "workflow_update" in content:
            # Update an existing workflow
            await self._handle_workflow_update(message)
        else:
            # Generic message, treat as a task
            await self._handle_generic_task(message)
    
    async def _process_command(self, message: Message) -> None:
        """
        Process a coordination command.
        
        Args:
            message: The command message
        """
        content = message.content
        command = content["command"]
        
        if command == "add_agent":
            # Add an agent to management
            agent_id = content.get("agent_id")
            if agent_id:
                self.add_managed_agent(agent_id)
                await self.send_message(
                    recipients=message.sender,
                    content={
                        "status": "success",
                        "message": f"Agent {agent_id} added to coordination"
                    },
                    metadata={"in_response_to": message.id}
                )
            else:
                await self.send_message(
                    recipients=message.sender,
                    content={
                        "status": "error",
                        "error": "Missing agent_id in command"
                    },
                    metadata={"in_response_to": message.id}
                )
        elif command == "remove_agent":
            # Remove an agent from management
            agent_id = content.get("agent_id")
            if agent_id:
                self.remove_managed_agent(agent_id)
                await self.send_message(
                    recipients=message.sender,
                    content={
                        "status": "success",
                        "message": f"Agent {agent_id} removed from coordination"
                    },
                    metadata={"in_response_to": message.id}
                )
            else:
                await self.send_message(
                    recipients=message.sender,
                    content={
                        "status": "error",
                        "error": "Missing agent_id in command"
                    },
                    metadata={"in_response_to": message.id}
                )
        elif command == "list_agents":
            # List managed agents
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "success",
                    "agents": self.managed_agents
                },
                metadata={"in_response_to": message.id}
            )
        elif command == "list_workflows":
            # List active workflows
            workflow_summaries = {}
            for wf_id, workflow in self.active_workflows.items():
                workflow_summaries[wf_id] = {
                    "type": workflow["type"],
                    "status": workflow["status"],
                    "started_at": workflow["started_at"],
                    "steps_completed": workflow["steps_completed"]
                }
            
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "success",
                    "workflows": workflow_summaries
                },
                metadata={"in_response_to": message.id}
            )
        else:
            # Unknown command
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": f"Unknown command: {command}"
                },
                metadata={"in_response_to": message.id}
            )
    
    async def _handle_workflow_start(self, message: Message) -> None:
        """
        Handle a request to start a new workflow.
        
        Args:
            message: The workflow start request message
        """
        content = message.content
        workflow_data = content.get("workflow_start", {})
        
        workflow_id = workflow_data.get("id") or str(uuid.uuid4())
        workflow_type = workflow_data.get("type", "sequential")
        
        try:
            # Start the workflow
            self.start_workflow(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                workflow_data=workflow_data
            )
            
            # Execute the workflow
            if workflow_type in self.coordination_strategies:
                strategy = self.coordination_strategies[workflow_type]
                result = await strategy(workflow_id)
                
                # Send workflow result
                await self.send_message(
                    recipients=message.sender,
                    content={
                        "status": "success",
                        "workflow_id": workflow_id,
                        "result": result
                    },
                    metadata={"in_response_to": message.id}
                )
            else:
                await self.send_message(
                    recipients=message.sender,
                    content={
                        "status": "error",
                        "error": f"Unknown workflow type: {workflow_type}"
                    },
                    metadata={"in_response_to": message.id}
                )
        except Exception as e:
            # Send error response
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": f"Workflow execution failed: {str(e)}"
                },
                metadata={"in_response_to": message.id}
            )
    
    async def _handle_workflow_query(self, message: Message) -> None:
        """
        Handle a query about workflow status.
        
        Args:
            message: The workflow query message
        """
        content = message.content
        workflow_id = content.get("workflow_query")
        
        if not workflow_id:
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": "Missing workflow ID in query"
                },
                metadata={"in_response_to": message.id}
            )
            return
        
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "success",
                    "workflow": {
                        "id": workflow_id,
                        "type": workflow["type"],
                        "status": workflow["status"],
                        "started_at": workflow["started_at"],
                        "steps_completed": workflow["steps_completed"],
                        "result": workflow.get("result")
                    }
                },
                metadata={"in_response_to": message.id}
            )
        else:
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": f"Workflow {workflow_id} not found"
                },
                metadata={"in_response_to": message.id}
            )
    
    async def _handle_workflow_update(self, message: Message) -> None:
        """
        Handle an update to an existing workflow.
        
        Args:
            message: The workflow update message
        """
        content = message.content
        update_data = content.get("workflow_update", {})
        
        workflow_id = update_data.get("id")
        if not workflow_id:
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": "Missing workflow ID in update"
                },
                metadata={"in_response_to": message.id}
            )
            return
        
        if workflow_id not in self.active_workflows:
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "error": f"Workflow {workflow_id} not found"
                },
                metadata={"in_response_to": message.id}
            )
            return
        
        # Update workflow data
        workflow = self.active_workflows[workflow_id]
        
        for key, value in update_data.items():
            if key != "id" and key in workflow:
                workflow[key] = value
        
        await self.send_message(
            recipients=message.sender,
            content={
                "status": "success",
                "message": f"Workflow {workflow_id} updated"
            },
            metadata={"in_response_to": message.id}
        )
    
    async def _handle_generic_task(self, message: Message) -> None:
        """
        Handle a generic task by distributing it to managed agents.
        
        This is a simplified implementation that uses a sequential strategy.
        
        Args:
            message: The task message
        """
        # Create a task ID
        task_id = str(uuid.uuid4())
        
        # Register the task
        self.register_task(task_id, {
            "sender": message.sender,
            "content": message.content,
            "original_message_id": message.id
        })
        
        # Start a sequential workflow for this task
        workflow_id = f"task-{task_id}"
        try:
            self.start_workflow(
                workflow_id=workflow_id,
                workflow_type="sequential",
                workflow_data={
                    "input_data": message.content,
                    "sequence": self.managed_agents
                }
            )
            
            # Execute the workflow
            result = await self._sequential_coordination(workflow_id)
            
            # Update task status
            self.update_task_status(task_id, "completed", result)
            
            # Send task result
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "success",
                    "task_id": task_id,
                    "result": result
                },
                metadata={"in_response_to": message.id}
            )
        except Exception as e:
            # Update task status
            self.update_task_status(task_id, "failed", {"error": str(e)})
            
            # Send error response
            await self.send_message(
                recipients=message.sender,
                content={
                    "status": "error",
                    "task_id": task_id,
                    "error": f"Task execution failed: {str(e)}"
                },
                metadata={"in_response_to": message.id}
            )


class AgentBuilder:
    """
    Factory for creating and configuring agents.
    
    The AgentBuilder provides a fluent interface for creating and configuring
    agents, making it easier to construct complex agent configurations.
    """
    
    def __init__(self, agent_manager: AgentManager):
        """
        Initialize the agent builder.
        
        Args:
            agent_manager: AgentManager to use for creating agents
        """
        self._agent_manager = agent_manager
        self._agent_type = None
        self._agent_id = None
        self._name = ""
        self._description = ""
        self._metadata = {}
        self._config_params = {}
    
    def of_type(self, agent_type: Union[str, Type[BaseAgent]]) -> 'AgentBuilder':
        """
        Set the type of agent to build.
        
        Args:
            agent_type: Type of agent (class or name)
            
        Returns:
            This builder instance for method chaining
            
        Raises:
            ValueError: If the agent type is not registered
        """
        if isinstance(agent_type, str):
            # Look up the agent type by name
            resolved_type = self._agent_manager.get_agent_type(agent_type)
            if not resolved_type:
                raise ValueError(f"Agent type {agent_type} is not registered")
            self._agent_type = resolved_type
        else:
            # Use the provided class directly
            self._agent_type = agent_type
        
        return self
    
    def with_id(self, agent_id: Optional[AgentID] = None) -> 'AgentBuilder':
        """
        Set the agent ID.
        
        Args:
            agent_id: ID for the agent (generated if None)
            
        Returns:
            This builder instance for method chaining
        """
        self._agent_id = agent_id
        return self
    
    def with_name(self, name: str) -> 'AgentBuilder':
        """
        Set the agent name.
        
        Args:
            name: Name for the agent
            
        Returns:
            This builder instance for method chaining
        """
        self._name = name
        return self
    
    def with_description(self, description: str) -> 'AgentBuilder':
        """
        Set the agent description.
        
        Args:
            description: Description for the agent
            
        Returns:
            This builder instance for method chaining
        """
        self._description = description
        return self
    
    def with_metadata(self, metadata: Dict[str, Any]) -> 'AgentBuilder':
        """
        Set the agent metadata.
        
        Args:
            metadata: Metadata for the agent
            
        Returns:
            This builder instance for method chaining
        """
        self._metadata = metadata
        return self
    
    def with_config(self, **config_params) -> 'AgentBuilder':
        """
        Set configuration parameters for the agent.
        
        Args:
            **config_params: Configuration parameters
            
        Returns:
            This builder instance for method chaining
        """
        self._config_params.update(config_params)
        return self
    
    def build(self) -> AgentID:
        """
        Build and create the agent.
        
        Returns:
            ID of the created agent
            
        Raises:
            ValueError: If no agent type has been set
            AgentInitializationError: If agent creation fails
        """
        if not self._agent_type:
            raise ValueError("Agent type must be set before building")
        
        config = AgentConfig(
            agent_type=self._agent_type,
            agent_id=self._agent_id,
            name=self._name,
            description=self._description,
            metadata=self._metadata,
            config_params=self._config_params
        )
        
        return self._agent_manager.create_agent(config)
    
    def build_and_start(self) -> AgentID:
        """
        Build and start the agent.
        
        Returns:
            ID of the created and started agent
            
        Raises:
            ValueError: If no agent type has been set
            AgentInitializationError: If agent creation fails
        """
        agent_id = self.build()
        self._agent_manager.start_agent(agent_id)
        return agent_id
"""
