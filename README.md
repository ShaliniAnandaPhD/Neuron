# Open Source Attribution Notice

Using open source software without proper attribution or in violation of license terms is not only ethically problematic but may also constitute a legal violation ⚠️ . I believe in supporting the open source community that makes projects like this possible.

If you're using code or tools from this repository or GitHub, please ensure you maintain all attribution notices and comply with all applicable licenses.

The license above is a *modified MIT LICENSE* for the purpose of this project 👆


-----------------------------------

# Neuron: A Composable Agent Framework Toolkit

Neuron is a comprehensive framework for building composable AI agent systems inspired by neuroscience principles. It provides tools for creating, deploying, and orchestrating networks of specialized AI agents that can communicate and collaborate to solve complex problems.

## What Neuron Is For

Neuron is a framework for building AI systems that think in circuits—not chains.

It’s designed to create, deploy, and orchestrate networks of specialized agents that can reason over time, adapt to uncertainty, and collaborate through shared memory. Inspired by the modular structure of the brain, Neuron enables agents to specialize, coordinate, and evolve—handling ambiguity, planning across multiple steps, and making decisions with context.

Neuron is ideal for:
- Complex, multi-turn tasks that require memory and adaptation
- Reasoning under ambiguity or conflicting constraints
- Systems where interpretability, modularity, and fallback behavior are critical
- Integrating language models, planning tools, and domain-specific agents into a unified, auditable system

Whether you're building research agents, automated reasoning pipelines, or full microservice-driven applications, Neuron provides the architecture to make them resilient, traceable, and intelligent by design.


## Key Features

- **Agent-Based Architecture**: Compose modular agents with specialized roles (retrieval, planning, synthesis, classification).
- **Dynamic Circuit Composition**: Construct adaptive circuits that re-route tasks based on confidence, ambiguity, or failure.
- **Memory-Driven Reasoning**: Leverage working, episodic, semantic, and procedural memory to guide decisions over time.
- **SynapticBus Communication**: Enable asynchronous, scoped message passing and shared agent context across tasks.
- **Simulation Planning**: Support lookahead reasoning via simulated agent rollouts before committing to a path.
- **Multimodal Token Fusion**: Integrate structured text, vision, and metadata into unified token streams for reasoning.
- **Behavior Arbitration**: Resolve conflicting agent outputs using confidence-weighted voting and fallback logic.
- **Scoped Memory Access**: Query memory selectively based on context relevance and decay thresholds.
- **Reliability-Aware Routing**: Prioritize agent pathways using performance history and trust scores.
- **Comprehensive Monitoring**: Trace execution paths, memory usage, confidence levels, and circuit timing via NeuroMonitor.
- **Extensible Microservices**: Deploy agents and subsystems (e.g. ambiguity resolution, constraint planning) as reusable services.
- **Developer-Friendly Config**: Define and modify circuits, thresholds, and agent policies with YAML templates.


## 🧠 Neuron: Building in Public

Neuron is being developed in public with regular technical posts, architectural updates, and use case demos.

📍 Follow the series on LinkedIn:  
[🔗 Building in Public Series – Neuron Framework](https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-neuronframework-agentreasoning-activity-7327820225213620228-fS8D?utm_source=share&utm_medium=member_desktop&rcm=ACoAAATH3cgBLB3ZhNKdiK83PyAA1KPddyaaY2I)

This includes:

- Modular agent architecture insights  
- Memory system breakdowns  
- Real-world experiments (claim verification, ambiguity resolution, planning)  
- System diagrams and performance benchmarks

## 🧠 Neuron Evaluation Notebook

Over the first four months of development, Neuron was benchmarked across 12 real-world evaluation scenarios—from sarcasm detection and memory persistence to infrastructure degradation and contradiction handling.

