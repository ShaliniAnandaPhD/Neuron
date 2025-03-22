"""
cli.py - Command Line Interface for Neuron Framework

This module provides a command-line interface for the Neuron framework,
allowing users to initialize, start, and manage the framework and its components.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .neuron_core import NeuronCore, initialize, start, shutdown
from .config import config
from .extensions import PluginScope

logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """Set up the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Neuron Framework - A Composable Agent Framework Toolkit"
    )
    
    # Global arguments
    parser.add_argument(
        "--config", 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Set the logging level"
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Initialize command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize the framework"
    )
    init_parser.add_argument(
        "--data-dir",
        help="Path to data directory"
    )
    init_parser.add_argument(
        "--plugin-dir",
        help="Path to plugin directory"
    )
    
    # Start command
    start_parser = subparsers.add_parser(
        "start",
        help="Start the framework"
    )
    start_parser.add_argument(
        "--no-plugins",
        action="store_true",
        help="Disable plugin auto-discovery"
    )
    
    # Stop command
    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop the framework"
    )
    
    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show framework status"
    )
    status_parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed status"
    )
    
    # Plugin commands
    plugin_parser = subparsers.add_parser(
        "plugin",
        help="Plugin management"
    )
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="plugin_command",
        help="Plugin command"
    )
    
    # Plugin list command
    plugin_list_parser = plugin_subparsers.add_parser(
        "list",
        help="List installed plugins"
    )
    
    # Plugin create command
    plugin_create_parser = plugin_subparsers.add_parser(
        "create",
        help="Create a new plugin skeleton"
    )
    plugin_create_parser.add_argument(
        "name",
        help="Name of the plugin"
    )
    plugin_create_parser.add_argument(
        "--scope",
        choices=[s.value for s in PluginScope],
        default="agent",
        help="Scope of the plugin"
    )
    plugin_create_parser.add_argument(
        "--author",
        default="",
        help="Author of the plugin"
    )
    plugin_create_parser.add_argument(
        "--description",
        default="",
        help="Description of the plugin"
    )
    
    # Plugin install command
    plugin_install_parser = plugin_subparsers.add_parser(
        "install",
        help="Install a plugin from a directory"
    )
    plugin_install_parser.add_argument(
        "path",
        help="Path to the plugin directory"
    )
    
    # Agent commands
    agent_parser = subparsers.add_parser(
        "agent",
        help="Agent management"
    )
    agent_subparsers = agent_parser.add_subparsers(
        dest="agent_command",
        help="Agent command"
    )
    
    # Agent list command
    agent_list_parser = agent_subparsers.add_parser(
        "list",
        help="List available agent types"
    )
    
    # Agent create command
    agent_create_parser = agent_subparsers.add_parser(
        "create",
        help="Create a new agent instance"
    )
    agent_create_parser.add_argument(
        "type",
        help="Type of agent to create"
    )
    agent_create_parser.add_argument(
        "--name",
        help="Name of the agent"
    )
    agent_create_parser.add_argument(
        "--description",
        help="Description of the agent"
    )
    agent_create_parser.add_argument(
        "--config",
        help="JSON configuration for the agent"
    )
    
    # Circuit commands
    circuit_parser = subparsers.add_parser(
        "circuit",
        help="Circuit management"
    )
    circuit_subparsers = circuit_parser.add_subparsers(
        dest="circuit_command",
        help="Circuit command"
    )
    
    # Circuit list command
    circuit_list_parser = circuit_subparsers.add_parser(
        "list",
        help="List available circuit templates"
    )
    
    # Circuit create command
    circuit_create_parser = circuit_subparsers.add_parser(
        "create",
        help="Create a new circuit from a template"
    )
    circuit_create_parser.add_argument(
        "template",
        help="Name of the template to use"
    )
    circuit_create_parser.add_argument(
        "--params",
        help="JSON parameters for the template"
    )
    
    # Circuit deploy command
    circuit_deploy_parser = circuit_subparsers.add_parser(
        "deploy",
        help="Deploy a circuit"
    )
    circuit_deploy_parser.add_argument(
        "circuit_id",
        help="ID of the circuit to deploy"
    )
    
    # Web UI command
    webui_parser = subparsers.add_parser(
        "webui",
        help="Start the web UI"
    )
    webui_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to"
    )
    webui_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to"
    )
    
    return parser


