
"""
Neuron Framework Setup Script
Automatically creates the project structure and sets up the environment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def create_project_structure():
    """Create the complete Neuron framework directory structure"""
    
    structure = {
        "neuron": {
            "__init__.py": '''"""Neuron Framework - Advanced Neural Coordination System"""
__version__ = "0.1.0"
__author__ = "Neuron Team"

from .core.base import BaseAgent, Message, MessageType, MessagePriority
from .core.messaging import SynapticBus
from .agents.deliberative_agent import DeliberativeAgent
from .memory.working import WorkingMemory

__all__ = [
    'BaseAgent', 'Message', 'MessageType', 'MessagePriority',
    'SynapticBus', 'DeliberativeAgent', 'WorkingMemory'
]
''',
            "core": {
                "__init__.py": "# Core framework components",
                # Files will be created by user from artifacts
            },
            "agents": {
                "__init__.py": "# Agent implementations",
            },
            "circuits": {
                "__init__.py": "# Circuit management",
                "circuit.py": '''"""Circuit management placeholder"""
# TODO: Implement circuit topology management
''',
            },
            "memory": {
                "__init__.py": "# Memory systems",
            },
            "utils": {
                "__init__.py": "# Utility functions",
                "colors.py": '''"""Color utilities for console output"""

class Colors:
    # ANSI color codes
    BLACK = '\\033[30m'
    RED = '\\033[31m'
    GREEN = '\\033[32m'
    YELLOW = '\\033[33m'
    BLUE = '\\033[34m'
    MAGENTA = '\\033[35m'
    CYAN = '\\033[36m'
    WHITE = '\\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\\033[90m'
    BRIGHT_RED = '\\033[91m'
    BRIGHT_GREEN = '\\033[92m'
    BRIGHT_YELLOW = '\\033[93m'
    BRIGHT_BLUE = '\\033[94m'
    BRIGHT_MAGENTA = '\\033[95m'
    BRIGHT_CYAN = '\\033[96m'
    BRIGHT_WHITE = '\\033[97m'
    
    # Styles
    BOLD = '\\033[1m'
    DIM = '\\033[2m'
    UNDERLINE = '\\033[4m'
    RESET = '\\033[0m'
    
    @classmethod
    def colored(cls, text: str, color: str) -> str:
        """Return colored text"""
        return f"{color}{text}{cls.RESET}"
''',
            }
        },
        "examples": {
            "__init__.py": "",
            "basic_circuit": {
                "__init__.py": "",
                # simple_demo.py will be created from artifact
            },
        },
        "tests": {
            "__init__.py": "",
            "test_basic.py": '''"""Basic tests for Neuron framework"""
import pytest
import asyncio
from neuron.core.base import Message, MessageType, MessagePriority
from neuron.core.messaging import SynapticBus
from neuron.agents.deliberative_agent import DeliberativeAgent

def test_message_creation():
    """Test basic message creation"""
    msg = Message(
        type=MessageType.REQUEST,
        priority=MessagePriority.NORMAL,
        sender_id="test_sender",
        recipient_id="test_recipient",
        content={"test": "data"}
    )
    
    assert msg.type == MessageType.REQUEST
    assert msg.priority == MessagePriority.NORMAL
    assert msg.sender_id == "test_sender"
    assert msg.recipient_id == "test_recipient"
    assert msg.content["test"] == "data"

@pytest.mark.asyncio
async def test_agent_creation():
    """Test basic agent creation"""
    agent = DeliberativeAgent("test_agent")
    assert agent.agent_id == "test_agent"
    assert agent.is_healthy()

@pytest.mark.asyncio  
async def test_synaptic_bus():
    """Test basic synaptic bus functionality"""
    bus = SynapticBus()
    agent = DeliberativeAgent("test_agent")
    
    # Register agent
    success = bus.register_agent(agent)
    assert success
    
    # Check agent is registered
    retrieved_agent = bus.get_agent("test_agent")
    assert retrieved_agent == agent
''',
        },
        "docs": {
            "README.md": '''# Neuron Framework Documentation

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the basic demo:
   ```bash
   python examples/basic_circuit/simple_demo.py
   ```

3. Try the interactive demo:
   ```bash
   python examples/basic_circuit/simple_demo.py --mode interactive
   ```

## Architecture

The Neuron framework consists of:
- **Agents**: Autonomous components with reasoning capabilities
- **SynapticBus**: Message routing and communication system
- **Memory Systems**: Various types of memory for information storage
- **Circuits**: Networks of connected agents

## Examples

See the `examples/` directory for working demonstrations.
''',
        },
        "requirements.txt": '''# Core dependencies
asyncio
dataclasses; python_version < "3.7"

# Optional dependencies  
PyYAML>=6.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0

# Development dependencies
black>=23.0.0
mypy>=1.5.0
''',
    }
    
    def create_structure(base_path: Path, structure: dict):
        """Recursively create directory structure"""
        for name, content in structure.items():
            if isinstance(content, dict):
                # Directory
                dir_path = base_path / name
                dir_path.mkdir(exist_ok=True)
                print(f"📁 Created directory: {dir_path}")
                create_structure(dir_path, content)
            else:
                # File
                file_path = base_path / name
                if not file_path.exists():
                    file_path.write_text(content)
                    print(f"📄 Created file: {file_path}")
                else:
                    print(f"⚠️  File exists: {file_path}")
    
    print("🚀 Creating Neuron Framework project structure...")
    base_path = Path(".")
    create_structure(base_path, structure)
    
    return True

def create_run_script():
    """Create a simple run script"""
    run_script = '''#!/usr/bin/env python3
"""
Neuron Framework - Quick Start Script
"""

import sys
import os

def main():
    print("🧠 Neuron Framework")
    print("==================")
    print()
    print("Available commands:")
    print("  demo     - Run basic demonstration")
    print("  interactive - Run interactive demo")
    print("  test     - Run tests")
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python run.py [command]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "demo":
        os.system("python examples/basic_circuit/simple_demo.py")
    elif command == "interactive":
        os.system("python examples/basic_circuit/simple_demo.py --mode interactive")
    elif command == "test":
        os.system("python -m pytest tests/ -v")
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
'''
    
    with open("run.py", "w") as f:
        f.write(run_script)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod("run.py", 0o755)
    
    print("📄 Created run.py script")

def install_dependencies():
    """Install required dependencies"""
    try:
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True, text=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        print("You can install manually with: pip install -r requirements.txt")
        return False

def create_example_config():
    """Create example configuration files"""
    configs_dir = Path("configs")
    configs_dir.mkdir(exist_ok=True)
    
    # Basic configuration
    basic_config = '''# Neuron Framework Configuration
system:
  log_level: INFO
  max_agents: 50
  message_timeout: 30

messaging:
  max_queue_size: 1000
  retry_attempts: 3
  compression: false

memory:
  working_memory_size: 1000
  default_ttl: 3600
  
agents:
  default_confidence_threshold: 0.7
  max_concurrent_tasks: 5
'''
    
    with open(configs_dir / "basic.yaml", "w") as f:
        f.write(basic_config)
    
    print("📄 Created configs/basic.yaml")

def check_environment():
    """Check if the environment is suitable"""
    print("🔍 Checking environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ required, found {sys.version}")
        return False
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Check if pip is available
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✅ pip is available")
    except subprocess.CalledProcessError:
        print("❌ pip is not available")
        return False
    
    return True

def provide_next_steps():
    """Provide guidance on next steps"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETE!")
    print("="*60)
    print()
    print("📋 Next Steps:")
    print()
    print("1. 📄 Create the core implementation files:")
    print("   Copy the code from the artifacts into these files:")
    print("   • neuron/core/base.py")
    print("   • neuron/core/messaging.py") 
    print("   • neuron/memory/working.py")
    print("   • neuron/agents/deliberative_agent.py")
    print("   • examples/basic_circuit/simple_demo.py")
    print()
    print("2. 🧪 Test the installation:")
    print("   python run.py test")
    print()
    print("3. 🚀 Run the demo:")
    print("   python run.py demo")
    print()
    print("4. 🎯 Try interactive mode:")
    print("   python run.py interactive")
    print()
    print("5. 📚 Read the documentation:")
    print("   Check docs/README.md for more information")
    print()
    print("🔗 Need help? Check the artifacts in the conversation above!")

def main():
    """Main setup function"""
    print("🧠 Neuron Framework Setup")
    print("=========================")
    print()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed")
        sys.exit(1)
    
    # Create project structure
    if not create_project_structure():
        print("❌ Failed to create project structure")
        sys.exit(1)
    
    # Create additional files
    create_run_script()
    create_example_config()
    
    # Install dependencies (optional)
    install_choice = input("\n📦 Install dependencies now? (y/n): ").lower().strip()
    if install_choice in ['y', 'yes']:
        install_dependencies()
    else:
        print("⚠️  Remember to install dependencies later with: pip install -r requirements.txt")
    
    # Provide next steps
    provide_next_steps()

if __name__ == "__main__":
    main()
