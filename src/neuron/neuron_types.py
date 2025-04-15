"""
neuron_types.py - Core Type Definitions for Neuron Framework

This module contains all the fundamental type definitions, enums, and data classes 
that are used throughout the Neuron framework. These types provide the foundation
for the entire framework's type system, enabling strong typing and better code organization.

The design is inspired by how the brain categorizes and processes different types of information,
with specialized structures for different purposes.
"""

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union

# Type variables for generic programming
T = TypeVar('T')

# Core identifiers
AgentID = str          # Unique identifier for an agent
MessageID = str        # Unique identifier for a message
CircuitID = str        # Unique identifier for a circuit of agents
SignalID = str         # Unique identifier for a signal in the SynapticBus
MemoryID = str         # Unique identifier for a memory entry


class MessagePriority(Enum):
    """
    Defines priority levels for messages in the SynapticBus.
    
    Inspired by the varying priorities of signals in the brain, where
    certain neural pathways have priority over others (e.g., pain signals
    are processed with higher priority than background sensory information).
    
    This allows the framework to prioritize critical messages in high-load scenarios.
    """
    LOW = auto()        # Background/non-urgent information
    NORMAL = auto()     # Standard priority for most messages
    HIGH = auto()       # Important messages that should be processed quickly
    URGENT = auto()     # Critical messages that require immediate attention


class AgentState(Enum):
    """
    Defines the possible states of an Agent.
    
    This mirrors the concept of neuronal states, where neurons can be
    at rest, active, or in a refractory period. The state machine for
    agents follows a similar conceptual model to track an agent's
    processing lifecycle.
    
    These states are used for lifecycle management and monitoring.
    """
    INITIALIZING = auto()  # Agent is being set up with initial configuration
    READY = auto()         # Agent is ready to receive and process messages
    PROCESSING = auto()    # Agent is actively processing one or more messages
    PAUSED = auto()        # Agent is temporarily suspended from processing
    TERMINATED = auto()    # Agent has been shut down and can no longer process


class MemoryType(Enum):
    """
    Defines different types of memory in the Neuron framework.
    
    Inspired by human memory systems:
    - Working memory: temporary, limited capacity storage (like a buffer)
    - Episodic memory: records of experiences and events
    - Semantic memory: factual knowledge, concepts, and relationships
    - Procedural memory: skills and how to perform tasks
    - Emotional memory: affective associations and responses
    
    This allows agents to organize information in a way similar to human memory,
    with different access patterns and retention policies.
    """
    WORKING = auto()      # Short-term, limited capacity, actively maintained
    EPISODIC = auto()     # Event-based memories tied to specific contexts
    SEMANTIC = auto()     # Factual, conceptual knowledge independent of context
    PROCEDURAL = auto()   # Skills, methods, and processes
    EMOTIONAL = auto()    # Affective states associated with concepts/experiences


class CircuitRole(Enum):
    """
    Defines the possible roles an agent can play within a circuit.
    
    Inspired by specialized regions in the brain that perform specific functions
    as part of larger neural circuits. These roles help in designing circuits
    with clear responsibilities for each agent.
    """
    INPUT = auto()         # Agents that receive external input
    PROCESSOR = auto()     # Agents that transform or process information
    COORDINATOR = auto()   # Agents that direct flow and orchestrate other agents
    MEMORY = auto()        # Agents that store and retrieve information
    OUTPUT = auto()        # Agents that produce final outputs
    MONITOR = auto()       # Agents that observe and report on circuit behavior