def handle_init(args: argparse.Namespace) -> int:
    """
    Handle the init command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        config_dict = {}
        
        if args.data_dir:
            config_dict["system"] = config_dict.get("system", {})
            config_dict["system"]["data_dir"] = args.data_dir
        
        if args.plugin_dir:
            config_dict["system"] = config_dict.get("system", {})
            config_dict["system"]["plugin_dir"] = args.plugin_dir
        
        # Initialize the framework
        core = initialize(args.config, config_dict)
        
        print(f"Initialized Neuron framework with:")
        print(f"  - Data directory: {core.config.get('system', 'data_dir')}")
        print(f"  - Plugin directory: {core.config.get('system', 'plugin_dir')}")
        
        return 0
    except Exception as e:
        logger.error(f"Error initializing framework: {e}")
        return 1


def handle_start(args: argparse.Namespace) -> int:
    """
    Handle the start command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        config_dict = {}
        
        if args.no_plugins:
            config_dict["extensions"] = {"auto_discover": False}
        
        # Start the framework
        core = start(args.config, config_dict)
        
        print(f"Started Neuron framework")
        print(f"Use 'neuron stop' to stop the framework")
        
        # Keep running until interrupted
        try:
            while core.is_running:
                # Sleep briefly to avoid high CPU usage
                import time
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("Received interrupt, shutting down...")
            shutdown()
        
        return 0
    except Exception as e:
        logger.error(f"Error starting framework: {e}")
        return 1


def handle_stop(_: argparse.Namespace) -> int:
    """
    Handle the stop command.
    
    Args:
        _: Command-line arguments (unused)
        
    Returns:
        Exit code
    """
    try:
        # Stop the framework
        shutdown()
        
        print("Stopped Neuron framework")
        
        return 0
    except Exception as e:
        logger.error(f"Error stopping framework: {e}")
        return 1


def handle_status(args: argparse.Namespace) -> int:
    """
    Handle the status command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        core = NeuronCore()
        
        if not core.is_initialized:
            print("Neuron framework is not initialized")
            return 0
        
        if core.is_running:
            print("Neuron framework is running")
        else:
            print("Neuron framework is initialized but not running")
        
        if args.detailed:
            # Get detailed status
            agent_count = len(core.agent_manager.get_all_agents())
            circuit_count = len(core.circuit_designer.get_all_circuits())
            plugin_count = len(core.extension_manager.get_all_plugins())
            
            print(f"  - Agents: {agent_count}")
            print(f"  - Circuits: {circuit_count}")
            print(f"  - Plugins: {plugin_count}")
            
            # Get system metrics if available
            if core.is_running and core.neuro_monitor:
                metrics = core.neuro_monitor.get_metrics("system.*")
                if "system.memory.usage" in metrics:
                    print(f"  - Memory usage: {metrics['system.memory.usage']*100:.1f}%")
                if "system.cpu.usage" in metrics:
                    print(f"  - CPU usage: {metrics['system.cpu.usage']*100:.1f}%")
                if "system.threads.count" in metrics:
                    print(f"  - Thread count: {metrics['system.threads.count']}")
        
        return 0
    except Exception as e:
        logger.error(f"Error getting framework status: {e}")
        return 1


def handle_plugin(args: argparse.Namespace) -> int:
    """
    Handle the plugin command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        core = NeuronCore()
        
        if not core.is_initialized:
            print("Neuron framework is not initialized")
            return 1
        
        if args.plugin_command == "list":
            # List installed plugins
            plugins = core.extension_manager.get_all_plugins()
            
            if not plugins:
                print("No plugins installed")
                return 0
            
            print(f"Installed plugins ({len(plugins)}):")
            for name, plugin in plugins.items():
                metadata = plugin.get_metadata()
                status = "Running" if plugin.is_running() else "Loaded"
                print(f"  - {name} v{metadata.version} ({status})")
                print(f"    {metadata.description}")
                print(f"    Scope: {', '.join(s.value for s in metadata.scope)}")
            
            return 0
            
        elif args.plugin_command == "create":
            # Create a new plugin skeleton
            result = core.extension_manager.create_plugin(
                plugin_name=args.name,
                scope=[args.scope],
                author=args.author,
                description=args.description
            )
            
            print(f"Created plugin skeleton: {args.name}")
            print(f"  - Location: {result['path']}")
            print(f"  - Edit the plugin files to implement your functionality")
            
            return 0
            
        elif args.plugin_command == "install":
            # Install a plugin from a directory
            plugin_path = Path(args.path)
            
            if not plugin_path.exists() or not plugin_path.is_dir():
                print(f"Plugin directory not found: {plugin_path}")
                return 1
            
            # Copy plugin to plugin directory
            import shutil
            plugin_dir = Path(core.config.get("system", "plugin_dir"))
            target_dir = plugin_dir / plugin_path.name
            
            if target_dir.exists():
                print(f"Plugin directory already exists: {target_dir}")
                return 1
            
            shutil.copytree(plugin_path, target_dir)
            
            print(f"Installed plugin: {plugin_path.name}")
            print(f"  - Location: {target_dir}")
            print(f"  - Restart the framework to load the plugin")
            
            return 0
            
        else:
            print(f"Unknown plugin command: {args.plugin_command}")
            return 1
            
    except Exception as e:
        logger.error(f"Error processing plugin command: {e}")
        return 1