The full evaluation results, design notes, and failure mode breakdowns are documented here:  
📘 [Neuron Evaluation Notebook (Notion)](https://shalini-ananda-phd.notion.site/NEURON-EVALUATION-NOTEBOOK-1cec18ea2aa18002b7acf9c1791ca8ea)

These tests explore how Neuron adapts when things break — and what makes modular, brain-inspired AI architectures different from linear pipelines or single-shot tools.


# Neuron's Flagship Product

## NeuronFlow – Using Steven Kotler's Tools to Improve Productivity

Explore how we're integrating neuroscience-based flow state principles into AI orchestration:

🔗 [LinkedIn Post](https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-neuron-llmorchestration-activity-7328159531266441217-jGDa?utm_source=share&utm_medium=member_desktop&rcm=ACoAAATH3cgBLB3ZhNKdiK83PyAA1KPddyaaY2I)


## Other Use Cases:

## 📽️ Neuron in Action — Demo Links & Use Case Walkthroughs

This section collects real-world demonstrations of the Neuron Framework in action. Each post showcases how Neuron orchestrates specialized modules, integrates with Hugging Face models, and adapts across modalities and domains.

### 🔁 Core Demos & Integrations

- **🧠 Hugging Face Integration**  
  Dynamic model selection per module using Hugging Face's task-specific models  
  https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-neuronframework-huggingface-activity-7329640595067428864-lWWl

- **🎛️ Cross-Modal Reasoning**  
  Coordinated image, audio, and text pipelines in one composable framework  
  https://www.linkedin.com/posts/shalinianandaphd_building-in-public-neuron-doing-cross-activity-7329366442720612352-1Wm5

- **🧩 How Neuron Works (Architecture Overview)**  
  Explains modular agents, circuit orchestration, memory layers, and SynapticBus  
  https://www.linkedin.com/posts/shalinianandaphd_building-in-public-how-does-neuron-work-activity-7329348734524252160-X611

- **📊 Neuron Evaluation Notebook**  
  Full performance benchmarks, architecture metrics, and breakdown recovery analysis  
  https://shalini-ananda-phd.notion.site/NEURON-EVALUATION-NOTEBOOK-1cec18ea2aa18002b7acf9c1791ca8ea

---

### 🧠 Real-World Scenarios

- **📞 Customer Support: Multi-Issue Resolution**  
  A customer needs to exchange a sweater and report missing pants — Neuron coordinates agents in parallel  
  https://www.linkedin.com/posts/shalinianandaphd_ai-customerexperience-neuroscienceintech-activity-7310046900240470016-8vs_

- **🌍 Travel Planning with Constraints**  
  Hotels with pools, accessibility features, and dietary restrictions — all handled in parallel  
  https://www.linkedin.com/posts/shalinianandaphd_ai-neuroscienceintech-innovation-activity-7310052197210226688-Gq2s

- **📜 Legal Reasoning with Modular AI**  
  How Neuron enhanced PRISM by managing retrieval, reasoning, and regulation across jurisdictions  
  https://www.linkedin.com/posts/shalinianandaphd_technical-integration-of-prism-activity-7310016308371144704-yGZM

- **📞 Multilingual Customer Service Escalation**  
  Whisper + NLLB + BLOOM used for transcribing, translating, and responding in native language  
  https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-aiobservability-neuronframework-activity-7329305474086920192-SaUJ

- **📉 Crisis Response System (Disaster Scenario)**  
  Resource prioritization during Hurricane Elena with real-time incident escalation  
  https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-modularai-neuronframework-activity-7329308373269598208-u-16

- **📁 Content Analysis & Classification**  
  Cross-language policy document triage using modular perception and reasoning  
  https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-neuronframework-aiobservability-activity-7329312616416235521-SoRw

- **⚖️ Regulatory Compliance (Cross-Border)**  
  Handling jurisdictional conflicts with modular rule logic and memory  
  https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-neuronframework-modularai-activity-7329303216678936577-KSAZ



## **Microservices**

Neuron Micro-Audit Services is a growing library of self-contained diagnostic agents, each designed to detect and repair a specific fragility pattern in LLM-based systems. These modules are plug-and-play, composable, and explainable.

[![🔧 Sanity Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/sanity_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/sanity_check.yml)
[![🧠 Run Ambiguity Audit](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/run_ambiguity_audit.yml/badge.svg)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/run_ambiguity_audit.yml)
[![📦 Verify Microservices Layout](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/verify_microservices_layout.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/verify_microservices_layout.yml)
[![🔬 Basic Neuron Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/basic_neuron_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/basic_neuron_check.yml)
[![📝 Neuron Log Writer](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/neuron_log_writer.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/neuron_log_writer.yml)




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

## 🧠 Neuroscience Foundations

Neuron is inspired by how the brain handles complexity, ambiguity, and adaptation. Each architectural feature reflects a core cognitive function:

- **Specialized Processing Regions → Agent-Based Architecture**  
  Each Neuron agent performs a distinct function (e.g. retrieval, planning, classification), mirroring how brain regions specialize in perception, memory, or action.

- **Hierarchical Information Processing → CircuitDesigner + SynapticBus**  
  Agent circuits are composed hierarchically, allowing progressive refinement from raw input to abstract reasoning through layered agent interaction.

- **Neuroplasticity → ProceduralMemory + BehaviorController**  
  The system adapts over time by updating strategy templates and altering agent routing based on past outcomes and confidence signals.

- **Working Memory and Attention → WorkingMemory + ReliabilityRouter**  
  Agents dynamically prioritize active context and reliable collaborators, simulating attentional focus and transient recall.

- **Predictive Processing → SimulationPlanner + Circuit Re-Routing**  
  Agents simulate potential task outcomes before execution, allowing Neuron to anticipate consequences and adjust plans proactively.

---

##  Evaluation Metrics

To evaluate whether Neuron is suited to your project or research goals, consider the following:

- **Task Complexity Analysis**  
  Are your tasks multi-step, ambiguous, or requiring flexible agent coordination?

- **Emergent Intelligence Metrics**  
  Do you need system-wide reasoning that goes beyond the capabilities of individual models?

- **Resource Efficiency**  
  Is performance a concern—especially with respect to memory usage, latency, or API cost?

- **Robustness and Reliability**  
  Will your system benefit from fallback agents, arbitration of disagreement, and graceful degradation?

- **Development and Maintenance Metrics**  
  How important is modularity, reuse, and the ability to swap agents or reconfigure pipelines without breaking the whole system?

- **Explainability and Control**  
  Do you need clear visibility into decision paths, memory usage, and routing logic to build trust or meet compliance needs?


## Contextual Memory Architecture

Neuron implements a multi-layered contextual memory system that goes beyond simple token accumulation. Instead of relying on ever-larger context windows, we've designed a memory architecture that intelligently persists, evolves, and selectively recalls information.

### Core Memory Components

#### Layered Memory Structure
* **Working Memory** - Handles immediate context and current interaction state
* **Episodic Memory** - Stores sequential events and interaction history
* **Semantic Memory** - Maintains conceptual relationships and knowledge connections
* **Procedural Memory** - Retains action patterns and response strategies

#### Importance-Weighted Memory Decay
* Implements selective forgetting through importance scoring
* Weighs factors including recency, usage frequency, and explicit importance markers
* Preserves critical information while allowing trivial details to fade
* Adapts memory persistence based on contextual relevance

#### Semantic Compression
* Reduces raw conversations to conceptual summaries without losing essence
* Extracts core intents and key information points
* Preserves relationship patterns and preference structures
* Minimizes memory footprint while maintaining contextual integrity

#### Associative Retrieval
* Makes memory searchable rather than using all-or-nothing context windows
* Retrieves specific memories based on semantic relevance
* Implements context-aware search that understands references to past interactions
* Balances recency and relevance in memory retrieval

### Memory Persistence

* **Cross-Session Continuity** - Maintains relevant context between separate interactions
* **Memory Lifecycle Management** - Rules for creation, updating, and deprecation
* **Context Evolution** - Adapts memory representation as new information arrives

## Implementation Design Principles

* **Modular Architecture** - Memory components are separable and independently testable
* **Configurability** - Memory behavior is adjustable through configuration
* **Observability** - Comprehensive logging of memory operations for debugging
* **Efficiency** - Optimized for minimal computational overhead during retrieval


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
