"""
extensions.py - Plugin and Extension System for Neuron Framework

This module implements the plugin and extension system for the Neuron framework,
allowing users to extend and customize the framework's functionality with
additional components, integrations, and capabilities.

The extension system is inspired by how the brain integrates with various
external systems and adapts to new inputs and environments.
"""

import importlib
import importlib.util
import inspect
import json
import logging
import os
import pkgutil
import sys
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

from .config import config
from .exceptions import ExtensionError, PluginError

logger = logging.getLogger(__name__)


class PluginScope(Enum):
    """
    Scope of a plugin's capabilities.
    
    This defines what parts of the framework a plugin can modify
    and interact with, determining its integration depth.
    """
    AGENT = "agent"             # Can create/modify agent types only
    MEMORY = "memory"           # Can create/modify memory systems only
    COMMUNICATION = "communication"  # Can create/modify communication components only
    CIRCUIT = "circuit"         # Can create/modify circuit capabilities only
    MONITORING = "monitoring"   # Can extend monitoring capabilities only
    SYSTEM = "system"           # Full system access


@dataclass
class PluginMetadata:
    """
    Metadata about a plugin.
    
    This includes information about the plugin's identity, compatibility,
    and capabilities, used for plugin management and validation.
    """
    name: str                           # Unique name of the plugin
    version: str                        # Version string (semver)
    description: str                    # Description of the plugin
    author: str                         # Author/creator of the plugin
    scope: List[PluginScope]            # Plugin's scope of capabilities
    dependencies: Dict[str, str] = field(default_factory=dict)  # Plugin dependencies (name -> version)
    framework_version: str = ""         # Compatible framework version
    license: str = "MIT"                # License of the plugin
    homepage: str = ""                  # Plugin homepage/documentation URL
    tags: List[str] = field(default_factory=list)  # Tags for categorization
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        # Convert enums to strings
        result["scope"] = [s.value for s in self.scope]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginMetadata':
        """Create from dictionary representation."""
        # Convert scope strings to enums
        if "scope" in data:
            data = data.copy()  # Don't modify the input
            data["scope"] = [PluginScope(s) for s in data["scope"]]
        return cls(**data)
    
    def is_compatible_with(self, framework_version: str) -> bool:
        """
        Check if the plugin is compatible with a framework version.
        
        Args:
            framework_version: Framework version to check against
            
        Returns:
            True if compatible, False otherwise
        """
        # This is a simplified implementation
        # A real implementation would use proper semver comparison
        if not self.framework_version:
            return True  # No version requirement
        
        # Remove prefix/suffix and compare major.minor version only
        required = self.framework_version.split(".")[:2]
        actual = framework_version.split(".")[:2]
        
        return required == actual


class Plugin(ABC):
    """
    Base class for all plugins in the Neuron framework.
    
    Plugins extend the framework with additional functionality,
    integrating with various components of the system.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize a plugin.
        
        Args:
            metadata: Plugin metadata
        """
        self.metadata = metadata
        self._initialized = False
        self._running = False
        
        logger.debug(f"Created plugin: {metadata.name} v{metadata.version}")
    
    @abstractmethod
    def initialize(self, neuron_core: Any) -> None:
        """
        Initialize the plugin with the framework core.
        
        This is called when the plugin is first loaded, giving it
        access to the framework's core components and services.
        
        Args:
            neuron_core: NeuronCore instance
            
        Raises:
            PluginError: If initialization fails
        """
        pass
    
    @abstractmethod
    def start(self) -> None:
        """
        Start the plugin.
        
        This is called when the framework is started, signaling
        the plugin to begin its active operations.
        
        Raises:
            PluginError: If startup fails
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """
        Stop the plugin.
        
        This is called when the framework is shutting down, giving
        the plugin a chance to clean up resources and terminate gracefully.
        
        Raises:
            PluginError: If shutdown fails
        """
        pass
    
    def get_metadata(self) -> PluginMetadata:
        """
        Get the plugin's metadata.
        
        Returns:
            Plugin metadata
        """
        return self.metadata
    
    def is_initialized(self) -> bool:
        """
        Check if the plugin is initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    def is_running(self) -> bool:
        """
        Check if the plugin is running.
        
        Returns:
            True if running, False otherwise
        """
        return self._running


