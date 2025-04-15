Open Source Attribution Notice

Using open source software without proper attribution or in violation of license terms is not only ethically problematic but may also constitute a legal violation. I believe in supporting the open source community that makes projects like this possible.

If you're using code or tools from this repository or GitHub, please ensure you maintain all attribution notices and comply with all applicable licenses.

The license above is a modified MIT LICENSE for the purpose of this project 👆


-----------------------------------

# Neuron: A Composable Agent Framework Toolkit

Neuron is a comprehensive framework for building composable AI agent systems inspired by neuroscience principles. It provides tools for creating, deploying, and orchestrating networks of specialized AI agents that can communicate and collaborate to solve complex problems.

## What Neuron Is For

Neuron is designed for creating, deploying, and orchestrating networks of specialized AI agents that can communicate and collaborate to solve complex problems. It draws inspiration from how the human brain works, with different specialized regions cooperating through neural pathways.

## Key Features

- **Agent-Based Architecture**: Create specialized agents with different capabilities and behaviors.
- **Dynamic Composition**: Build complex agent networks using circuit templates and connection patterns.
- **Flexible Communication**: Enable sophisticated agent interactions through the SynapticBus messaging system.
- **Multi-Level Memory**: Implement working, episodic, semantic, and procedural memory systems.
- **Advanced Behavior Control**: Adjust agent behavior dynamically based on context and goals.
- **Comprehensive Monitoring**: Track metrics, visualize system behavior, and detect issues.
- **Extensible Design**: Enhance functionality through plugins and custom components.

## Use Cases:

