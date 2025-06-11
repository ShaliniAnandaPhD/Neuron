"""
Neuron Framework: Project Structure Setup Script
Creates the complete directory structure and initial files for the Neuron framework
"""

import os
import json
from pathlib import Path

def create_neuron_project_structure():
    """Create the complete Neuron framework directory structure"""
    
    # Define the project structure
    structure = {
        "neuron/": {
            "__init__.py": "",
            "core/": {
                "__init__.py": "",
                "base.py": "# Base classes: BaseAgent, Message, etc.",
                "memory.py": "# Memory systems implementation",
                "messaging.py": "# SynapticBus and message routing",
                "monitoring.py": "# NeuroMonitor and observability",
                "config.py": "# Configuration management"
            },
            "agents/": {
                "__init__.py": "",
                "base_agent.py": "# BaseAgent implementation",
                "reflex_agent.py": "# ReflexAgent implementation", 
                "deliberative_agent.py": "# DeliberativeAgent implementation",
                "learning_agent.py": "# LearningAgent implementation",
                "coordinator_agent.py": "# CoordinatorAgent implementation"
            },
            "circuits/": {
                "__init__.py": "",
                "circuit.py": "# Circuit topology and management",
                "builder.py": "# Circuit builder utilities",
                "templates.py": "# Pre-built circuit templates"
            },
            "memory/": {
                "__init__.py": "",
                "working.py": "# Working memory implementation",
                "episodic.py": "# Episodic memory implementation",
                "semantic.py": "# Semantic memory implementation",
                "procedural.py": "# Procedural memory implementation",
                "emotional.py": "# Emotional memory implementation"
            },
            "utils/": {
                "__init__.py": "",
                "logging.py": "# Enhanced logging utilities",
                "serialization.py": "# State serialization",
                "metrics.py": "# Performance metrics",
                "validation.py": "# Input validation"
            }
        },
        "examples/": {
            "__init__.py": "",
            "kotler_flow/": {
                "__init__.py": "",
                "demo.py": "# Kotler flow demonstration",
                "config.yaml": "# Kotler circuit configuration"
            },
            "fault_injection/": {
                "__init__.py": "",
                "demo.py": "# Fault injection demonstration",
                "scenarios.py": "# Fault scenarios"
            },
            "basic_circuit/": {
                "__init__.py": "",
                "simple_demo.py": "# Basic 3-agent circuit"
            }
        },
        "tests/": {
            "__init__.py": "",
            "unit/": {
                "__init__.py": "",
                "test_agents.py": "# Agent unit tests",
                "test_memory.py": "# Memory system tests",
                "test_messaging.py": "# Message routing tests"
            },
            "integration/": {
                "__init__.py": "",
                "test_circuits.py": "# Circuit integration tests",
                "test_kotler_flow.py": "# Kotler demo tests"
            },
            "fixtures/": {
                "__init__.py": "",
                "sample_configs.py": "# Test configurations"
            }
        },
        "docs/": {
            "api/": {},
            "tutorials/": {},
            "examples/": {},
            "architecture.md": "# Architecture documentation"
        },
        "configs/": {
            "default.yaml": "# Default system configuration",
            "kotler_flow.yaml": "# Kotler flow circuit config",
            "fault_injection.yaml": "# Fault injection config"
        },
        "logs/": {},
        "requirements.txt": "# Python dependencies",
        "setup.py": "# Package setup",
        "README.md": "# Project README",
        "pyproject.toml": "# Modern Python project config"
    }
    
    def create_structure(base_path: Path, structure: dict):
        """Recursively create directory structure"""
        for name, content in structure.items():
            if name.endswith("/"):
                # It's a directory
                dir_path = base_path / name.rstrip("/")
                dir_path.mkdir(exist_ok=True)
                print(f"📁 Created directory: {dir_path}")
                
                if isinstance(content, dict):
                    create_structure(dir_path, content)
            else:
                # It's a file
                file_path = base_path / name
                if not file_path.exists():
                    file_path.write_text(content)
                    print(f"📄 Created file: {file_path}")
                else:
                    print(f"⚠️  File exists: {file_path}")
    
    # Create the structure
    print("🚀 Creating Neuron Framework project structure...")
    base_path = Path(".")
    create_structure(base_path, structure)
    
    # Create specific configuration files
    create_config_files()
    create_setup_files()
    create_readme()
    
    print("\n✅ Project structure created successfully!")
    print("\n📂 Your project now has this structure:")
    print_tree(".", max_depth=3)