@dataclass
class Message:
    """
    Basic unit of communication between agents.
    
    A Message in Neuron is analogous to an action potential in biological neurons.
    It carries information along a defined pathway from one agent to another.
    
    Messages contain not just content but metadata about the communication,
    enabling rich analysis of information flow through the system.
    """
    id: MessageID                      # Unique identifier for this message
    sender: AgentID                    # ID of the agent sending the message
    recipients: List[AgentID]          # IDs of agents receiving the message
    content: Any                       # The payload/content of the message
    priority: MessagePriority = MessagePriority.NORMAL  # Priority level
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context
    created_at: float = field(default_factory=time.time)    # Creation timestamp
    trace_id: Optional[str] = None     # Optional ID for tracing message chains
    
    @classmethod
    def create(cls, sender: AgentID, recipients: List[AgentID], content: Any, 
               priority: MessagePriority = MessagePriority.NORMAL,
               metadata: Optional[Dict[str, Any]] = None,
               trace_id: Optional[str] = None) -> 'Message':
        """Factory method to create a new message with a unique ID."""
        return cls(
            id=str(uuid.uuid4()),
            sender=sender,
            recipients=recipients,
            content=content,
            priority=priority,
            metadata=metadata or {},
            trace_id=trace_id or str(uuid.uuid4())
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the message to a dictionary representation for serialization."""
        result = asdict(self)
        # Convert enums to strings for clean serialization
        result['priority'] = self.priority.name
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a message from a dictionary representation (deserialization)."""
        # Convert string back to enum
        data = data.copy()  # Avoid modifying the input
        if 'priority' in data and isinstance(data['priority'], str):
            data['priority'] = MessagePriority[data['priority']]
        return cls(**data)


@dataclass
class AgentCapability:
    """
    Defines a specific capability that an agent possesses.
    
    Similar to how different brain regions have specialized functions,
    AgentCapability defines what an agent can do, including the inputs it accepts
    and outputs it can produce.
    
    This enables discovery and composition of agents based on their abilities.
    """
    name: str                          # Name of the capability
    description: str                   # Human-readable description
    input_schema: Optional[Dict] = None  # Schema of expected inputs
    output_schema: Optional[Dict] = None  # Schema of produced outputs
    parameters: Dict[str, Any] = field(default_factory=dict)  # Configuration parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert capability to a dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentCapability':
        """Create a capability from a dictionary representation."""
        return cls(**data)


@dataclass
class AgentMetrics:
    """
    Stores metrics about an agent's performance and resource usage.
    
    Similar to how neuroscientists measure neural activity to understand
    brain function, AgentMetrics gives us insights into agent behavior.
    
    These metrics are essential for monitoring, debugging, and optimizing
    agent networks.
    """
    # Performance metrics
    message_count: int = 0              # Total messages processed
    processing_time: float = 0          # Total time spent processing messages
    error_count: int = 0                # Count of errors encountered
    
    # Resource usage
    memory_usage: float = 0             # Estimated memory usage
    cpu_usage: float = 0                # Estimated CPU usage
    
    # Operational metrics
    last_active: Optional[float] = None  # Timestamp of last activity
    uptime: float = 0                    # Total time agent has been running
    
    # Custom metrics for specialized agents
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_processing_time(self, time_delta: float) -> None:
        """Update the total processing time."""
        self.processing_time += time_delta
        self.last_active = time.time()
    
    def increment_message_count(self) -> None:
        """Increment the message count."""
        self.message_count += 1
        self.last_active = time.time()
    
    def increment_error_count(self) -> None:
        """Increment the error count."""
        self.error_count += 1
    
    def update_custom_metric(self, key: str, value: Any) -> None:
        """Update a custom metric."""
        self.custom_metrics[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a dictionary representation."""
        return asdict(self)


@dataclass
class MemoryEntry:
    """
    Represents an entry in an agent's memory.
    
    Like a memory trace in the brain, MemoryEntry stores information
    with associated metadata about importance, recency, etc.
    
    The design allows for intelligent memory management, including
    prioritization of important memories and forgetting of less
    relevant information.
    """
    id: MemoryID                        # Unique identifier for this memory
    content: Any                        # The stored information
    memory_type: MemoryType             # Type of memory (working, episodic, etc.)
    created_at: float                   # Creation timestamp
    last_accessed: float                # Last access timestamp
    access_count: int = 0               # Number of times accessed
    importance: float = 0.5             # Importance score (0.0 to 1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context
    
    @classmethod
    def create(cls, content: Any, memory_type: MemoryType, 
               importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> 'MemoryEntry':
        """Factory method to create a new memory entry with a unique ID."""
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            created_at=now,
            last_accessed=now,
            importance=importance,
            metadata=metadata or {}
        )
    
    def access(self) -> None:
        """Record an access to this memory, updating relevant metadata."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def update_importance(self, new_importance: float) -> None:
        """Update the importance score of this memory."""
        self.importance = max(0.0, min(1.0, new_importance))  # Clamp to [0,1]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory entry to a dictionary representation."""
        result = asdict(self)
        # Convert enums to strings for clean serialization
        result['memory_type'] = self.memory_type.name
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create a memory entry from a dictionary representation."""
        # Convert string back to enum
        data = data.copy()  # Avoid modifying the input
        if 'memory_type' in data and isinstance(data['memory_type'], str):
            data['memory_type'] = MemoryType[data['memory_type']]
        return cls(**data)


@dataclass
class CircuitDefinition:
    """
    Defines a circuit of connected agents.
    
    Inspired by neural circuits in the brain, a CircuitDefinition describes
    how agents are connected and how information flows between them.
    
    This enables the creation of complex agent networks with well-defined
    information pathways.
    """
    id: CircuitID                       # Unique identifier for this circuit
    name: str                           # Human-readable name
    description: str                    # Detailed description of purpose and function
    agents: Dict[AgentID, Dict[str, Any]]  # Agent configurations with roles and settings
    connections: List[Dict[str, Any]]   # Connection definitions between agents
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional circuit metadata
    
    @classmethod
    def create(cls, name: str, description: str, 
               agents: Dict[AgentID, Dict[str, Any]],
               connections: List[Dict[str, Any]],
               metadata: Optional[Dict[str, Any]] = None) -> 'CircuitDefinition':
        """Factory method to create a new circuit definition with a unique ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            agents=agents,
            connections=connections,
            metadata=metadata or {}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert circuit definition to a dictionary representation."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CircuitDefinition':
        """Create a circuit definition from a dictionary representation."""
        return cls(**data)