def handle_agent(args: argparse.Namespace) -> int:
    """
    Handle the agent command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        core = NeuronCore()
        
        if not core.is_initialized:
            print("Neuron framework is not initialized")
            return 1
        
        if args.agent_command == "list":
            # List available agent types
            agent_types = core.agent_manager.get_all_agent_types()
            
            if not agent_types:
                print("No agent types available")
                return 0
            
            print(f"Available agent types ({len(agent_types)}):")
            for name in sorted(agent_types.keys()):
                print(f"  - {name}")
            
            return 0
            
        elif args.agent_command == "create":
            # Create a new agent instance
            agent_type = core.agent_manager.get_agent_type(args.type)
            
            if not agent_type:
                print(f"Unknown agent type: {args.type}")
                return 1
            
            # Parse agent configuration
            config_params = {}
            if args.config:
                try:
                    config_params = json.loads(args.config)
                except json.JSONDecodeError:
                    print(f"Invalid JSON configuration: {args.config}")
                    return 1
            
            # Create the agent
            from .agent import AgentBuilder, AgentConfig
            
            builder = AgentBuilder(core.agent_manager)
            agent_id = (builder
                      .of_type(agent_type)
                      .with_name(args.name or "")
                      .with_description(args.description or "")
                      .with_config(**config_params)
                      .build())
            
            print(f"Created agent: {agent_id}")
            print(f"  - Type: {args.type}")
            print(f"  - Name: {args.name or '<unnamed>'}")
            
            return 0
            
        else:
            print(f"Unknown agent command: {args.agent_command}")
            return 1
            
    except Exception as e:
        logger.error(f"Error processing agent command: {e}")
        return 1


def handle_circuit(args: argparse.Namespace) -> int:
    """
    Handle the circuit command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        core = NeuronCore()
        
        if not core.is_initialized:
            print("Neuron framework is not initialized")
            return 1
        
        if args.circuit_command == "list":
            # List available circuit templates
            templates = core.circuit_designer.get_all_templates()
            
            if not templates:
                print("No circuit templates available")
                return 0
            
            print(f"Available circuit templates ({len(templates)}):")
            for name, template in templates.items():
                print(f"  - {name}")
                print(f"    {template.description}")
            
            return 0
            
        elif args.circuit_command == "create":
            # Create a new circuit from a template
            template = core.circuit_designer.get_template(args.template)
            
            if not template:
                print(f"Unknown circuit template: {args.template}")
                return 1
            
            # Parse template parameters
            params = {}
            if args.params:
                try:
                    params = json.loads(args.params)
                except json.JSONDecodeError:
                    print(f"Invalid JSON parameters: {args.params}")
                    return 1
            
            # Create the circuit
            circuit_id = core.circuit_designer.create_from_template(
                args.template, params
            )
            
            print(f"Created circuit: {circuit_id}")
            print(f"  - Template: {args.template}")
            print(f"  - Use 'neuron circuit deploy {circuit_id}' to deploy the circuit")
            
            return 0
            
        elif args.circuit_command == "deploy":
            # Deploy a circuit
            circuit = core.circuit_designer.get_circuit(args.circuit_id)
            
            if not circuit:
                print(f"Unknown circuit: {args.circuit_id}")
                return 1
            
            # Deploy the circuit
            core.circuit_designer.deploy_circuit(args.circuit_id)
            
            print(f"Deployed circuit: {args.circuit_id}")
            
            return 0
            
        else:
            print(f"Unknown circuit command: {args.circuit_command}")
            return 1
            
    except Exception as e:
        logger.error(f"Error processing circuit command: {e}")
        return 1


def handle_webui(args: argparse.Namespace) -> int:
    """
    Handle the webui command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code
    """
    try:
        # Check if web UI dependencies are installed
        try:
            import fastapi
            import uvicorn
        except ImportError:
            print("Web UI dependencies not installed")
            print("Install with: pip install fastapi uvicorn jinja2")
            return 1
        
        core = NeuronCore()
        
        if not core.is_initialized:
            print("Neuron framework is not initialized")
            return 1
        
        # Import the web UI module
        try:
            from .web import create_app
        except ImportError:
            print("Web UI module not found")
            return 1
        
        # Create and start the web UI
        app = create_app(core)
        
        print(f"Starting web UI at http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        
        return 0
    except Exception as e:
        logger.error(f"Error starting web UI: {e}")
        return 1


def configure_logging(args: argparse.Namespace) -> None:
    """
    Configure logging based on command-line arguments.
    
    Args:
        args: Command-line arguments
    """
    # Set up logging level
    log_level = getattr(logging, args.log_level.upper())
    
    # Configure handlers
    handlers = []
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    handlers.append(console_handler)
    
    # Add file handler if specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code
    """
    parser = setup_parser()
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(args)
    
    # Handle command
    if args.command == "init":
        return handle_init(args)
    elif args.command == "start":
        return handle_start(args)
    elif args.command == "stop":
        return handle_stop(args)
    elif args.command == "status":
        return handle_status(args)
    elif args.command == "plugin":
        return handle_plugin(args)
    elif args.command == "agent":
        return handle_agent(args)
    elif args.command == "circuit":
        return handle_circuit(args)
    elif args.command == "webui":
        return handle_webui(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
"""