class AgentPlugin(Plugin):
    """
    Plugin for extending agent capabilities.
    
    Agent plugins add new agent types, behaviors, or capabilities
    to the agent system, enabling specialized agent functionality.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize an agent plugin.
        
        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._agent_types = {}  # name -> agent class
        
        # Ensure scope includes AGENT
        if PluginScope.AGENT not in metadata.scope:
            metadata.scope.append(PluginScope.AGENT)
    
    def register_agent_type(self, agent_class: Type) -> None:
        """
        Register an agent type.
        
        Args:
            agent_class: Agent class to register
            
        Raises:
            PluginError: If the agent type cannot be registered
        """
        try:
            # Validate agent class
            if not hasattr(agent_class, '__name__'):
                raise PluginError("Agent class must have a name")
            
            name = agent_class.__name__
            self._agent_types[name] = agent_class
            logger.debug(f"Plugin {self.metadata.name} registered agent type: {name}")
        except Exception as e:
            raise PluginError(f"Error registering agent type: {e}") from e
    
    def get_agent_types(self) -> Dict[str, Type]:
        """
        Get all registered agent types.
        
        Returns:
            Dictionary mapping agent type names to agent classes
        """
        return self._agent_types.copy()


class MemoryPlugin(Plugin):
    """
    Plugin for extending memory capabilities.
    
    Memory plugins add new memory systems, storage backends, or
    memory-related functions to the framework.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize a memory plugin.
        
        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._memory_stores = {}  # name -> memory store class
        self._memory_systems = {}  # name -> memory system class
        
        # Ensure scope includes MEMORY
        if PluginScope.MEMORY not in metadata.scope:
            metadata.scope.append(PluginScope.MEMORY)
    
    def register_memory_store(self, store_class: Type, name: Optional[str] = None) -> None:
        """
        Register a memory store class.
        
        Args:
            store_class: Memory store class to register
            name: Optional name for the store (defaults to class name)
            
        Raises:
            PluginError: If the memory store cannot be registered
        """
        try:
            # Get name if not provided
            if name is None:
                if not hasattr(store_class, '__name__'):
                    raise PluginError("Memory store class must have a name")
                name = store_class.__name__
            
            self._memory_stores[name] = store_class
            logger.debug(f"Plugin {self.metadata.name} registered memory store: {name}")
        except Exception as e:
            raise PluginError(f"Error registering memory store: {e}") from e
    
    def register_memory_system(self, system_class: Type, name: Optional[str] = None) -> None:
        """
        Register a memory system class.
        
        Args:
            system_class: Memory system class to register
            name: Optional name for the system (defaults to class name)
            
        Raises:
            PluginError: If the memory system cannot be registered
        """
        try:
            # Get name if not provided
            if name is None:
                if not hasattr(system_class, '__name__'):
                    raise PluginError("Memory system class must have a name")
                name = system_class.__name__
            
            self._memory_systems[name] = system_class
            logger.debug(f"Plugin {self.metadata.name} registered memory system: {name}")
        except Exception as e:
            raise PluginError(f"Error registering memory system: {e}") from e
    
    def get_memory_stores(self) -> Dict[str, Type]:
        """
        Get all registered memory stores.
        
        Returns:
            Dictionary mapping store names to store classes
        """
        return self._memory_stores.copy()
    
    def get_memory_systems(self) -> Dict[str, Type]:
        """
        Get all registered memory systems.
        
        Returns:
            Dictionary mapping system names to system classes
        """
        return self._memory_systems.copy()


