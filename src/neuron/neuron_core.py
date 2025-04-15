"""
neuron_core.py - Core Functionality for Neuron Framework

This module serves as the central hub for the Neuron framework, providing
core functionality and abstractions that are used throughout the system.
It handles framework initialization, lifecycle management, and serves as
the entry point for the framework's API.

The NeuronCore class is the heart of the framework, responsible for 
initializing and coordinating all the components of the system.
"""

import asyncio
import atexit
import importlib
import inspect
import logging
import os
import signal
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from .config import config, initialize_config
from .exceptions import (
    AgentInitializationError,
    CircuitDesignerError,
    ConfigurationError,
    NeuronException,
    PluginError,
)
from .types import AgentID, CircuitID

logger = logging.getLogger(__name__)


class NeuronCore:
    """
    Central coordinator for the Neuron framework.
    
    This class is responsible for initializing and managing all framework
    components, handling lifecycle events, and providing centralized
    resources and services.
    
    Conceptually, NeuronCore is like the brain stem - it connects and
    coordinates essential functions, provides common pathways for
    information flow, and maintains the overall system state.
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern for NeuronCore."""
        if cls._instance is None:
            cls._instance = super(NeuronCore, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None,
                 config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the Neuron framework.
        
        Args:
            config_path: Optional path to configuration file
            config_dict: Optional configuration dictionary
        
        Note:
            This will only fully initialize once, even if called multiple times.
            Subsequent calls will update configuration but not reinitialize components.
        """
        # Only initialize once
        if self._initialized:
            if config_path or config_dict:
                # Update configuration if provided
                if config_path:
                    config.load_file(config_path)
                if config_dict:
                    config.update(config_dict)
                logger.info("Updated Neuron configuration")
            return
        
        # Initialize configuration
        try:
            initialize_config(config_path, config_dict)
        except ConfigurationError as e:
            logger.error(f"Failed to initialize configuration: {e}")
            raise
        
        # Core state variables
        self._running = False
        self._lock = threading.RLock()
        self._shutdown_hooks = []
        self._agents = {}  # AgentID -> Agent
        self._circuits = {}  # CircuitID -> Circuit
        self._plugins = {}  # Plugin name -> Plugin instance
        
        # Component references (will be set during init_components)
        self.agent_manager = None
        self.synaptic_bus = None
        self.circuit_designer = None
        self.memory_manager = None
        self.neuro_monitor = None
        self.extension_manager = None
        
        # Event loop for async operations
        self.loop = asyncio.new_event_loop()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        # Register atexit handler
        atexit.register(self.shutdown)
        
        # Framework is now initialized
        self._initialized = True
        logger.info("NeuronCore initialized")
    
    def init_components(self) -> None:
        """
        Initialize all framework components.
        
        This method creates and initializes the core components of the framework:
        - AgentManager for agent lifecycle management
        - SynapticBus for inter-agent communication
        - CircuitDesigner for creating agent networks
        - MemoryManager for memory systems
        - NeuroMonitor for monitoring and observability
        - ExtensionManager for plugins and extensions
        
        Each component is initialized in a specific order to respect dependencies.
        """
        from .agent import AgentManager
        from .circuit_designer import CircuitDesigner
        from .extensions import ExtensionManager
        from .memory import MemoryManager
        from .neuro_monitor import NeuroMonitor
        from .synaptic_bus import SynapticBus
        
        logger.info("Initializing Neuron components")
        
        # Initialize components in dependency order
        try:
            with self._lock:
                # Create and initialize components
                self.synaptic_bus = SynapticBus()
                self.memory_manager = MemoryManager()
                self.agent_manager = AgentManager()
                self.circuit_designer = CircuitDesigner()
                self.neuro_monitor = NeuroMonitor()
                self.extension_manager = ExtensionManager()
                
                # Initialize components that require other components
                self.synaptic_bus.initialize()
                self.memory_manager.initialize()
                self.agent_manager.initialize(self.synaptic_bus, self.memory_manager)
                self.circuit_designer.initialize(self.agent_manager, self.synaptic_bus)
                self.neuro_monitor.initialize(
                    self.agent_manager, self.synaptic_bus, self.circuit_designer
                )
                
                # Initialize extensions last so they can access all other components
                data_dir = Path(config.get("system", "data_dir", "./data"))
                plugin_dir = Path(config.get("system", "plugin_dir", "./plugins"))
                self.extension_manager.initialize(
                    plugin_dir=plugin_dir,
                    data_dir=data_dir,
                    neuron_core=self
                )
                
                # Load discovered plugins if auto-discovery is enabled
                if config.get("extensions", "auto_discover", True):
                    self.extension_manager.discover_plugins()
            
            logger.info("All Neuron components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Neuron components: {e}")
            self.shutdown()
            raise NeuronException(f"Failed to initialize Neuron components: {e}") from e
    
    def start(self) -> None:
        """
        Start the Neuron framework and all its components.
        
        This initiates the processing of messages and activation of all
        framework services. After this call, agents can start receiving
        and processing messages.
        """
        if self._running:
            logger.warning("Neuron is already running")
            return
        
        logger.info("Starting Neuron framework")
        
        try:
            # Initialize components if not already done
            if not hasattr(self, 'agent_manager') or self.agent_manager is None:
                self.init_components()
            
            with self._lock:
                # Start components in dependency order
                self.synaptic_bus.start()
                self.memory_manager.start()
                self.agent_manager.start()
                self.neuro_monitor.start()
                
                # Start any plugins that were loaded
                self.extension_manager.start_plugins()
                
                self._running = True
            
            logger.info("Neuron framework started successfully")
        except Exception as e:
            logger.error(f"Error starting Neuron framework: {e}")
            self.shutdown()
            raise NeuronException(f"Failed to start Neuron framework: {e}") from e
    
    def shutdown(self) -> None:
        """
        Shutdown the Neuron framework and all its components.
        
        This performs a graceful shutdown of all framework services,
        ensuring that all pending operations are completed or properly
        aborted, and resources are released.
        """
        if not self._initialized or not self._running:
            logger.debug("Neuron is not running, nothing to shut down")
            return
        
        logger.info("Shutting down Neuron framework")
        
        with self._lock:
            try:
                # Run shutdown hooks
                for hook in self._shutdown_hooks:
                    try:
                        hook()
                    except Exception as e:
                        logger.error(f"Error in shutdown hook: {e}")
                
                # Shutdown components in reverse dependency order
                if hasattr(self, 'extension_manager') and self.extension_manager:
                    self.extension_manager.stop_plugins()
                
                if hasattr(self, 'neuro_monitor') and self.neuro_monitor:
                    self.neuro_monitor.stop()
                
                if hasattr(self, 'agent_manager') and self.agent_manager:
                    self.agent_manager.stop()
                
                if hasattr(self, 'memory_manager') and self.memory_manager:
                    self.memory_manager.stop()
                
                if hasattr(self, 'synaptic_bus') and self.synaptic_bus:
                    self.synaptic_bus.stop()
                
                # Close the event loop
                if hasattr(self, 'loop') and self.loop and not self.loop.is_closed():
                    self.loop.close()
                
                self._running = False
            except Exception as e:
                logger.error(f"Error during Neuron shutdown: {e}")
                # Continue with shutdown even if there are errors
            finally:
                # Clear instance reference to allow re-initialization if needed
                type(self)._instance = None
                logger.info("Neuron framework shutdown complete")
    
    def add_shutdown_hook(self, hook: Callable[[], None]) -> None:
        """
        Add a function to be called during framework shutdown.
        
        Args:
            hook: Function to call during shutdown
        """
        with self._lock:
            self._shutdown_hooks.append(hook)
    
    def register_agent(self, agent_id: AgentID, agent: Any) -> None:
        """
        Register an agent with the framework.
        
        Args:
            agent_id: Unique identifier for the agent
            agent: Agent instance
        """
        with self._lock:
            self._agents[agent_id] = agent
    
    def unregister_agent(self, agent_id: AgentID) -> None:
        """
        Unregister an agent from the framework.
        
        Args:
            agent_id: Unique identifier for the agent
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
    
    def get_agent(self, agent_id: AgentID) -> Optional[Any]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: Unique identifier for the agent
            
        Returns:
            The agent instance, or None if not found
        """
        return self._agents.get(agent_id)
    
    def register_circuit(self, circuit_id: CircuitID, circuit: Any) -> None:
        """
        Register a circuit with the framework.
        
        Args:
            circuit_id: Unique identifier for the circuit
            circuit: Circuit instance
        """
        with self._lock:
            self._circuits[circuit_id] = circuit
    
    def unregister_circuit(self, circuit_id: CircuitID) -> None:
        """
        Unregister a circuit from the framework.
        
        Args:
            circuit_id: Unique identifier for the circuit
        """
        with self._lock:
            if circuit_id in self._circuits:
                del self._circuits[circuit_id]
    
    def get_circuit(self, circuit_id: CircuitID) -> Optional[Any]:
        """
        Get a circuit by its ID.
        
        Args:
            circuit_id: Unique identifier for the circuit
            
        Returns:
            The circuit instance, or None if not found
        """
        return self._circuits.get(circuit_id)
    
    def register_plugin(self, name: str, plugin: Any) -> None:
        """
        Register a plugin with the framework.
        
        Args:
            name: Name of the plugin
            plugin: Plugin instance
        """
        with self._lock:
            self._plugins[name] = plugin
    
    def unregister_plugin(self, name: str) -> None:
        """
        Unregister a plugin from the framework.
        
        Args:
            name: Name of the plugin
        """
        with self._lock:
            if name in self._plugins:
                del self._plugins[name]
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """
        Get a plugin by its name.
        
        Args:
            name: Name of the plugin
            
        Returns:
            The plugin instance, or None if not found
        """
        return self._plugins.get(name)
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self._signal_handler)
            except (ValueError, OSError):
                # Signal handlers can only be set in the main thread
                pass
    
    def _signal_handler(self, sig, frame) -> None:
        """Handle termination signals by initiating shutdown."""
        logger.info(f"Received signal {sig}, initiating shutdown")
        self.shutdown()
    
    @property
    def is_running(self) -> bool:
        """Check if the framework is currently running."""
        return self._running
    
    @property
    def is_initialized(self) -> bool:
        """Check if the framework has been initialized."""
        return self._initialized
    
    @contextmanager
    def run_context(self):
        """
        Context manager for running the Neuron framework.
        
        This provides a convenient way to ensure proper shutdown
        even in the case of exceptions.
        
        Example:
            with NeuronCore().run_context():
                # Framework is running within this block
                # Do something with the framework
            # Framework is automatically shut down when exiting the block
        """
        try:
            self.start()
            yield self
        finally:
            self.shutdown()
    
    def __enter__(self):
        """Support for using NeuronCore as a context manager."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure shutdown when exiting context."""
        self.shutdown()


# Convenient access functions

def get_core() -> NeuronCore:
    """
    Get the global NeuronCore instance.
    
    This function is the recommended way to access the NeuronCore
    throughout the Neuron framework.
    
    Returns:
        The global NeuronCore instance
    """
    return NeuronCore()


def initialize(config_path: Optional[Union[str, Path]] = None,
              config_dict: Optional[Dict[str, Any]] = None) -> NeuronCore:
    """
    Initialize the Neuron framework.
    
    This is a convenience function that creates and initializes
    the NeuronCore and all framework components.
    
    Args:
        config_path: Optional path to configuration file
        config_dict: Optional configuration dictionary
        
    Returns:
        The initialized NeuronCore instance
    """
    core = NeuronCore(config_path, config_dict)
    core.init_components()
    return core


def start(config_path: Optional[Union[str, Path]] = None,
         config_dict: Optional[Dict[str, Any]] = None) -> NeuronCore:
    """
    Initialize and start the Neuron framework.
    
    This is a convenience function that creates, initializes,
    and starts the NeuronCore and all framework components.
    
    Args:
        config_path: Optional path to configuration file
        config_dict: Optional configuration dictionary
        
    Returns:
        The started NeuronCore instance
    """
    core = initialize(config_path, config_dict)
    core.start()
    return core


def shutdown() -> None:
    """
    Shutdown the Neuron framework.
    
    This is a convenience function that shuts down the NeuronCore
    and all framework components.
    """
    NeuronCore().shutdown()


@contextmanager
def run_context(config_path: Optional[Union[str, Path]] = None,
               config_dict: Optional[Dict[str, Any]] = None):
    """
    Context manager for running the Neuron framework.
    
    This is a convenience function that provides a context manager
    for running the Neuron framework.
    
    Args:
        config_path: Optional path to configuration file
        config_dict: Optional configuration dictionary
        
    Yields:
        The running NeuronCore instance
    """
    core = NeuronCore(config_path, config_dict)
    with core.run_context():
        yield core
"""