def create_config_files():
    """Create configuration files"""
    
    # Default configuration
    default_config = {
        "system": {
            "log_level": "INFO",
            "max_agents": 50,
            "message_timeout": 30,
            "memory_capacity": 10000
        },
        "messaging": {
            "max_queue_size": 1000,
            "retry_attempts": 3,
            "compression": True
        },
        "monitoring": {
            "metrics_enabled": True,
            "trace_enabled": True,
            "export_prometheus": False
        }
    }
    
    # Kotler flow configuration
    kotler_config = {
        "circuit": {
            "name": "kotler_flow",
            "description": "Kotler flow optimization circuit",
            "agents": [
                {
                    "id": "cognitive_detector",
                    "type": "DeliberativeAgent",
                    "capabilities": ["flow_detection", "pattern_analysis"],
                    "memory_types": ["working", "episodic"]
                },
                {
                    "id": "neural_bus",
                    "type": "MessageRouter",
                    "capabilities": ["routing", "load_balancing"],
                    "memory_types": ["working"]
                },
                {
                    "id": "memory_controller",
                    "type": "DeliberativeAgent", 
                    "capabilities": ["memory_management", "retrieval"],
                    "memory_types": ["working", "episodic", "semantic"]
                },
                {
                    "id": "decision_engine",
                    "type": "DeliberativeAgent",
                    "capabilities": ["decision_making", "optimization"],
                    "memory_types": ["working", "procedural"]
                },
                {
                    "id": "adaptation_controller",
                    "type": "LearningAgent",
                    "capabilities": ["adaptation", "learning"],
                    "memory_types": ["working", "procedural", "emotional"]
                },
                {
                    "id": "coordination_hub",
                    "type": "CoordinatorAgent",
                    "capabilities": ["coordination", "orchestration"],
                    "memory_types": ["working", "episodic"]
                }
            ],
            "connections": [
                {"from": "cognitive_detector", "to": "neural_bus"},
                {"from": "neural_bus", "to": "memory_controller"},
                {"from": "memory_controller", "to": "decision_engine"},
                {"from": "decision_engine", "to": "adaptation_controller"},
                {"from": "adaptation_controller", "to": "coordination_hub"},
                {"from": "coordination_hub", "to": "cognitive_detector"}
            ]
        }
    }
    
    # Write configuration files
    os.makedirs("configs", exist_ok=True)
    
    with open("configs/default.yaml", "w") as f:
        import yaml
        try:
            yaml.dump(default_config, f, default_flow_style=False)
        except ImportError:
            # Fallback to JSON if PyYAML not available
            f.write("# Install PyYAML for YAML support\n")
            f.write(f"# JSON equivalent:\n# {json.dumps(default_config, indent=2)}")
    
    with open("configs/kotler_flow.yaml", "w") as f:
        try:
            yaml.dump(kotler_config, f, default_flow_style=False)
        except ImportError:
            f.write("# Install PyYAML for YAML support\n")
            f.write(f"# JSON equivalent:\n# {json.dumps(kotler_config, indent=2)}")

def create_setup_files():
    """Create setup and requirements files"""
    
    # requirements.txt
    requirements = """# Core dependencies
pydantic>=2.0.0
asyncio-mqtt>=0.11.0
aiofiles>=23.0.0
click>=8.0.0

# Optional dependencies  
PyYAML>=6.0.0
prometheus-client>=0.17.0
opentelemetry-api>=1.20.0

# Development dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=23.0.0
mypy>=1.5.0
"""
    
    with open("requirements.txt", "w") as f:
        f.write(requirements)
    
    # setup.py
    setup_py = '''#!/usr/bin/env python3
"""
Neuron Framework Setup
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="neuron-framework",
    version="0.1.0", 
    author="Neuron Team",
    author_email="team@neuron-framework.ai",
    description="Advanced Neural Coordination Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/neuron-framework",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": ["pytest>=7.0.0", "black>=23.0.0", "mypy>=1.5.0"],
        "monitoring": ["prometheus-client>=0.17.0", "opentelemetry-api>=1.20.0"],
        "full": ["PyYAML>=6.0.0", "prometheus-client>=0.17.0", "opentelemetry-api>=1.20.0"],
    },
    entry_points={
        "console_scripts": [
            "neuron=neuron.cli:main",
        ],
    },
)
'''
    
    with open("setup.py", "w") as f:
        f.write(setup_py)
    
    # pyproject.toml
    pyproject = '''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "neuron-framework"
version = "0.1.0"
description = "Advanced Neural Coordination Framework"
authors = [{name = "Neuron Team", email = "team@neuron-framework.ai"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.8"
keywords = ["ai", "agents", "neural", "coordination", "memory"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers", 
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
]

[project.urls]
Homepage = "https://github.com/your-org/neuron-framework"
Documentation = "https://neuron-framework.readthedocs.io/"
Repository = "https://github.com/your-org/neuron-framework.git"
Issues = "https://github.com/your-org/neuron-framework/issues"

[tool.black]
line-length = 88
target-version = ['py38']

[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
'''
    
    with open("pyproject.toml", "w") as f:
        f.write(pyproject)