1) [The demo tackles a travel planning scenario with overlapping requirements - a family needs hotels with pools that are also accessible for mobility issues, while staying within budget and accommodating dietary restrictions](https://www.linkedin.com/posts/shalinianandaphd_ai-neuroscienceintech-innovation-activity-7310052197210226688-Gq2s?utm_source=share&utm_medium=member_desktop&rcm=ACoAAATH3cgBLB3ZhNKdiK83PyAA1KPddyaaY2I)

2) [Neuron handling Customer Support: The scenario: A customer has two problems - wrong-sized sweater and missing pants from the same order](https://www.linkedin.com/posts/shalinianandaphd_ai-customerexperience-neuroscienceintech-activity-7310046900240470016-8vs_?utm_source=share&utm_medium=member_desktop&rcm=ACoAAATH3cgBLB3ZhNKdiK83PyAA1KPddyaaY2I)

3) [Modular Reasoning Systems: Exploring how modular architectures can enhance the reliability and performance of legal AI systems](https://www.linkedin.com/posts/shalinianandaphd_technical-integration-of-prism-activity-7310016308371144704-yGZM?utm_source=share&utm_medium=member_desktop&rcm=ACoAAATH3cgBLB3ZhNKdiK83PyAA1KPddyaaY2I)


## **Microservices**

[![🔧 Sanity Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/sanity_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/sanity_check.yml)
[![🧠 Run Ambiguity Audit](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/run_ambiguity_audit.yml/badge.svg)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/run_ambiguity_audit.yml)


## Installation

```bash
# Clone the repository
git clone https://github.com/neuron-framework/neuron.git
cd neuron

# Install the package
pip install -e .
```

## Quick Start

### Initializing the Framework

```python
from neuron import initialize, start

# Initialize the framework
core = initialize()

# Start the framework
start()
```

### Creating a Simple Agent

```python
from neuron import create_agent, ReflexAgent

# Create a reflex agent
agent_id = create_agent(ReflexAgent, name="MyAgent", description="A simple agent")

# Get the agent
agent = core.agent_manager.get_agent(agent_id)
```

### Building a Circuit

```python
from neuron import CircuitDefinition

# Define a circuit
circuit_def = CircuitDefinition.create(
    name="SimpleCircuit",
    description="A simple processing circuit",
    agents={
        "input": {
            "type": "ReflexAgent",
            "role": "INPUT",
            "name": "Input Agent"
        },
        "processor": {
            "type": "DeliberativeAgent",
            "role": "PROCESSOR",
            "name": "Processor Agent"
        },
        "output": {
            "type": "ReflexAgent",
            "role": "OUTPUT",
            "name": "Output Agent"
        }
    },
    connections=[
        {
            "source": "input",
            "target": "processor",
            "connection_type": "direct"
        },
        {
            "source": "processor",
            "target": "output",
            "connection_type": "direct"
        }
    ]
)

# Create and deploy the circuit
circuit_id = core.circuit_designer.create_circuit(circuit_def)
core.circuit_designer.deploy_circuit(circuit_id)

# Send input to the circuit
core.circuit_designer.send_input(circuit_id, {"data": "Hello, world!"})
```

## Core Components

Neuron is comprised of several key components that work together to create a flexible and powerful agent framework:

### NeuronCore

The central coordinator for the framework, responsible for initializing and managing all components.

```python
from neuron import NeuronCore

# Get the singleton instance
core = NeuronCore()
```

### Agents

Specialized processing units that can receive and send messages, perform tasks, and learn from experience.

```python
# Create different types of agents
reflex_agent = create_agent(ReflexAgent)
deliberative_agent = create_agent(DeliberativeAgent)
learning_agent = create_agent(LearningAgent)
coordinator_agent = create_agent(CoordinatorAgent)
```

### Memory Systems

Different types of memory for storing and retrieving information.

```python
# Access different memory types
working_memory = core.memory_manager.get_memory_system(MemoryType.WORKING)
episodic_memory = core.memory_manager.get_memory_system(MemoryType.EPISODIC)
semantic_memory = core.memory_manager.get_memory_system(MemoryType.SEMANTIC)
```

### SynapticBus

Communication system that enables message exchange between agents.

```python
# Send a message
message = Message.create(
    sender="agent1",
    recipients=["agent2"],
    content={"data": "Hello"}
)
await core.synaptic_bus.send(message)
```

### CircuitDesigner

Tool for creating and managing networks of agents.

```python
# Create a circuit from a template
circuit_id = await core.circuit_designer.create_from_template(
    "sequential_pipeline",
    {
        "processor1_type": "DeliberativeAgent",
        "processor2_type": "LearningAgent"
    }
)
```

### Behavior Control

System for dynamically adjusting agent behavior.

```python
from neuron import BehaviorTrait, with_behavior_control

# Enhance an agent with behavior control
EnhancedAgent = with_behavior_control(ReflexAgent)
agent = EnhancedAgent()

# Adjust behavior traits
agent.get_behavior_controller().set_trait(BehaviorTrait.CURIOSITY, 0.8)
```

### Monitoring

System for tracking metrics and diagnosing issues.

```python
# Get system metrics
metrics = core.neuro_monitor.get_metrics("system.*")

# Check health status
health = core.neuro_monitor.get_health_status()
```

## Command-Line Interface

Neuron includes a command-line interface for managing the framework:

```bash
# Initialize the framework
neuron init

# Start the framework
neuron start

# View status
neuron status --detailed

# List available agent types
neuron agent list

# Create a circuit from a template
neuron circuit create sequential_pipeline --params '{"processor1_type": "DeliberativeAgent"}'
```

## Neuroscience Foundations

Neuron incorporates several principles from neuroscience:

- **Specialized Processing Regions**: Agents with specific capabilities, like brain regions.
- **Hierarchical Information Processing**: Circuit composition for progressive refinement.
- **Neuroplasticity**: Learning and adaptation from experience.
- **Working Memory and Attention**: Prioritization of information for processing.
- **Predictive Processing**: Anticipation of inputs and outcomes.

## Evaluation Metrics

To determine if Neuron is right for your use case, consider these metrics:

- **Task Complexity Analysis**: How complex are the problems you need to solve?
- **Emergent Intelligence Metrics**: Do you need system-level capabilities beyond individual agents?
- **Resource Efficiency**: How important are memory and CPU requirements?
- **Robustness and Reliability**: What level of fault tolerance do you need?
- **Development and Maintenance Metrics**: How much customization will you need?
- **Explainability and Control**: How important is understanding the system's decisions?

## Examples

Check the `examples/` directory for detailed demonstrations of Neuron's capabilities:

- `simple_agent.py`: Basic agent creation and usage
- `memory_system.py`: Working with different memory types
- `agent_communication.py`: Message passing between agents
- `circuit_creation.py`: Building and deploying circuits
- `behavior_control.py`: Adjusting agent behavior dynamically
- `plugin_development.py`: Creating a custom plugin

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

## License

Neuron is released under the MIT License. See `LICENSE` for details.