class CommunicationPlugin(Plugin):
    """
    Plugin for extending communication capabilities.
    
    Communication plugins add new message types, routing mechanisms,
    or communication channels to the framework.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize a communication plugin.
        
        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._message_processors = {}  # name -> processor function
        self._channel_types = {}  # name -> channel class
        
        # Ensure scope includes COMMUNICATION
        if PluginScope.COMMUNICATION not in metadata.scope:
            metadata.scope.append(PluginScope.COMMUNICATION)
    
    def register_message_processor(self, processor: Callable, name: str) -> None:
        """
        Register a message processor function.
        
        Args:
            processor: Message processor function
            name: Name for the processor
            
        Raises:
            PluginError: If the processor cannot be registered
        """
        try:
            if not callable(processor):
                raise PluginError("Message processor must be callable")
            
            self._message_processors[name] = processor
            logger.debug(f"Plugin {self.metadata.name} registered message processor: {name}")
        except Exception as e:
            raise PluginError(f"Error registering message processor: {e}") from e
    
    def register_channel_type(self, channel_class: Type, name: Optional[str] = None) -> None:
        """
        Register a channel type.
        
        Args:
            channel_class: Channel class to register
            name: Optional name for the channel type (defaults to class name)
            
        Raises:
            PluginError: If the channel type cannot be registered
        """
        try:
            # Get name if not provided
            if name is None:
                if not hasattr(channel_class, '__name__'):
                    raise PluginError("Channel class must have a name")
                name = channel_class.__name__
            
            self._channel_types[name] = channel_class
            logger.debug(f"Plugin {self.metadata.name} registered channel type: {name}")
        except Exception as e:
            raise PluginError(f"Error registering channel type: {e}") from e
    
    def get_message_processors(self) -> Dict[str, Callable]:
        """
        Get all registered message processors.
        
        Returns:
            Dictionary mapping processor names to processor functions
        """
        return self._message_processors.copy()
    
    def get_channel_types(self) -> Dict[str, Type]:
        """
        Get all registered channel types.
        
        Returns:
            Dictionary mapping channel type names to channel classes
        """
        return self._channel_types.copy()


class CircuitPlugin(Plugin):
    """
    Plugin for extending circuit capabilities.
    
    Circuit plugins add new circuit templates, connection types,
    or circuit components to the framework.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize a circuit plugin.
        
        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._circuit_templates = {}  # name -> template
        self._connection_types = {}  # name -> connection type class
        
        # Ensure scope includes CIRCUIT
        if PluginScope.CIRCUIT not in metadata.scope:
            metadata.scope.append(PluginScope.CIRCUIT)
    
    def register_circuit_template(self, template_name: str, template_definition: Dict[str, Any]) -> None:
        """
        Register a circuit template.
        
        Args:
            template_name: Name for the template
            template_definition: Template definition
            
        Raises:
            PluginError: If the template cannot be registered
        """
        try:
            self._circuit_templates[template_name] = template_definition
            logger.debug(f"Plugin {self.metadata.name} registered circuit template: {template_name}")
        except Exception as e:
            raise PluginError(f"Error registering circuit template: {e}") from e
    
    def register_connection_type(self, connection_class: Type, name: Optional[str] = None) -> None:
        """
        Register a connection type.
        
        Args:
            connection_class: Connection class to register
            name: Optional name for the connection type (defaults to class name)
            
        Raises:
            PluginError: If the connection type cannot be registered
        """
        try:
            # Get name if not provided
            if name is None:
                if not hasattr(connection_class, '__name__'):
                    raise PluginError("Connection class must have a name")
                name = connection_class.__name__
            
            self._connection_types[name] = connection_class
            logger.debug(f"Plugin {self.metadata.name} registered connection type: {name}")
        except Exception as e:
            raise PluginError(f"Error registering connection type: {e}") from e
    
    def get_circuit_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered circuit templates.
        
        Returns:
            Dictionary mapping template names to template definitions
        """
        return self._circuit_templates.copy()
    
    def get_connection_types(self) -> Dict[str, Type]:
        """
        Get all registered connection types.
        
        Returns:
            Dictionary mapping connection type names to connection classes
        """
        return self._connection_types.copy()


class MonitoringPlugin(Plugin):
    """
    Plugin for extending monitoring capabilities.
    
    Monitoring plugins add new metrics, visualization types,
    or alerting mechanisms to the framework.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize a monitoring plugin.
        
        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._metric_collectors = {}  # name -> collector function
        self._alert_rules = {}  # name -> rule definition
        self._visualizers = {}  # name -> visualizer function
        
        # Ensure scope includes MONITORING
        if PluginScope.MONITORING not in metadata.scope:
            metadata.scope.append(PluginScope.MONITORING)
    
    def register_metric_collector(self, collector: Callable, name: str,
                               interval: float = 10.0) -> None:
        """
        Register a metric collector function.
        
        Args:
            collector: Metric collector function
            name: Name for the collector
            interval: Collection interval in seconds
            
        Raises:
            PluginError: If the collector cannot be registered
        """
        try:
            if not callable(collector):
                raise PluginError("Metric collector must be callable")
            
            self._metric_collectors[name] = (collector, interval)
            logger.debug(f"Plugin {self.metadata.name} registered metric collector: {name}")
        except Exception as e:
            raise PluginError(f"Error registering metric collector: {e}") from e
    
    def register_alert_rule(self, rule_definition: Dict[str, Any], name: str) -> None:
        """
        Register an alert rule.
        
        Args:
            rule_definition: Alert rule definition
            name: Name for the rule
            
        Raises:
            PluginError: If the rule cannot be registered
        """
        try:
            self._alert_rules[name] = rule_definition
            logger.debug(f"Plugin {self.metadata.name} registered alert rule: {name}")
        except Exception as e:
            raise PluginError(f"Error registering alert rule: {e}") from e
    
    def register_visualizer(self, visualizer: Callable, name: str) -> None:
        """
        Register a visualizer function.
        
        Args:
            visualizer: Visualizer function
            name: Name for the visualizer
            
        Raises:
            PluginError: If the visualizer cannot be registered
        """
        try:
            if not callable(visualizer):
                raise PluginError("Visualizer must be callable")
            
            self._visualizers[name] = visualizer
            logger.debug(f"Plugin {self.metadata.name} registered visualizer: {name}")
        except Exception as e:
            raise PluginError(f"Error registering visualizer: {e}") from e
    
    def get_metric_collectors(self) -> Dict[str, Tuple[Callable, float]]:
        """
        Get all registered metric collectors.
        
        Returns:
            Dictionary mapping collector names to (collector, interval) tuples
        """
        return self._metric_collectors.copy()
    
    def get_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all registered alert rules.
        
        Returns:
            Dictionary mapping rule names to rule definitions
        """
        return self._alert_rules.copy()
    
    def get_visualizers(self) -> Dict[str, Callable]:
        """
        Get all registered visualizers.
        
        Returns:
            Dictionary mapping visualizer names to visualizer functions
        """
        return self._visualizers.copy()


class SystemPlugin(Plugin):
    """
    Plugin for extending system-wide capabilities.
    
    System plugins have broad access to the framework's core functionality,
    enabling deep integrations and extensions.
    """
    
    def __init__(self, metadata: PluginMetadata):
        """
        Initialize a system plugin.
        
        Args:
            metadata: Plugin metadata
        """
        super().__init__(metadata)
        self._integrations = {}  # name -> integration
        
        # Ensure scope includes SYSTEM
        if PluginScope.SYSTEM not in metadata.scope:
            metadata.scope.append(PluginScope.SYSTEM)
    
    def register_integration(self, integration: Any, name: str) -> None:
        """
        Register a system integration.
        
        Args:
            integration: Integration object
            name: Name for the integration
            
        Raises:
            PluginError: If the integration cannot be registered
        """
        try:
            self._integrations[name] = integration
            logger.debug(f"Plugin {self.metadata.name} registered integration: {name}")
        except Exception as e:
            raise PluginError(f"Error registering integration: {e}") from e
    
    def get_integrations(self) -> Dict[str, Any]:
        """
        Get all registered integrations.
        
        Returns:
            Dictionary mapping integration names to integration objects
        """
        return self._integrations.copy()


class ExtensionManager:
    """
    Manages plugins and extensions for the Neuron framework.
    
    The ExtensionManager is responsible for discovering, loading, initializing,
    and managing plugins, providing a uniform interface to the framework's
    extension capabilities.
    """
    
    def __init__(self):
        """Initialize the extension manager."""
        self._plugins = {}  # plugin_name -> Plugin
        self._plugin_dir = None
        self._data_dir = None
        self._neuron_core = None
        
        # Plugin factory registry
        self._plugin_factories = {
            PluginScope.AGENT: AgentPlugin,
            PluginScope.MEMORY: MemoryPlugin,
            PluginScope.COMMUNICATION: CommunicationPlugin,
            PluginScope.CIRCUIT: CircuitPlugin,
            PluginScope.MONITORING: MonitoringPlugin,
            PluginScope.SYSTEM: SystemPlugin,
        }
        
        # Framework version (for compatibility checks)
        self._framework_version = "1.0.0"
        
        logger.info("Initialized ExtensionManager")
    
    def initialize(self, plugin_dir: Union[str, Path],
                 data_dir: Union[str, Path],
                 neuron_core: Any) -> None:
        """
        Initialize the extension manager with required paths and dependencies.
        
        Args:
            plugin_dir: Directory for plugins
            data_dir: Directory for plugin data
            neuron_core: NeuronCore instance
        """
        self._plugin_dir = Path(plugin_dir)
        self._data_dir = Path(data_dir)
        self._neuron_core = neuron_core
        
        # Create directories if they don't exist
        self._plugin_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ExtensionManager initialized with plugin dir: {self._plugin_dir}")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in the plugin directory.
        
        This scans the plugin directory for valid plugins and loads them.
        
        Returns:
            List of discovered plugin names
            
        Raises:
            ExtensionError: If plugin discovery fails
        """
        if not self._plugin_dir:
            raise ExtensionError("ExtensionManager not initialized")
        
        discovered_plugins = []
        
        try:
            # Check for plugin directories
            for item in self._plugin_dir.iterdir():
                if item.is_dir():
                    # Check for metadata file
                    metadata_path = item / "metadata.json"
                    if metadata_path.exists():
                        plugin_name = item.name
                        try:
                            # Load the plugin
                            self.load_plugin(plugin_name)
                            discovered_plugins.append(plugin_name)
                        except Exception as e:
                            logger.error(f"Error loading plugin {plugin_name}: {e}")
        except Exception as e:
            raise ExtensionError(f"Error discovering plugins: {e}") from e
        
        logger.info(f"Discovered {len(discovered_plugins)} plugins: {', '.join(discovered_plugins)}")
        return discovered_plugins
    
    def load_plugin(self, plugin_name: str) -> Plugin:
        """
        Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load
            
        Returns:
            Loaded plugin instance
            
        Raises:
            ExtensionError: If plugin loading fails
        """
        if not self._plugin_dir:
            raise ExtensionError("ExtensionManager not initialized")
        
        if plugin_name in self._plugins:
            logger.debug(f"Plugin {plugin_name} already loaded")
            return self._plugins[plugin_name]
        
        try:
            # Get plugin directory
            plugin_dir = self._plugin_dir / plugin_name
            if not plugin_dir.exists() or not plugin_dir.is_dir():
                raise ExtensionError(f"Plugin directory not found: {plugin_dir}")
            
            # Load metadata
            metadata_path = plugin_dir / "metadata.json"
            if not metadata_path.exists():
                raise ExtensionError(f"Plugin metadata not found: {metadata_path}")
            
            with open(metadata_path) as f:
                metadata_dict = json.load(f)
            
            metadata = PluginMetadata.from_dict(metadata_dict)
            
            # Check compatibility
            if not metadata.is_compatible_with(self._framework_version):
                raise ExtensionError(
                    f"Plugin {plugin_name} is not compatible with framework version {self._framework_version}"
                )
            
            # Check dependencies
            for dep_name, dep_version in metadata.dependencies.items():
                if dep_name not in self._plugins:
                    # Try to load dependency
                    try:
                        self.load_plugin(dep_name)
                    except:
                        raise ExtensionError(
                            f"Plugin {plugin_name} depends on {dep_name}, which is not available"
                        )
            
            # Load plugin module
            plugin_module_path = plugin_dir / "__init__.py"
            if not plugin_module_path.exists():
                raise ExtensionError(f"Plugin module not found: {plugin_module_path}")
            
            module_name = f"neuron_plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_module_path)
            if not spec or not spec.loader:
                raise ExtensionError(f"Failed to create module spec for {plugin_name}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and issubclass(obj, Plugin) and
                    obj is not Plugin and obj.__module__ == module_name):
                    plugin_class = obj
                    break
            
            if not plugin_class:
                raise ExtensionError(f"No plugin class found in {plugin_name}")
            
            # Create plugin instance
            plugin = plugin_class(metadata)
            
            # Store plugin
            self._plugins[plugin_name] = plugin
            
            logger.info(f"Loaded plugin: {plugin_name} v{metadata.version}")
            return plugin
        except Exception as e:
            raise ExtensionError(f"Error loading plugin {plugin_name}: {e}") from e
    
    def initialize_plugin(self, plugin_name: str) -> None:
        """
        Initialize a plugin.
        
        Args:
            plugin_name: Name of the plugin to initialize
            
        Raises:
            ExtensionError: If plugin initialization fails
        """
        if not self._neuron_core:
            raise ExtensionError("ExtensionManager not initialized")
        
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            raise ExtensionError(f"Plugin not loaded: {plugin_name}")
        
        if plugin.is_initialized():
            logger.debug(f"Plugin {plugin_name} already initialized")
            return
        
        try:
            # Initialize the plugin
            plugin.initialize(self._neuron_core)
            plugin._initialized = True
            
            logger.info(f"Initialized plugin: {plugin_name}")
        except Exception as e:
            raise ExtensionError(f"Error initializing plugin {plugin_name}: {e}") from e
    
    def start_plugin(self, plugin_name: str) -> None:
        """
        Start a plugin.
        
        Args:
            plugin_name: Name of the plugin to start
            
        Raises:
            ExtensionError: If plugin startup fails
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            raise ExtensionError(f"Plugin not loaded: {plugin_name}")
        
        if not plugin.is_initialized():
            raise ExtensionError(f"Plugin not initialized: {plugin_name}")
        
        if plugin.is_running():
            logger.debug(f"Plugin {plugin_name} already running")
            return
        
        try:
            # Start the plugin
            plugin.start()
            plugin._running = True
            
            logger.info(f"Started plugin: {plugin_name}")
        except Exception as e:
            raise ExtensionError(f"Error starting plugin {plugin_name}: {e}") from e
    
    def stop_plugin(self, plugin_name: str) -> None:
        """
        Stop a plugin.
        
        Args:
            plugin_name: Name of the plugin to stop
            
        Raises:
            ExtensionError: If plugin shutdown fails
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            raise ExtensionError(f"Plugin not loaded: {plugin_name}")
        
        if not plugin.is_running():
            logger.debug(f"Plugin {plugin_name} not running")
            return
        
        try:
            # Stop the plugin
            plugin.stop()
            plugin._running = False
            
            logger.info(f"Stopped plugin: {plugin_name}")
        except Exception as e:
            raise ExtensionError(f"Error stopping plugin {plugin_name}: {e}") from e
    
    def unload_plugin(self, plugin_name: str) -> None:
        """
        Unload a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload
            
        Raises:
            ExtensionError: If plugin unloading fails
        """
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            logger.debug(f"Plugin not loaded: {plugin_name}")
            return
        
        try:
            # Stop the plugin if running
            if plugin.is_running():
                self.stop_plugin(plugin_name)
            
            # Remove plugin
            del self._plugins[plugin_name]
            
            # Remove from sys.modules
            module_name = f"neuron_plugins.{plugin_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            logger.info(f"Unloaded plugin: {plugin_name}")
        except Exception as e:
            raise ExtensionError(f"Error unloading plugin {plugin_name}: {e}") from e
    
    def initialize_plugins(self) -> None:
        """
        Initialize all loaded plugins.
        
        Raises:
            ExtensionError: If initialization fails
        """
        for plugin_name in list(self._plugins.keys()):
            try:
                self.initialize_plugin(plugin_name)
            except Exception as e:
                logger.error(f"Error initializing plugin {plugin_name}: {e}")
    
    def start_plugins(self) -> None:
        """
        Start all initialized plugins.
        
        Raises:
            ExtensionError: If startup fails
        """
        for plugin_name, plugin in self._plugins.items():
            if plugin.is_initialized() and not plugin.is_running():
                try:
                    self.start_plugin(plugin_name)
                except Exception as e:
                    logger.error(f"Error starting plugin {plugin_name}: {e}")
    
    def stop_plugins(self) -> None:
        """
        Stop all running plugins.
        
        Raises:
            ExtensionError: If shutdown fails
        """
        for plugin_name, plugin in self._plugins.items():
            if plugin.is_running():
                try:
                    self.stop_plugin(plugin_name)
                except Exception as e:
                    logger.error(f"Error stopping plugin {plugin_name}: {e}")
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        Get a plugin by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Plugin instance, or None if not found
        """
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, Plugin]:
        """
        Get all loaded plugins.
        
        Returns:
            Dictionary mapping plugin names to plugin instances
        """
        return self._plugins.copy()
    
    def create_plugin(self, plugin_name: str, scope: List[str],
                    author: str, description: str, version: str = "0.1.0") -> Dict[str, Any]:
        """
        Create a new plugin skeleton.
        
        Args:
            plugin_name: Name for the new plugin
            scope: List of plugin scopes
            author: Plugin author
            description: Plugin description
            version: Plugin version
            
        Returns:
            Dictionary with plugin creation information
            
        Raises:
            ExtensionError: If plugin creation fails
        """
        if not self._plugin_dir:
            raise ExtensionError("ExtensionManager not initialized")
        
        # Validate inputs
        if not plugin_name or not plugin_name.isidentifier():
            raise ExtensionError(f"Invalid plugin name: {plugin_name}")
        
        # Convert scope strings to enums
        plugin_scopes = []
        for s in scope:
            try:
                plugin_scopes.append(PluginScope(s))
            except ValueError:
                raise ExtensionError(f"Invalid plugin scope: {s}")
        
        try:
            # Create plugin directory
            plugin_dir = self._plugin_dir / plugin_name
            if plugin_dir.exists():
                raise ExtensionError(f"Plugin directory already exists: {plugin_dir}")
            
            plugin_dir.mkdir(parents=True)
            
            # Create metadata
            metadata = PluginMetadata(
                name=plugin_name,
                version=version,
                description=description,
                author=author,
                scope=plugin_scopes,
                framework_version=self._framework_version
            )
            
            # Write metadata file
            metadata_path = plugin_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            # Determine plugin base class
            if len(plugin_scopes) == 1:
                # Use specific plugin class
                base_class = self._plugin_factories[plugin_scopes[0]].__name__
            else:
                # Use generic Plugin class
                base_class = "Plugin"
            
            # Create plugin module
            module_path = plugin_dir / "__init__.py"
            with open(module_path, 'w') as f:
                f.write(f"""\"\"\"
{plugin_name} - {description}

