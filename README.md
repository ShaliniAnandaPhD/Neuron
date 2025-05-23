# Open Source Attribution Notice

Using open source software without proper attribution or in violation of license terms is not only ethically problematic but may also constitute a legal violation ⚠️ . I believe in supporting the open source community that makes projects like this possible.

If you're using code or tools from this repository or GitHub, please ensure you maintain all attribution notices and comply with all applicable licenses.

The license above is a *modified MIT LICENSE* for the purpose of this project 👆


-----------------------------------

# Neuron: A Brain-Inspired AI Framework for Complex Reasoning

[![🔧 Sanity Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/sanity_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/sanity_check.yml)
[![🧠 Run Ambiguity Audit](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/run_ambiguity_audit.yml/badge.svg)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/run_ambiguity_audit.yml)
[![📦 Verify Microservices Layout](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/verify_microservices_layout.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/verify_microservices_layout.yml)

> **Neuron is a composable AI framework that thinks in circuits, not chains.**

Traditional AI orchestration tools collapse under real-world complexity—contradictions, sarcasm, conflicting goals, or mixed data formats. Neuron addresses these breakdown zones through **modular reasoning circuits** inspired by how the brain actually processes information.

```
┌─────────────────────────────────────────┐
│            NEURON ARCHITECTURE          │
└─────────────────────────────────────────┘
               │
┌──────────────┬─────────┼─────────┬──────────────┐
│              │         │         │              │
▼              ▼         ▼         ▼              ▼
┌──────────┐ ┌─────────┐ ┌───────┐ ┌─────────┐ ┌─────────┐
│Perception│ │ Memory  │ │Synaptic│ │Reasoning│ │Expression│
│ Modules  │ │ System  │ │  Bus   │ │ Modules │ │ Modules │
│          │ │         │ │       │ │         │ │         │
│• Language│◄►│• Episodic│◄►│ Coord │◄►│• Logic  │◄►│• Response│
│• Vision  │ │• Semantic│ │ Layer │ │• Planning│ │• Adapt   │
│• Audio   │ │• Working │ │       │ │• Temporal│ │• Format  │
│• Multi.. │ │• Context │ │       │ │• Causal  │ │• Tone    │
└──────────┘ └─────────┘ └───────┘ └─────────┘ └─────────┘
               │                           │
               ▼                           ▼
    ┌──────────────────┐      ┌──────────────────┐
    │ Self-Monitoring  │      │  Adaptability    │
    │                  │      │                  │
    │• Error Detection │      │• Dynamic Routing │
    │• Uncertainty     │      │• Context Shift   │
    │• Explanation     │      │• Resource Alloc  │
    └──────────────────┘      └──────────────────┘
```

## 🧠 Why Neuron?

**For Complex, Real-World AI Systems Where Failure Isn't an Option**

Neuron excels in scenarios traditional AI struggles with:

- **🔄 Resilient Processing**: Handles ambiguous inputs, contradictory information, and incomplete data without system failure
- **🧠 Persistent Memory**: Maintains context across extended interactions for longitudinal reasoning
- **⚡ Selective Activation**: Dynamically combines only needed capabilities rather than running every component
- **🔀 Parallel Coordination**: Processes multiple tasks simultaneously while maintaining consistency
- **👁️ Complete Observability**: Every decision is traceable with full reasoning paths and evidence trails

### Where Neuron Shines

| Use Case | Traditional AI | Neuron Approach |
|----------|---------------|-----------------|
| **Contradictory Customer Requests** | Fails or picks one instruction | Detects contradiction, requests clarification |
| **Multi-Session Medical History** | Loses context between visits | Maintains episodic memory with temporal reasoning |
| **Emergency Response Triage** | Static rule-based priority | Dynamic multi-modal assessment with uncertainty scoring |
| **Regulatory Compliance** | Rigid rule checking | Contextual interpretation with jurisdiction conflict resolution |

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/ShaliniAnandaPhD/Neuron.git
cd Neuron
pip install -e .
```

### Your First Neural Circuit

```python
from neuron import initialize, create_agent, CircuitDefinition
from neuron.agents import ReflexAgent, DeliberativeAgent

# Initialize the framework
core = initialize()

# Define a simple reasoning circuit
circuit_def = CircuitDefinition.create(
    name="CustomerSupportCircuit",
    description="Handles complex customer issues with memory",
    agents={
        "intake": {
            "type": "ReflexAgent",
            "role": "INPUT",
            "capabilities": ["sentiment_analysis", "intent_detection"]
        },
        "reasoner": {
            "type": "DeliberativeAgent", 
            "role": "PROCESSOR",
            "capabilities": ["contradiction_detection", "memory_retrieval"]
        },
        "responder": {
            "type": "ReflexAgent",
            "role": "OUTPUT",
            "capabilities": ["response_generation", "tone_adaptation"]
        }
    },
    connections=[
        {"source": "intake", "target": "reasoner", "type": "direct"},
        {"source": "reasoner", "target": "responder", "type": "conditional"}
    ]
)

# Deploy and test
circuit_id = core.circuit_designer.create_circuit(circuit_def)
core.circuit_designer.deploy_circuit(circuit_id)

# Process a complex request
response = core.circuit_designer.send_input(circuit_id, {
    "customer_id": "12345",
    "message": "I love this product but it's completely broken and I want a refund but also keep it",
    "context": "third_complaint_this_month"
})

print(response)  # Neuron detects contradiction and requests clarification
```

## 🏗️ Core Architecture

### Agent Types

Neuron provides specialized agents for different cognitive functions:

```python
# Quick response agents
reflex_agent = create_agent(ReflexAgent, 
    name="IntakeAgent",
    capabilities=["sentiment_analysis", "classification"])

# Deep reasoning agents  
deliberative_agent = create_agent(DeliberativeAgent,
    name="ReasoningAgent", 
    capabilities=["logical_inference", "contradiction_detection"])

# Learning and adaptation agents
learning_agent = create_agent(LearningAgent,
    name="AdaptiveAgent",
    capabilities=["pattern_recognition", "strategy_evolution"])

# Coordination and orchestration agents
coordinator_agent = create_agent(CoordinatorAgent,
    name="OrchestratorAgent",
    capabilities=["resource_allocation", "priority_management"])
```

### Memory Systems

Neuron implements a sophisticated multi-layered memory architecture:

```python
# Access different memory types
memory_manager = core.memory_manager

# Immediate context and active processing
working_memory = memory_manager.get_memory_system(MemoryType.WORKING)

# Sequential events and interaction history  
episodic_memory = memory_manager.get_memory_system(MemoryType.EPISODIC)

# Conceptual knowledge and relationships
semantic_memory = memory_manager.get_memory_system(MemoryType.SEMANTIC)

# Learned processes and strategies
procedural_memory = memory_manager.get_memory_system(MemoryType.PROCEDURAL)

# Store and retrieve contextual information
episodic_memory.store({
    "event": "customer_complaint",
    "timestamp": "2024-01-15T10:30:00Z",
    "context": {"customer_id": "12345", "sentiment": "frustrated"},
    "resolution": "product_replacement_offered"
})

# Retrieve relevant past interactions
relevant_history = episodic_memory.query(
    context={"customer_id": "12345"},
    timeframe="last_30_days"
)
```

### SynapticBus Communication

Agents communicate through a brain-inspired message passing system:

```python
from neuron import Message

# Create and send messages between agents
message = Message.create(
    sender="intake_agent",
    recipients=["reasoning_agent", "memory_agent"],
    content={
        "type": "customer_issue",
        "data": {"sentiment": "mixed", "intent": "unclear"},
        "confidence": 0.75,
        "requires_reasoning": True
    },
    metadata={
        "priority": "high",
        "timeout": 30,
        "fallback_required": True
    }
)

await core.synaptic_bus.send(message)
```

### Dynamic Circuit Composition

Build adaptive processing pipelines that reconfigure based on context:

```python
# Create circuits that adapt to complexity
adaptive_circuit = CircuitDefinition.create(
    name="AdaptiveReasoningCircuit",
    routing_strategy="confidence_based",
    fallback_strategy="graceful_degradation",
    agents={
        "simple_classifier": {
            "type": "ReflexAgent",
            "activation_threshold": 0.8,  # High confidence required
            "capabilities": ["quick_classification"]
        },
        "deep_reasoner": {
            "type": "DeliberativeAgent", 
            "activation_threshold": 0.3,  # Handles uncertain cases
            "capabilities": ["complex_reasoning", "uncertainty_quantification"]
        },
        "contradiction_resolver": {
            "type": "DeliberativeAgent",
            "activation_condition": "contradiction_detected",
            "capabilities": ["conflict_resolution", "clarification_generation"]
        }
    },
    decision_rules=[
        {
            "condition": "confidence > 0.8",
            "route": "simple_classifier"
        },
        {
            "condition": "contradiction_detected == True", 
            "route": "contradiction_resolver"
        },
        {
            "default": True,
            "route": "deep_reasoner"
        }
    ]
)
```

## 🎯 Real-World Applications

### Healthcare: Modular Compliance & Clinical Decision Support

```python
# HIPAA-aware healthcare circuit
healthcare_circuit = CircuitDefinition.create(
    name="ClinicalDecisionSupport",
    compliance_modules=["hipaa_monitor", "clinical_guidelines"],
    agents={
        "triage": {"type": "ReflexAgent", "capabilities": ["symptom_analysis"]},
        "risk_scorer": {"type": "DeliberativeAgent", "capabilities": ["risk_assessment"]},
        "compliance_checker": {"type": "ValidatorAgent", "capabilities": ["hipaa_validation"]}
    }
)
```

### Emergency Response: Multi-Modal Crisis Processing

```python
# Crisis response with multi-format input handling
crisis_circuit = CircuitDefinition.create(
    name="EmergencyResponseSystem", 
    input_types=["text", "voice", "social_media", "sensor_data"],
    agents={
        "input_processor": {"capabilities": ["multi_modal_parsing"]},
        "priority_ranker": {"capabilities": ["urgency_assessment", "resource_allocation"]},
        "response_coordinator": {"capabilities": ["dispatch_optimization", "status_tracking"]}
    }
)
```

### Customer Support: Multi-Session Relationship Management

```python
# Customer retention with cross-session memory
support_circuit = CircuitDefinition.create(
    name="CustomerRetentionIntelligence",
    memory_integration=True,
    agents={
        "relationship_analyzer": {"capabilities": ["sentiment_tracking", "churn_prediction"]},
        "issue_resolver": {"capabilities": ["problem_solving", "escalation_management"]},
        "retention_strategist": {"capabilities": ["intervention_planning", "satisfaction_optimization"]}
    }
)
```

## 🔧 Advanced Features

### Self-Monitoring and Error Detection

Neuron includes built-in reliability mechanisms:

```python
# Configure monitoring and fallback behavior
monitoring_config = {
    "hallucination_detection": True,
    "uncertainty_quantification": True,
    "contradiction_detection": True,
    "automatic_fallback": True,
    "explanation_generation": True
}

# Monitor system health in real-time
health_status = core.neuro_monitor.get_health_status()
performance_metrics = core.neuro_monitor.get_metrics("circuit.*")
```

### Temporal Reasoning and Causal Analysis

```python
# Enable temporal reasoning capabilities
temporal_agent = create_agent(DeliberativeAgent,
    capabilities=[
        "timeline_reconstruction",
        "causal_chain_analysis", 
        "dependency_tracking",
        "scenario_projection"
    ]
)

# Analyze complex temporal scenarios
timeline_analysis = temporal_agent.process({
    "events": mixed_chronological_data,
    "analysis_type": "causal_dependencies",
    "projection_horizon": "30_days"
})
```

### Explainability Dashboard

Every decision in Neuron is fully traceable:

```python
# Access detailed reasoning paths
explanation = core.explainability.get_decision_trace(
    circuit_id="customer_support_001",
    request_id="req_12345"
)

print(explanation.reasoning_tree)      # Step-by-step logic
print(explanation.confidence_scores)   # Certainty at each step  
print(explanation.alternative_paths)   # Other options considered
print(explanation.evidence_sources)    # Supporting information
```

## 🔌 Microservices & Extensions

Neuron's modular architecture supports plug-and-play microservices:

### Available Microservices

- **🔍 Ambiguity Resolution Service**: Detects and handles unclear inputs
- **⚖️ Contradiction Detection Service**: Identifies logical conflicts  
- **🧠 Memory Optimization Service**: Manages contextual memory efficiently
- **📊 Performance Analytics Service**: Tracks system-wide metrics
- **🔧 Dynamic Reconfiguration Service**: Adapts circuits in real-time

### Custom Microservice Development

```python
from neuron.microservices import BaseService

class CustomAnalysisService(BaseService):
    """Custom domain-specific analysis service"""
    
    def __init__(self):
        super().__init__(name="domain_analyzer")
        
    async def process(self, input_data):
        # Your custom logic here
        analysis_result = self.analyze_domain_specifics(input_data)
        return {
            "analysis": analysis_result,
            "confidence": self.calculate_confidence(analysis_result),
            "recommendations": self.generate_recommendations(analysis_result)
        }

# Register and deploy your service
core.microservice_manager.register(CustomAnalysisService())
```

## 🧪 Testing and Evaluation

### Built-in Testing Framework

```python
# Test circuit resilience
test_results = core.testing.run_stress_tests(
    circuit_id="customer_support_001",
    test_scenarios=[
        "contradictory_inputs",
        "incomplete_information", 
        "component_failures",
        "high_load_conditions"
    ]
)

# Evaluate memory persistence
memory_tests = core.testing.evaluate_memory_systems(
    retention_periods=["1_hour", "1_day", "1_week"],
    decay_patterns=["importance_weighted", "recency_based"]
)
```

### Performance Benchmarking

```python
# Compare against other frameworks
benchmark_results = core.benchmarking.compare_against([
    "langchain_equivalent",
    "direct_api_calls", 
    "custom_pipeline"
], test_cases="real_world_scenarios")
```

## 📚 Examples and Documentation

### Complete Examples

- **[Healthcare Decision Support](examples/healthcare_circuit.py)**: HIPAA-compliant medical reasoning
- **[Emergency Response System](examples/crisis_management.py)**: Multi-modal disaster response
- **[Legal Document Analysis](examples/legal_reasoning.py)**: Cross-jurisdictional compliance
- **[Customer Retention AI](examples/customer_intelligence.py)**: Multi-session relationship management
- **[Financial Risk Assessment](examples/risk_analysis.py)**: Real-time market analysis with uncertainty

### Documentation Links

- 📘 **[Full Evaluation Notebook](https://shalini-ananda-phd.notion.site/NEURON-EVALUATION-NOTEBOOK-1cec18ea2aa18002b7acf9c1791ca8ea)**: Comprehensive benchmarks and analysis
- 🎬 **[Video Demonstrations](https://github.com/ShaliniAnandaPhD/Neuron#-neuron-in-action--demo-links--use-case-walkthroughs)**: Real-world use case walkthroughs
- 🧠 **[Building in Public Series](https://www.linkedin.com/posts/shalinianandaphd_buildinpublic-neuronframework-agentreasoning-activity-7327820225213620228-fS8D)**: Development insights and updates

## 🌟 Why Choose Neuron?

### vs. LangChain
- **Memory**: Persistent multi-layered vs. token-level context
- **Reasoning**: Parallel multi-agent vs. sequential chains  
- **Observability**: Full decision traces vs. execution logs only
- **Adaptability**: Dynamic reconfiguration vs. manual flow updates

### vs. Direct API Calls
- **State Management**: Rich memory systems vs. stateless calls
- **Error Handling**: Graceful degradation vs. hard failures
- **Coordination**: Multi-agent orchestration vs. single-shot responses
- **Explainability**: Complete reasoning traces vs. black box outputs

### vs. AutoGen/CrewAI
- **Brain-Inspired Design**: Neuroscience principles vs. generic multi-agent
- **Memory Architecture**: Sophisticated persistence vs. simple conversation history
- **Fault Tolerance**: Component-level resilience vs. system-wide failures
- **Observability**: Deep introspection vs. basic logging

## 🚀 Getting Started

1. **[Install Neuron](#installation)** and run the quick start example
2. **[Explore Examples](examples/)** relevant to your use case
3. **[Read the Evaluation Notebook](https://shalini-ananda-phd.notion.site/NEURON-EVALUATION-NOTEBOOK-1cec18ea2aa18002b7acf9c1791ca8ea)** to understand capabilities
4. **[Join the Community](https://github.com/ShaliniAnandaPhD/Neuron/discussions)** for support and contributions

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

> **"Traditional AI often fails under real-world complexity—contradictions, sarcasm, conflicting goals, or mixed data formats. Neuron handles these breakdown zones through modular reasoning and memory."**  
> *— Dr. Shalini Ananda, Creator of Neuron*