def create_readme():
    """Create project README"""
    
    readme = '''# Neuron Framework

Advanced Neural Coordination Framework with multi-agent architecture, memory systems, and fault tolerance.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Kotler flow demonstration
python -m examples.kotler_flow.demo

# Run fault injection testing  
python -m examples.fault_injection.demo

# Start interactive mode
python -c "from neuron import NeuroCircuit; circuit = NeuroCircuit.load('configs/kotler_flow.yaml'); circuit.start()"
```

## 🏗️ Architecture

The Neuron framework provides:

- **Multi-Agent Coordination**: 6 specialized agents working together
- **Memory Systems**: Working, episodic, semantic, procedural, and emotional memory
- **Fault Tolerance**: Automatic recovery and healing mechanisms  
- **Real-time Monitoring**: Complete observability and metrics
- **Circuit Templates**: Pre-built patterns for common use cases

## 📂 Project Structure

```
neuron/
├── core/           # Core framework components
├── agents/         # Agent implementations
├── circuits/       # Circuit management
├── memory/         # Memory systems
└── utils/          # Utilities

examples/           # Example circuits and demos
tests/             # Test suite
configs/           # Configuration files
docs/              # Documentation
```

## 🧠 Core Concepts

### Agents
- **BaseAgent**: Foundation for all agents
- **ReflexAgent**: Simple stimulus-response behavior
- **DeliberativeAgent**: Complex reasoning and planning
- **LearningAgent**: Adaptive behavior with experience
- **CoordinatorAgent**: Multi-agent orchestration

### Memory Systems
- **Working Memory**: Short-term active information
- **Episodic Memory**: Event sequences and experiences
- **Semantic Memory**: Knowledge and facts
- **Procedural Memory**: Skills and procedures
- **Emotional Memory**: Affective states and associations

### Circuits
- **Sequential**: Linear agent chains
- **Parallel**: Concurrent processing
- **Hierarchical**: Multi-level coordination
- **Dynamic**: Runtime reconfiguration

## 🔬 Examples

### Basic Circuit
```python
from neuron import NeuroCircuit, DeliberativeAgent

# Create agents
detector = DeliberativeAgent("detector", capabilities=["analysis"])
processor = DeliberativeAgent("processor", capabilities=["processing"])
responder = DeliberativeAgent("responder", capabilities=["response"])

# Create circuit
circuit = NeuroCircuit()
circuit.add_agent(detector)
circuit.add_agent(processor) 
circuit.add_agent(responder)

# Connect agents
circuit.connect(detector, processor)
circuit.connect(processor, responder)

# Process message
result = circuit.process("Analyze this situation")
```

### Kotler Flow Optimization
```python
from neuron.circuits import KotlerFlowCircuit

# Load pre-configured Kotler circuit
circuit = KotlerFlowCircuit.from_config("configs/kotler_flow.yaml")

# Run flow analysis
flow_result = circuit.optimize_flow(
    user_profile={"stress": 3, "challenge": 7, "skill": 5},
    context="work_task"
)

print(f"Flow optimization: {flow_result.improvement}%")
```

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests  
python -m pytest tests/integration/

# Run specific test
python -m pytest tests/unit/test_agents.py::test_base_agent
```

## 📊 Monitoring

The framework includes comprehensive monitoring:

- **Real-time Metrics**: Agent performance, memory usage, message throughput
- **Trace Logging**: Complete execution paths and decision points
- **Health Monitoring**: System health scores and alerts
- **Fault Detection**: Automatic issue detection and recovery

## 🔧 Development

```bash
# Install in development mode
pip install -e .

# Format code
black neuron/ examples/ tests/

# Type checking
mypy neuron/

# Run full test suite
python -m pytest
```

## 📖 Documentation

- [Architecture Guide](docs/architecture.md)
- [API Reference](docs/api/)
- [Tutorial Series](docs/tutorials/)
- [Examples](docs/examples/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with inspiration from cognitive science, neuroscience, and distributed systems research.
'''
    
    with open("README.md", "w") as f:
        f.write(readme)

def print_tree(directory, max_depth=3, current_depth=0):
    """Print directory tree structure"""
    if current_depth >= max_depth:
        return
    
    items = []
    try:
        for item in sorted(os.listdir(directory)):
            if item.startswith('.'):
                continue
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                items.append((item + "/", True))
            else:
                items.append((item, False))
    except PermissionError:
        return
    
    for i, (item, is_dir) in enumerate(items):
        is_last = i == len(items) - 1
        prefix = "└── " if is_last else "├── "
        print("    " * current_depth + prefix + item)
        
        if is_dir and current_depth < max_depth - 1:
            item_path = os.path.join(directory, item.rstrip("/"))
            print_tree(item_path, max_depth, current_depth + 1)

if __name__ == "__main__":
    create_neuron_project_structure()
    
    print("\n🎯 Next Steps:")
    print("1. cd into your project directory")
    print("2. Run: pip install -r requirements.txt")
    print("3. Start implementing: neuron/core/base.py")
    print("4. Test your setup: python -m pytest tests/")
    print("\n📖 See README.md for detailed instructions!")