Author: {author}
Version: {version}
\"\"\"

from neuron.extensions import {base_class}, PluginMetadata

class {plugin_name.capitalize()}Plugin({base_class}):
    \"\"\"
    {description}
    \"\"\"
    
    def initialize(self, neuron_core):
        \"\"\"
        Initialize the plugin.
        
        Args:
            neuron_core: NeuronCore instance
        \"\"\"
        # Your initialization code here
        pass
    
    def start(self):
        \"\"\"
        Start the plugin.
        \"\"\"
        # Your startup code here
        pass
    
    def stop(self):
        \"\"\"
        Stop the plugin.
        \"\"\"
        # Your shutdown code here
        pass
""")
            
            # Create data directory
            data_dir = self._data_dir / plugin_name
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Create README
            readme_path = plugin_dir / "README.md"
            with open(readme_path, 'w') as f:
                f.write(f"""# {plugin_name}

{description}

## Author

{author}

## Version

{version}

## Scope

{', '.join(s.value for s in plugin_scopes)}

## Installation

1. Place this directory in the Neuron framework's plugins directory.
2. Restart the framework.

## Usage

Add usage instructions here.
""")
            
            logger.info(f"Created plugin skeleton: {plugin_name}")
            
            return {
                "name": plugin_name,
                "path": str(plugin_dir),
                "data_path": str(data_dir),
                "metadata": metadata.to_dict()
            }
        except Exception as e:
            raise ExtensionError(f"Error creating plugin {plugin_name}: {e}") from e
    
    def get_plugin_data_dir(self, plugin_name: str) -> Path:
        """
        Get the data directory for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Path to the plugin's data directory
            
        Raises:
            ExtensionError: If the directory cannot be accessed
        """
        if not self._data_dir:
            raise ExtensionError("ExtensionManager not initialized")
        
        # Create data directory if it doesn't exist
        data_dir = self._data_dir / plugin_name
        data_dir.mkdir(parents=True, exist_ok=True)
        
        return data_dir
"""
