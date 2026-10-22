"""
circuit_designer.py - Agent Network Composition for Neuron Framework

This module implements the circuit design and management functionality for the 
Neuron framework. A circuit is a network of interconnected agents designed to 
solve specific problems or perform specific functions.

The circuit designer provides tools for creating, validating, deploying, and 
managing agent circuits, enabling complex agent compositions that work together 
in a coordinated fashion.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from .agent import AgentBuilder, BaseAgent, CoordinatorAgent
from .config import config
from .exceptions import CircuitDesignerError, CircuitRuntimeError, ValidationError
from .neuron_types import AgentID, CircuitDefinition, CircuitID, CircuitRole, Message

logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    """
    Types of connections between agents in a circuit.
    
    This defines the communication pattern between connected agents,
    determining how information flows through the circuit.
    """
    DIRECT = "direct"        # Direct point-to-point connection
    FILTERED = "filtered"    # Connection with filtered message passing
    TRANSFORMED = "transformed"  # Connection with message transformation
    CONDITIONAL = "conditional"  # Connection that activates under specific conditions
    WEIGHTED = "weighted"    # Connection with a strength/weight factor


@dataclass
class Connection:
    """
    Represents a connection between agents in a circuit.
    
    A connection defines how information flows from a source agent to a
    target agent, including any transformations or conditions on the flow.
    """
    source: AgentID              # ID of the source agent
    target: AgentID              # ID of the target agent
    connection_type: ConnectionType  # Type of connection
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional configuration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "source": self.source,
            "target": self.target,
            "connection_type": self.connection_type.value,
            "metadata": self.metadata
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Connection':
        """Create from dictionary representation."""
        return cls(
            source=data["source"],
            target=data["target"],
            connection_type=ConnectionType(data["connection_type"]),
            metadata=data.get("metadata", {})
        )


class CircuitValidator:
    """
    Validates circuit designs before deployment.
    
    The CircuitValidator checks for structural integrity, agent compatibility,
    and potential issues in a circuit design before it is deployed.
    """
    
    @staticmethod
    def validate_circuit(circuit_def: CircuitDefinition, 
                       available_agents: Dict[str, Type[BaseAgent]]) -> List[str]:
        """
        Validate a circuit definition.
        
        Args:
            circuit_def: Circuit definition to validate
            available_agents: Dictionary of available agent types
            
        Returns:
            List of validation errors, or empty list if valid
        """
        errors = []
        
        # Check for basic structural requirements
        if not circuit_def.name:
            errors.append("Circuit must have a name")
        
        if not circuit_def.agents:
            errors.append("Circuit must have at least one agent")
        
        # Check agent configurations
        agent_ids = set()
        for agent_id, agent_config in circuit_def.agents.items():
            # Check for duplicate IDs
            if agent_id in agent_ids:
                errors.append(f"Duplicate agent ID: {agent_id}")
            agent_ids.add(agent_id)
            
            # Check agent type
            agent_type = agent_config.get("type")
            if not agent_type:
                errors.append(f"Agent {agent_id} has no type specified")
            elif agent_type not in available_agents:
                errors.append(f"Unknown agent type for {agent_id}: {agent_type}")
            
            # Check role
            role = agent_config.get("role")
            if role and role not in [r.name for r in CircuitRole]:
                errors.append(f"Invalid role for {agent_id}: {role}")
        
        # Check connections
        for connection in circuit_def.connections:
            source = connection.get("source")
            target = connection.get("target")
            
            # Check that source and target exist
            if not source:
                errors.append("Connection missing source")
            elif source not in agent_ids:
                errors.append(f"Connection source does not exist: {source}")
            
            if not target:
                errors.append("Connection missing target")
            elif target not in agent_ids:
                errors.append(f"Connection target does not exist: {target}")
            
            # Check connection type
            conn_type = connection.get("connection_type")
            if not conn_type:
                errors.append("Connection missing type")
            elif conn_type not in [ct.value for ct in ConnectionType]:
                errors.append(f"Invalid connection type: {conn_type}")
        
        # Check for input and output agents
        has_input = False
        has_output = False
        for agent_config in circuit_def.agents.values():
            role = agent_config.get("role")
            if role == CircuitRole.INPUT.name:
                has_input = True
            elif role == CircuitRole.OUTPUT.name:
                has_output = True
        
        if not has_input:
            errors.append("Circuit has no input agent")
        
        if not has_output:
            errors.append("Circuit has no output agent")
        
        # Check for connectivity
        if circuit_def.connections and agent_ids:
            # Build an undirected adjacency list: an agent counts as connected
            # whether messages flow into it or out of it. (Following only
            # outgoing edges made the result depend on which agent the
            # search happened to start from.)
            adjacency = {agent_id: [] for agent_id in agent_ids}
            for connection in circuit_def.connections:
                source = connection.get("source")
                target = connection.get("target")
                if source in adjacency and target in adjacency:
                    adjacency[source].append(target)
                    adjacency[target].append(source)

            # Check if the graph is connected
            visited = set()
            stack = [next(iter(agent_ids))]
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(adjacency[node])
            
            if len(visited) < len(agent_ids):
                errors.append("Circuit has disconnected agents")
        
        return errors


class Circuit:
    """
    Runtime representation of an agent circuit.
    
    A Circuit is a network of agents that work together to perform a task.
    This class manages the runtime behavior of a circuit, including agent
    creation, communication setup, and circuit lifecycle.
    """
    
    def __init__(self, circuit_id: CircuitID, definition: CircuitDefinition, 
                agent_manager: Any, synaptic_bus: Any):
        """
        Initialize a circuit.
        
        Args:
            circuit_id: Unique identifier for this circuit
            definition: Definition of the circuit structure
            agent_manager: AgentManager for creating and managing agents
            synaptic_bus: SynapticBus for agent communication
        """
        self.id = circuit_id
        self.definition = definition
        self._agent_manager = agent_manager
        self._synaptic_bus = synaptic_bus
        
        self._agents = {}  # agent_id -> AgentID (actual)
        self._connections = []  # List of established Connection objects
        self._status = "initialized"
        self._lock = threading.RLock()
        self._coordinator_id = None  # ID of the coordinator agent (if any)
        
        # The circuit sends every message to its agents and receives every
        # reply under this ID, then forwards replies along the connections.
        self._hub_id = f"{circuit_id}:hub"
        self._routes = {}  # actual source ID -> [(actual target ID, predicate, transform)]
        self._outputs = None  # asyncio.Queue of replies from OUTPUT agents
        
        logger.info(f"Initialized circuit: {definition.name} ({circuit_id})")
    
    async def deploy(self) -> None:
        """
        Deploy the circuit by creating and connecting agents.
        
        This creates all agents in the circuit and establishes the
        defined connections between them.
        
        Raises:
            CircuitRuntimeError: If deployment fails
        """
        with self._lock:
            if self._status != "initialized":
                raise CircuitRuntimeError(f"Circuit {self.id} is already deployed")
            
            self._status = "deploying"
            logger.info(f"Deploying circuit: {self.definition.name} ({self.id})")
            
            try:
                # Create agents
                await self._create_agents()
                
                # Create connections
                await self._create_connections()
                
                # Start agents
                await self._start_agents()
                
                # Receive agent replies so they can be routed
                self._outputs = asyncio.Queue()
                self._synaptic_bus.register_agent_nowait(self._hub_id, self._on_agent_message)
                
                self._status = "deployed"
                logger.info(f"Circuit {self.definition.name} ({self.id}) deployed successfully")
            except Exception as e:
                self._status = "deployment_failed"
                logger.error(f"Error deploying circuit {self.id}: {e}")
                raise CircuitRuntimeError(f"Failed to deploy circuit: {e}") from e
    
    async def _create_agents(self) -> None:
        """
        Create all agents in the circuit.
        
        This uses the AgentManager to create instances of the agents
        defined in the circuit.
        
        Raises:
            CircuitRuntimeError: If agent creation fails
        """
        builder = AgentBuilder(self._agent_manager)
        
        # First, check if we need a coordinator agent
        needs_coordinator = self.definition.metadata.get("needs_coordinator", True)
        
        if needs_coordinator:
            # Create coordinator agent
            coordinator_id = await self._create_coordinator_agent(builder)
            self._coordinator_id = coordinator_id
        
        # Create all other agents
        for agent_id, agent_config in self.definition.agents.items():
            # Skip if this agent already exists
            if agent_id in self._agents:
                continue
            
            agent_type = agent_config["type"]
            agent_class = self._agent_manager.get_agent_type(agent_type)
            
            if not agent_class:
                raise CircuitRuntimeError(f"Unknown agent type: {agent_type}")
            
            # Build agent configuration
            name = agent_config.get("name", f"{agent_type}_{agent_id}")
            description = agent_config.get("description", "")
            
            metadata = {
                **agent_config.get("metadata", {}),
                "circuit_id": self.id,
                "circuit_role": agent_config.get("role", "PROCESSOR")
            }
            
            # Create the agent
            actual_id = (builder
                       .of_type(agent_class)
                       .with_id(agent_id)
                       .with_name(name)
                       .with_description(description)
                       .with_metadata(metadata)
                       .with_config(**agent_config.get("config", {}))
                       .build())
            
            # Store mapping
            self._agents[agent_id] = actual_id
            
            # If this is a coordinator, store its ID
            if agent_config.get("role") == CircuitRole.COORDINATOR.name:
                self._coordinator_id = actual_id
            
            logger.debug(f"Created agent {name} ({actual_id}) for circuit {self.id}")
    
    async def _create_coordinator_agent(self, builder: AgentBuilder) -> AgentID:
        """
        Create a coordinator agent for the circuit.
        
        Args:
            builder: AgentBuilder to use for agent creation
            
        Returns:
            ID of the created coordinator agent
            
        Raises:
            CircuitRuntimeError: If coordinator creation fails
        """
        # Check if a coordinator is already defined in the circuit
        for agent_id, agent_config in self.definition.agents.items():
            if agent_config.get("role") == CircuitRole.COORDINATOR.name:
                return agent_id
        
        # Create a new coordinator agent
        coordinator_id = f"{self.id}_coordinator"
        
        # Build coordinator configuration
        name = f"Coordinator for {self.definition.name}"
        description = f"Coordinates agents in circuit {self.definition.name}"
        
        metadata = {
            "circuit_id": self.id,
            "circuit_role": CircuitRole.COORDINATOR.name
        }
        
        # Create the coordinator
        actual_id = (builder
                   .of_type(CoordinatorAgent)
                   .with_id(coordinator_id)
                   .with_name(name)
                   .with_description(description)
                   .with_metadata(metadata)
                   .build())
        
        # Store mapping
        self._agents[coordinator_id] = actual_id
        
        logger.debug(f"Created coordinator agent ({actual_id}) for circuit {self.id}")
        
        return actual_id
    
    async def _create_connections(self) -> None:
        """
        Create connections between agents in the circuit.
        
        This sets up the communication pathways between agents according
        to the circuit definition.
        """
        # Create a channel for circuit-wide communication
        circuit_channel = f"circuit_{self.id}"
        await self._synaptic_bus.create_channel(circuit_channel)
        
        # Subscribe the coordinator agent to the circuit channel
        if self._coordinator_id:
            await self._synaptic_bus.subscribe_to_channel(
                self._coordinator_id, circuit_channel
            )
        
        # Process each connection in the definition
        for conn_def in self.definition.connections:
            source_id = conn_def.get("source")
            target_id = conn_def.get("target")
            conn_type = ConnectionType(conn_def.get("connection_type"))
            metadata = conn_def.get("metadata", {})
            
            # Get actual agent IDs
            actual_source = self._agents.get(source_id)
            actual_target = self._agents.get(target_id)
            
            if not actual_source or not actual_target:
                logger.warning(f"Skipping connection due to missing agent: {source_id} -> {target_id}")
                continue
            
            # Work out how messages travel along this connection. Conditions and
            # transforms are Python expressions over `message`, evaluated with
            # eval(), so only deploy circuit definitions you trust.
            predicate = None
            transform = None
            if conn_type in (ConnectionType.FILTERED, ConnectionType.CONDITIONAL):
                key = "filter_condition" if conn_type == ConnectionType.FILTERED else "condition_code"
                if metadata.get(key):
                    predicate = self._compile_expression(metadata[key], source_id, target_id)
            elif conn_type == ConnectionType.TRANSFORMED:
                if metadata.get("transform_code"):
                    transform = self._compile_expression(metadata["transform_code"], source_id, target_id)
            # DIRECT and WEIGHTED connections forward every message unchanged.
            
            self._routes.setdefault(actual_source, []).append((actual_target, predicate, transform))
            
            # Record the connection
            connection = Connection(
                source=actual_source,
                target=actual_target,
                connection_type=conn_type,
                metadata=metadata
            )
            self._connections.append(connection)
            
            logger.debug(f"Created connection {actual_source} -> {actual_target} for circuit {self.id}")
    
    async def _start_agents(self) -> None:
        """
        Start all agents in the circuit.
        
        This initiates the processing of messages by each agent in the circuit.
        """
        # Start agents in dependency order
        # First, start the coordinator
        if self._coordinator_id:
            self._agent_manager.start_agent(self._coordinator_id)
        
        # Then start input agents
        for agent_id, agent_config in self.definition.agents.items():
            if agent_config.get("role") == CircuitRole.INPUT.name:
                actual_id = self._agents.get(agent_id)
                if actual_id:
                    self._agent_manager.start_agent(actual_id)
        
        # Then start processor agents
        for agent_id, agent_config in self.definition.agents.items():
            if agent_config.get("role") in (CircuitRole.PROCESSOR.name, CircuitRole.MEMORY.name):
                actual_id = self._agents.get(agent_id)
                if actual_id:
                    self._agent_manager.start_agent(actual_id)
        
        # Finally start output agents
        for agent_id, agent_config in self.definition.agents.items():
            if agent_config.get("role") == CircuitRole.OUTPUT.name:
                actual_id = self._agents.get(agent_id)
                if actual_id:
                    self._agent_manager.start_agent(actual_id)
        
        logger.debug(f"Started all agents for circuit {self.id}")
    
    @staticmethod
    def _compile_expression(expression: str, source_id: str, target_id: str) -> Callable[[Message], Any]:
        try:
            return eval(f"lambda message: {expression}")
        except SyntaxError as e:
            raise CircuitRuntimeError(
                f"Invalid expression on connection {source_id} -> {target_id}: {expression!r}"
            ) from e
    
    async def _on_agent_message(self, message: Message) -> None:
        """
        Route a reply from one of the circuit's agents.
        
        The reply is forwarded to every agent the sender connects to (subject
        to each connection's condition or transform). Replies from OUTPUT
        agents, and from agents with no outgoing connections, become circuit
        output that get_output() returns.
        """
        sender_name = self._agent_name(message.sender)
        routes = self._routes.get(message.sender, [])
        
        for target, predicate, transform in routes:
            try:
                if predicate is not None and not predicate(message):
                    continue
                content = transform(message) if transform is not None else message.content
            except Exception as e:
                logger.error(f"Connection {sender_name} -> {self._agent_name(target)} failed: {e}")
                continue
            
            await self._synaptic_bus.send(Message.create(
                sender=self._hub_id,
                recipients=[target],
                content=content,
                metadata={**message.metadata, "circuit_id": self.id, "from_agent": sender_name},
                trace_id=message.trace_id,
            ))
        
        role = self.definition.agents.get(sender_name, {}).get("role")
        if not routes or role == CircuitRole.OUTPUT.name:
            await self._outputs.put({
                "agent": sender_name,
                "content": message.content,
                "trace_id": message.trace_id,
            })
    
    def _agent_name(self, actual_id: AgentID) -> str:
        """Map an actual agent ID back to its name in the circuit definition."""
        for name, agent_id in self._agents.items():
            if agent_id == actual_id:
                return name
        return actual_id
    
    async def get_output(self, timeout: Optional[float] = 5.0) -> Dict[str, Any]:
        """
        Wait for the next output the circuit produces.
        
        Returns:
            {"agent": name of the agent that produced it, "content": ..., "trace_id": ...}
            
        Raises:
            CircuitRuntimeError: If the circuit is not deployed
            asyncio.TimeoutError: If no output arrives within `timeout` seconds
        """
        if self._outputs is None:
            raise CircuitRuntimeError(f"Circuit {self.id} is not deployed")
        return await asyncio.wait_for(self._outputs.get(), timeout)
    
    async def send_input(self, input_data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Send input to the circuit.
        
        This sends the provided data to all input agents in the circuit.
        
        Args:
            input_data: Data to send as input
            metadata: Additional metadata for the input
            
        Raises:
            CircuitRuntimeError: If the circuit is not deployed or has no input agents
        """
        if self._status != "deployed":
            raise CircuitRuntimeError(f"Circuit {self.id} is not deployed")
        
        # Find input agents
        input_agents = []
        for agent_id, agent_config in self.definition.agents.items():
            if agent_config.get("role") == CircuitRole.INPUT.name:
                actual_id = self._agents.get(agent_id)
                if actual_id:
                    input_agents.append(actual_id)
        
        if not input_agents:
            raise CircuitRuntimeError(f"Circuit {self.id} has no input agents")
        
        # Create input message
        message = Message.create(
            sender=self._hub_id,
            recipients=input_agents,
            content=input_data,
            metadata=metadata or {}
        )
        
        # Send to all input agents
        await self._synaptic_bus.send(message)
        
        logger.debug(f"Sent input to circuit {self.id}")
    
    async def pause(self) -> None:
        """
        Pause the circuit.
        
        This stops all agents from processing messages, but maintains
        their state and the circuit structure.
        
        Raises:
            CircuitRuntimeError: If the circuit is not deployed
        """
        with self._lock:
            if self._status != "deployed":
                raise CircuitRuntimeError(f"Circuit {self.id} is not deployed")
            
            self._status = "pausing"
            
            # Pause all agents
            for agent_id in self._agents.values():
                self._agent_manager.stop_agent(agent_id)
            
            self._status = "paused"
            logger.info(f"Paused circuit {self.id}")
    
    async def resume(self) -> None:
        """
        Resume a paused circuit.
        
        This restarts all agents and allows the circuit to continue processing.
        
        Raises:
            CircuitRuntimeError: If the circuit is not paused
        """
        with self._lock:
            if self._status != "paused":
                raise CircuitRuntimeError(f"Circuit {self.id} is not paused")
            
            self._status = "resuming"
            
            # Resume all agents
            await self._start_agents()
            
            self._status = "deployed"
            logger.info(f"Resumed circuit {self.id}")
    
    async def terminate(self) -> None:
        """
        Terminate the circuit.
        
        This stops all agents, removes connections, and cleans up resources.
        After termination, the circuit cannot be restarted.
        """
        with self._lock:
            if self._status in ("terminated", "terminating"):
                return
            
            self._status = "terminating"
            
            # Terminate all agents
            for agent_id in self._agents.values():
                try:
                    self._agent_manager.terminate_agent(agent_id)
                except Exception as e:
                    logger.warning(f"Error terminating agent {agent_id}: {e}")
            
            if self._synaptic_bus.is_registered(self._hub_id):
                self._synaptic_bus.unregister_agent_nowait(self._hub_id)
            
            # Close circuit channel
            try:
                await self._synaptic_bus.remove_channel(f"circuit_{self.id}")
            except Exception as e:
                logger.warning(f"Error removing circuit channel: {e}")
            
            self._agents.clear()
            self._connections.clear()
            self._status = "terminated"
            logger.info(f"Terminated circuit {self.id}")
    
    def get_agent_mapping(self) -> Dict[str, AgentID]:
        """
        Get the mapping from definition agent IDs to actual agent IDs.
        
        Returns:
            Dictionary mapping definition agent IDs to actual agent IDs
        """
        return self._agents.copy()
    
    def get_status(self) -> str:
        """
        Get the current status of the circuit.
        
        Returns:
            String representing the circuit status
        """
        return self._status
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the circuit to a dictionary representation.
        
        Returns:
            Dictionary representation of the circuit
        """
        return {
            "id": self.id,
            "name": self.definition.name,
            "description": self.definition.description,
            "status": self._status,
            "agents": {
                agent_id: {"actual_id": actual_id, **self.definition.agents.get(agent_id, {})}
                for agent_id, actual_id in self._agents.items()
            },
            "connections": [conn.to_dict() for conn in self._connections],
            "metadata": self.definition.metadata
        }


class CircuitTemplate:
    """
    Reusable template for creating circuits.
    
    A CircuitTemplate provides a blueprint for creating circuit instances
    with the same structure but potentially different agent configurations.
    """
    
    def __init__(self, name: str, description: str, template_def: Dict[str, Any]):
        """
        Initialize a circuit template.
        
        Args:
            name: Name of the template
            description: Description of the template
            template_def: Template definition dictionary
        """
        self.name = name
        self.description = description
        self.template_def = template_def
        
        logger.debug(f"Created circuit template: {name}")
    
    def create_definition(self, parameters: Dict[str, Any] = None) -> CircuitDefinition:
        """
        Create a circuit definition from this template.
        
        Args:
            parameters: Parameter values to apply to the template
            
        Returns:
            Circuit definition created from the template
            
        Raises:
            ValidationError: If parameter validation fails
        """
        parameters = parameters or {}
        
        # Start with a copy of the template
        definition = self.template_def.copy()
        
        # Apply parameters
        try:
            # Replace parameter placeholders in the definition
            definition = self._apply_parameters(definition, parameters)
            
            # Create the circuit definition
            circuit_def = CircuitDefinition.create(
                name=definition.get("name", self.name),
                description=definition.get("description", self.description),
                agents=definition.get("agents", {}),
                connections=definition.get("connections", []),
                metadata=definition.get("metadata", {})
            )
            
            return circuit_def
        except Exception as e:
            raise ValidationError(f"Error applying parameters to template: {e}") from e
    
    def _apply_parameters(self, definition: Dict[str, Any], 
                         parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply parameters to a definition.
        
        Args:
            definition: Template definition to apply parameters to
            parameters: Parameter values to apply
            
        Returns:
            Definition with parameters applied
            
        Raises:
            ValidationError: If parameter validation fails
        """
        # This is a simplified implementation
        # A real implementation would use a more sophisticated parameter substitution mechanism
        
        # Convert definition to JSON string
        definition_str = json.dumps(definition)
        
        # Replace parameter placeholders
        for key, value in parameters.items():
            placeholder = f"{{${key}}}"
            # Convert value to JSON string if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value)
            else:
                # Escape quotes in string values
                value = value.replace('"', '\\"')
                value = f'"{value}"'
            
            definition_str = definition_str.replace(placeholder, value)
        
        # Convert back to dictionary
        try:
            result = json.loads(definition_str)
            return result
        except json.JSONDecodeError as e:
            raise ValidationError(f"Error parsing template with parameters: {e}") from e
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the template to a dictionary representation.
        
        Returns:
            Dictionary representation of the template
        """
        return {
            "name": self.name,
            "description": self.description,
            "template_def": self.template_def
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CircuitTemplate':
        """
        Create a template from a dictionary representation.
        
        Args:
            data: Dictionary representation of the template
            
        Returns:
            Created circuit template
        """
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            template_def=data.get("template_def", {})
        )


class CircuitDesigner:
    """
    Creates and manages agent circuits.
    
    The CircuitDesigner provides the interface for creating, validating,
    deploying, and managing agent circuits, allowing users to compose
    agent networks for specific tasks.
    """
    
    def __init__(self):
        """Initialize the circuit designer."""
        self._circuits = {}  # circuit_id -> Circuit
        self._templates = {}  # template_name -> CircuitTemplate
        self._agent_manager = None
        self._synaptic_bus = None
        self._lock = threading.RLock()
        
        logger.info("Initialized CircuitDesigner")
    
    def initialize(self, agent_manager: Any, synaptic_bus: Any) -> None:
        """
        Initialize the circuit designer with dependencies.
        
        Args:
            agent_manager: AgentManager for agent lifecycle management
            synaptic_bus: SynapticBus for agent communication
        """
        self._agent_manager = agent_manager
        self._synaptic_bus = synaptic_bus
        
        # Load built-in templates
        self._load_built_in_templates()
        
        logger.info("CircuitDesigner initialized with dependencies")
    
    def _load_built_in_templates(self) -> None:
        """Load built-in circuit templates."""
        # Define built-in templates
        templates = [
            {
                "name": "sequential_pipeline",
                "description": "A sequential pipeline of processing agents",
                "template_def": {
                    "name": "Sequential Pipeline",
                    "description": "A circuit that processes data sequentially through a pipeline",
                    "agents": {
                        "input": {
                            "type": "ReflexAgent",
                            "role": "INPUT",
                            "name": "Input Agent",
                            "description": "Receives input data and passes it to the first processor"
                        },
                        "processor1": {
                            "type": "${processor1_type}",
                            "role": "PROCESSOR",
                            "name": "Processor 1",
                            "description": "First processing stage"
                        },
                        "processor2": {
                            "type": "${processor2_type}",
                            "role": "PROCESSOR",
                            "name": "Processor 2",
                            "description": "Second processing stage"
                        },
                        "output": {
                            "type": "ReflexAgent",
                            "role": "OUTPUT",
                            "name": "Output Agent",
                            "description": "Receives processed data and produces final output"
                        }
                    },
                    "connections": [
                        {
                            "source": "input",
                            "target": "processor1",
                            "connection_type": "direct"
                        },
                        {
                            "source": "processor1",
                            "target": "processor2",
                            "connection_type": "direct"
                        },
                        {
                            "source": "processor2",
                            "target": "output",
                            "connection_type": "direct"
                        }
                    ],
                    "metadata": {
                        "template": "sequential_pipeline"
                    }
                }
            },
            {
                "name": "star_network",
                "description": "A central coordinator with radiating connections to worker agents",
                "template_def": {
                    "name": "Star Network",
                    "description": "A circuit with a central coordinator and multiple worker agents",
                    "agents": {
                        "input": {
                            "type": "ReflexAgent",
                            "role": "INPUT",
                            "name": "Input Agent",
                            "description": "Receives input data and passes it to the coordinator"
                        },
                        "coordinator": {
                            "type": "CoordinatorAgent",
                            "role": "COORDINATOR",
                            "name": "Coordinator",
                            "description": "Coordinates work among worker agents"
                        },
                        "worker1": {
                            "type": "${worker1_type}",
                            "role": "PROCESSOR",
                            "name": "Worker 1",
                            "description": "First worker agent"
                        },
                        "worker2": {
                            "type": "${worker2_type}",
                            "role": "PROCESSOR",
                            "name": "Worker 2",
                            "description": "Second worker agent"
                        },
                        "worker3": {
                            "type": "${worker3_type}",
                            "role": "PROCESSOR",
                            "name": "Worker 3",
                            "description": "Third worker agent"
                        },
                        "output": {
                            "type": "ReflexAgent",
                            "role": "OUTPUT",
                            "name": "Output Agent",
                            "description": "Receives processed data and produces final output"
                        }
                    },
                    "connections": [
                        {
                            "source": "input",
                            "target": "coordinator",
                            "connection_type": "direct"
                        },
                        {
                            "source": "coordinator",
                            "target": "worker1",
                            "connection_type": "direct"
                        },
                        {
                            "source": "coordinator",
                            "target": "worker2",
                            "connection_type": "direct"
                        },
                        {
                            "source": "coordinator",
                            "target": "worker3",
                            "connection_type": "direct"
                        },
                        {
                            "source": "worker1",
                            "target": "coordinator",
                            "connection_type": "direct"
                        },
                        {
                            "source": "worker2",
                            "target": "coordinator",
                            "connection_type": "direct"
                        },
                        {
                            "source": "worker3",
                            "target": "coordinator",
                            "connection_type": "direct"
                        },
                        {
                            "source": "coordinator",
                            "target": "output",
                            "connection_type": "direct"
                        }
                    ],
                    "metadata": {
                        "template": "star_network"
                    }
                }
            }
        ]
        
        # Register templates
        for template_data in templates:
            template = CircuitTemplate(
                name=template_data["name"],
                description=template_data["description"],
                template_def=template_data["template_def"]
            )
            self._templates[template.name] = template
        
        logger.debug(f"Loaded {len(templates)} built-in circuit templates")
    
    async def create_circuit(self, definition: CircuitDefinition) -> CircuitID:
        """
        Create a new circuit from a definition.
        
        Args:
            definition: Circuit definition
            
        Returns:
            ID of the created circuit
            
        Raises:
            CircuitDesignerError: If circuit creation fails
            ValidationError: If the circuit definition is invalid
        """
        with self._lock:
            # Validate the circuit
            validation_level = config.get("circuit", "validation_level", "strict")
            
            if validation_level != "none":
                available_agents = self._agent_manager.get_all_agent_types()
                errors = CircuitValidator.validate_circuit(definition, available_agents)
                
                if errors and validation_level == "strict":
                    error_str = "\n".join(errors)
                    raise ValidationError(f"Circuit validation failed:\n{error_str}")
                elif errors and validation_level == "warn":
                    error_str = "\n".join(errors)
                    logger.warning(f"Circuit validation warnings:\n{error_str}")
            
            # Create the circuit
            circuit_id = str(uuid.uuid4())
            circuit = Circuit(circuit_id, definition, self._agent_manager, self._synaptic_bus)
            
            # Store the circuit
            self._circuits[circuit_id] = circuit
            
            logger.info(f"Created circuit {definition.name} ({circuit_id})")
            
            return circuit_id
    
    async def create_from_template(self, template_name: str, 
                                 parameters: Dict[str, Any] = None) -> CircuitID:
        """
        Create a circuit from a template.
        
        Args:
            template_name: Name of the template to use
            parameters: Parameter values to apply to the template
            
        Returns:
            ID of the created circuit
            
        Raises:
            CircuitDesignerError: If the template doesn't exist or circuit creation fails
        """
        # Get the template
        template = self._templates.get(template_name)
        if not template:
            raise CircuitDesignerError(f"Template '{template_name}' not found")
        
        # Create a definition from the template
        definition = template.create_definition(parameters)
        
        # Create a circuit from the definition
        return await self.create_circuit(definition)
    
    async def deploy_circuit(self, circuit_id: CircuitID) -> None:
        """
        Deploy a circuit.
        
        Args:
            circuit_id: ID of the circuit to deploy
            
        Raises:
            CircuitDesignerError: If the circuit doesn't exist or deployment fails
        """
        with self._lock:
            circuit = self._circuits.get(circuit_id)
            if not circuit:
                raise CircuitDesignerError(f"Circuit '{circuit_id}' not found")
            
            await circuit.deploy()
    
    async def create_and_deploy(self, definition: CircuitDefinition) -> CircuitID:
        """
        Create and deploy a circuit in one step.
        
        Args:
            definition: Circuit definition
            
        Returns:
            ID of the created and deployed circuit
            
        Raises:
            CircuitDesignerError: If circuit creation or deployment fails
        """
        circuit_id = await self.create_circuit(definition)
        await self.deploy_circuit(circuit_id)
        return circuit_id
    
    async def send_input(self, circuit_id: CircuitID, input_data: Any,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Send input to a circuit.
        
        Args:
            circuit_id: ID of the circuit
            input_data: Data to send as input
            metadata: Additional metadata for the input
            
        Raises:
            CircuitDesignerError: If the circuit doesn't exist or input sending fails
        """
        circuit = self._circuits.get(circuit_id)
        if not circuit:
            raise CircuitDesignerError(f"Circuit '{circuit_id}' not found")

        await circuit.send_input(input_data, metadata)

    async def get_output(self, circuit_id: CircuitID, timeout: Optional[float] = 5.0) -> Dict[str, Any]:
        """
        Wait for the next output from a circuit.

        Args:
            circuit_id: ID of the circuit
            timeout: Seconds to wait (None waits forever)

        Returns:
            {"agent": name of the agent that produced it, "content": ..., "trace_id": ...}

        Raises:
            CircuitDesignerError: If the circuit doesn't exist
            asyncio.TimeoutError: If no output arrives in time
        """
        circuit = self._circuits.get(circuit_id)
        if not circuit:
            raise CircuitDesignerError(f"Circuit '{circuit_id}' not found")

        return await circuit.get_output(timeout)

    async def pause_circuit(self, circuit_id: CircuitID) -> None:
        """
        Pause a circuit.
        
        Args:
            circuit_id: ID of the circuit to pause
            
        Raises:
            CircuitDesignerError: If the circuit doesn't exist or pausing fails
        """
        circuit = self._circuits.get(circuit_id)
        if not circuit:
            raise CircuitDesignerError(f"Circuit '{circuit_id}' not found")
        
        await circuit.pause()
    
    async def resume_circuit(self, circuit_id: CircuitID) -> None:
        """
        Resume a paused circuit.
        
        Args:
            circuit_id: ID of the circuit to resume
            
        Raises:
            CircuitDesignerError: If the circuit doesn't exist or resuming fails
        """
        circuit = self._circuits.get(circuit_id)
        if not circuit:
            raise CircuitDesignerError(f"Circuit '{circuit_id}' not found")
        
        await circuit.resume()
    
    async def terminate_circuit(self, circuit_id: CircuitID) -> None:
        """
        Terminate a circuit.
        
        Args:
            circuit_id: ID of the circuit to terminate
            
        Raises:
            CircuitDesignerError: If the circuit doesn't exist
        """
        with self._lock:
            circuit = self._circuits.get(circuit_id)
            if not circuit:
                raise CircuitDesignerError(f"Circuit '{circuit_id}' not found")
            
            await circuit.terminate()
            del self._circuits[circuit_id]
    
    def get_circuit(self, circuit_id: CircuitID) -> Optional[Circuit]:
        """
        Get a circuit by ID.
        
        Args:
            circuit_id: ID of the circuit
            
        Returns:
            The circuit, or None if not found
        """
        return self._circuits.get(circuit_id)
    
    def get_all_circuits(self) -> Dict[CircuitID, Circuit]:
        """
        Get all circuits.
        
        Returns:
            Dictionary mapping circuit IDs to circuits
        """
        return self._circuits.copy()
    
    def register_template(self, template: CircuitTemplate) -> None:
        """
        Register a new circuit template.
        
        Args:
            template: Template to register
            
        Raises:
            CircuitDesignerError: If a template with the same name already exists
        """
        with self._lock:
            if template.name in self._templates:
                raise CircuitDesignerError(f"Template '{template.name}' already exists")
            
            self._templates[template.name] = template
            logger.debug(f"Registered circuit template: {template.name}")
    
    def get_template(self, name: str) -> Optional[CircuitTemplate]:
        """
        Get a template by name.
        
        Args:
            name: Name of the template
            
        Returns:
            The template, or None if not found
        """
        return self._templates.get(name)
    
    def get_all_templates(self) -> Dict[str, CircuitTemplate]:
        """
        Get all registered templates.
        
        Returns:
            Dictionary mapping template names to templates
        """
        return self._templates.copy()
    
    def save_template(self, template: CircuitTemplate, file_path: Union[str, Path]) -> None:
        """
        Save a template to a file.
        
        Args:
            template: Template to save
            file_path: Path to save the template to
            
        Raises:
            CircuitDesignerError: If saving fails
        """
        try:
            # Convert to dictionary
            template_dict = template.to_dict()
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(template_dict, f, indent=2)
            
            logger.debug(f"Saved template {template.name} to {file_path}")
        except Exception as e:
            raise CircuitDesignerError(f"Error saving template: {e}") from e
    
    def load_template(self, file_path: Union[str, Path]) -> CircuitTemplate:
        """
        Load a template from a file.
        
        Args:
            file_path: Path to load the template from
            
        Returns:
            Loaded template
            
        Raises:
            CircuitDesignerError: If loading fails
        """
        try:
            # Load from file
            with open(file_path, 'r') as f:
                template_dict = json.load(f)
            
            # Create template
            template = CircuitTemplate.from_dict(template_dict)
            
            logger.debug(f"Loaded template {template.name} from {file_path}")
            
            return template
        except Exception as e:
            raise CircuitDesignerError(f"Error loading template: {e}") from e
