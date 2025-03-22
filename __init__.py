"""
Neuron - A Composable Agent Framework Toolkit

Neuron is a comprehensive framework for building composable AI agent systems
inspired by neuroscience principles. It provides tools for creating, deploying,
and orchestrating networks of specialized AI agents that can communicate and
collaborate to solve complex problems.

The framework draws inspiration from how the human brain works, with different
specialized regions cooperating through neural pathways. It enables AI systems
that exhibit emergent intelligence through the cooperation of simpler components.
"""

# Version information
__version__ = "1.0.0"
__author__ = "Neuron Framework Team"
__license__ = "MIT"

# Import core components for convenience
from .neuron_core import NeuronCore, initialize, start, shutdown, run_context
from .agent import BaseAgent, AgentBuilder, AgentConfig, AgentState
from .memory import MemoryManager, MemoryType
from .synaptic_bus import SynapticBus, Message
from .circuit_designer import CircuitDesigner, CircuitDefinition
from .neuro_monitor import NeuroMonitor
from .extensions import Plugin, PluginMetadata
from .config import config, get_config

# Special agents for convenience imports
from .agent import (
    ReflexAgent,
    DeliberativeAgent,
    LearningAgent,
    CoordinatorAgent
)

# Behavioral components for convenience imports
from .behavior_controller import (
    BehaviorController,
    BehaviorProfile,
    BehaviorTrait,
    BehaviorMode,
    with_behavior_control
)

# Convenience function to create a new instance of the framework
def create_framework(config_path=None, config_dict=None):
    """
    Create and initialize a new instance of the Neuron framework.
    
    Args:
        config_path: Optional path to a configuration file
        config_dict: Optional configuration dictionary
        
    Returns:
        Initialized NeuronCore instance
    """
    return initialize(config_path, config_dict)

# Convenience function to create a new agent
def create_agent(agent_type, name=None, description=None, **kwargs):
    """
    Create a new agent instance.
    
    This is a convenience function that requires an initialized framework.
    
    Args:
        agent_type: Type of agent to create (class or string name)
        name: Optional name for the agent
        description: Optional description
        **kwargs: Additional arguments for the agent
        
    Returns:
        ID of the created agent
    """
    core = NeuronCore()
    if not core.is_initialized:
        raise RuntimeError("Framework not initialized. Call initialize() first.")
    
    builder = AgentBuilder(core.agent_manager)
    
    agent_id = (builder
                .of_type(agent_type)
                .with_name(name or "")
                .with_description(description or "")
                .with_config(**kwargs)
                .build())
    
    return agent_id
"""
