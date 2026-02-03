# Neuron Framework Integration Guide
## Hallucination Detection Module

This guide shows how to integrate the hallucination detection module with the existing Neuron framework.

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Neuron Agent Circuit                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Response Generator                   │
│  (ReflexAgent, DeliberativeAgent, etc.)                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│          Hallucination Detection Layer                  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Uncertainty │  │Self-          │  │Fact           │ │
│  │ Quantifier  │  │Consistency    │  │Verification   │ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│            Detection Result & Routing                   │
│                                                         │
│  IF hallucination_detected:                            │
│    - Log to monitoring system                          │
│    - Apply mitigation strategy                         │
│    - Escalate to human if critical                     │
│  ELSE:                                                 │
│    - Proceed with response                             │
└─────────────────────────────────────────────────────────┘
```

## Step 1: Add to Neuron Framework Structure

```bash
# In your Neuron repository
cd /path/to/Neuron/
mkdir -p hallucination_detection
cp -r /path/to/hallucination_detection/* hallucination_detection/
```

## Step 2: Create Hallucination Detection Agent

Create a new file: `agents/hallucination_monitor_agent.py`

```python
"""
Hallucination Monitor Agent for Neuron Framework

Integrates hallucination detection into the agent circuit pipeline.
"""

from neuron.agents import ValidatorAgent
from hallucination_detection import HallucinationDetector, HallucinationType


class HallucinationMonitorAgent(ValidatorAgent):
    """
    Agent that monitors responses for hallucinations before they're
    sent to users or downstream systems.
    """
    
    def __init__(self, config=None):
        super().__init__(name="hallucination_monitor")
        
        self.detector = HallucinationDetector(config or {
            'hallucination_threshold': 0.6,
            'consistency_samples': 5,
            'consensus_threshold': 0.7
        })
        
        # Track hallucination patterns over time
        self.hallucination_history = []
        
    async def validate(self, response, context, agent_function=None):
        """
        Validate a response for potential hallucinations.
        
        Args:
            response: The agent's response text
            context: Context dictionary with input data
            agent_function: Optional function to generate consistency samples
            
        Returns:
            ValidationResult with hallucination detection outcome
        """
        # Run hallucination detection
        result = await self.detector.detect(
            response=response,
            context=context,
            agent_function=agent_function
        )
        
        # Log to history
        self.hallucination_history.append({
            'timestamp': result.timestamp,
            'is_hallucination': result.is_hallucination,
            'types': result.hallucination_types,
            'confidence': result.confidence_score
        })
        
        # Return validation result
        return {
            'is_valid': not result.is_hallucination,
            'confidence': result.confidence_score,
            'issues': [ht.value for ht in result.hallucination_types],
            'reasoning': result.reasoning,
            'mitigation': result.mitigation_suggestions,
            'metadata': {
                'evidence': result.evidence,
                'timestamp': result.timestamp
            }
        }
    
    def get_hallucination_metrics(self):
        """Get aggregated hallucination metrics"""
        if not self.hallucination_history:
            return {'total': 0, 'hallucinations': 0, 'rate': 0.0}
        
        total = len(self.hallucination_history)
        hallucinations = sum(
            1 for h in self.hallucination_history 
            if h['is_hallucination']
        )
        
        return {
            'total_validations': total,
            'hallucinations_detected': hallucinations,
            'hallucination_rate': hallucinations / total,
            'recent_patterns': self._analyze_recent_patterns()
        }
    
    def _analyze_recent_patterns(self, window=100):
        """Analyze recent hallucination patterns"""
        recent = self.hallucination_history[-window:]
        
        type_counts = {}
        for entry in recent:
            if entry['is_hallucination']:
                for ht in entry['types']:
                    type_name = ht.value
                    type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return type_counts
```

## Step 3: Integrate into Circuit Definition

Update your circuit definitions to include hallucination monitoring:

```python
from neuron import CircuitDefinition
from agents.hallucination_monitor_agent import HallucinationMonitorAgent

# Example: Healthcare circuit with hallucination detection
healthcare_circuit = CircuitDefinition.create(
    name="SafeHealthcareCircuit",
    description="Clinical decision support with hallucination protection",
    agents={
        "triage": {
            "type": "ReflexAgent",
            "role": "INPUT",
            "capabilities": ["symptom_analysis", "risk_assessment"]
        },
        "clinical_reasoner": {
            "type": "DeliberativeAgent",
            "role": "PROCESSOR",
            "capabilities": ["diagnosis", "treatment_planning"]
        },
        "hallucination_monitor": {
            "type": "HallucinationMonitorAgent",
            "role": "VALIDATOR",
            "config": {
                'hallucination_threshold': 0.7,  # Higher for medical
                'consistency_samples': 7,
                'consensus_threshold': 0.85
            }
        },
        "responder": {
            "type": "ReflexAgent",
            "role": "OUTPUT",
            "capabilities": ["response_formatting"]
        }
    },
    connections=[
        {"source": "triage", "target": "clinical_reasoner", "type": "direct"},
        {"source": "clinical_reasoner", "target": "hallucination_monitor", "type": "validation"},
        {"source": "hallucination_monitor", "target": "responder", "type": "conditional"}
    ],
    routing_logic={
        "hallucination_monitor": {
            "on_valid": "responder",
            "on_invalid": "escalate_to_human"
        }
    }
)
```

## Step 4: Add to Microservices

Create microservice endpoint: `Microservices/hallucination_service.py`

```python
"""
Hallucination Detection Microservice
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from hallucination_detection import HallucinationDetector


app = FastAPI(title="Hallucination Detection Service")
detector = HallucinationDetector()


class DetectionRequest(BaseModel):
    response: str
    context: dict
    config: dict = None


@app.post("/detect")
async def detect_hallucination(request: DetectionRequest):
    """Detect hallucinations in agent responses"""
    try:
        result = await detector.detect(
            response=request.response,
            context=request.context
        )
        
        return {
            'is_hallucination': result.is_hallucination,
            'confidence_score': result.confidence_score,
            'hallucination_types': [ht.value for ht in result.hallucination_types],
            'reasoning': result.reasoning,
            'mitigation_suggestions': result.mitigation_suggestions,
            'evidence': result.evidence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "service": "hallucination_detection"}
```

## Step 5: Update Monitoring Dashboard

Add to `src/neuro_monitor.py`:

```python
class NeuroMonitor:
    # ... existing code ...
    
    def get_hallucination_metrics(self, circuit_id=None):
        """Get hallucination detection metrics"""
        if circuit_id:
            circuit = self.circuits.get(circuit_id)
            if circuit and hasattr(circuit, 'hallucination_monitor'):
                return circuit.hallucination_monitor.get_hallucination_metrics()
        
        # Aggregate across all circuits
        all_metrics = []
        for circuit in self.circuits.values():
            if hasattr(circuit, 'hallucination_monitor'):
                all_metrics.append(
                    circuit.hallucination_monitor.get_hallucination_metrics()
                )
        
        return self._aggregate_metrics(all_metrics)
```

## Step 6: Configuration Files

Add to `configs/hallucination_detection.yml`:

```yaml
hallucination_detection:
  # Global settings
  enabled: true
  
  # Detection sensitivity by domain
  domains:
    healthcare:
      threshold: 0.75
      consistency_samples: 7
      consensus_threshold: 0.85
      escalate_on_detection: true
      
    customer_support:
      threshold: 0.65
      consistency_samples: 5
      consensus_threshold: 0.75
      escalate_on_detection: false
      
    legal_compliance:
      threshold: 0.80
      consistency_samples: 10
      consensus_threshold: 0.90
      escalate_on_detection: true
  
  # Mitigation strategies
  mitigation:
    auto_retry: true
    max_retries: 3
    fallback_to_human: true
    log_all_detections: true
  
  # Monitoring
  monitoring:
    track_metrics: true
    alert_threshold: 0.15  # Alert if >15% hallucination rate
    alert_channels: ['slack', 'email']
```

## Step 7: Testing Integration

Create test file: `tests/test_hallucination_integration.py`

```python
"""
Integration tests for hallucination detection in Neuron framework
"""

import pytest
from neuron import initialize, create_agent
from agents.hallucination_monitor_agent import HallucinationMonitorAgent


@pytest.mark.asyncio
async def test_circuit_with_hallucination_detection():
    """Test complete circuit with hallucination monitoring"""
    core = initialize()
    
    # Create circuit
    circuit_def = {
        'name': 'TestCircuit',
        'agents': {
            'responder': {'type': 'ReflexAgent'},
            'monitor': {'type': 'HallucinationMonitorAgent'}
        }
    }
    
    circuit_id = core.circuit_designer.create_circuit(circuit_def)
    
    # Test input
    response = await core.circuit_designer.send_input(circuit_id, {
        'query': 'What is the patient diagnosis?',
        'context': {'symptoms': 'fever, cough'}
    })
    
    assert 'validation' in response
    assert 'confidence' in response['validation']


@pytest.mark.asyncio  
async def test_hallucination_escalation():
    """Test automatic escalation on hallucination detection"""
    monitor = HallucinationMonitorAgent(config={
        'hallucination_threshold': 0.5
    })
    
    # Test with likely hallucination
    result = await monitor.validate(
        response="The patient probably maybe has the condition",
        context={},
        agent_function=None
    )
    
    assert result['is_valid'] == False
    assert len(result['mitigation']) > 0
```

## Usage Examples

### Basic Usage in Circuit
```python
# Initialize Neuron with hallucination detection
from neuron import initialize
from hallucination_detection import HallucinationDetector

core = initialize()

# Process request through circuit with monitoring
response = await core.process_with_monitoring(
    circuit_id="healthcare_001",
    input_data=patient_query,
    enable_hallucination_detection=True
)

if response.hallucination_detected:
    # Handle appropriately
    escalate_to_human(response)
```

### Direct Detection
```python
from hallucination_detection import HallucinationDetector

detector = HallucinationDetector()
result = await detector.detect(agent_response, context)

if result.is_hallucination:
    print(f"Warning: {result.reasoning}")
    for suggestion in result.mitigation_suggestions:
        print(f"  - {suggestion}")
```

## Deployment Checklist

- [ ] Install dependencies: `pip install -r hallucination_detection/requirements.txt`
- [ ] Copy module to Neuron framework
- [ ] Create HallucinationMonitorAgent
- [ ] Update circuit definitions
- [ ] Configure domain-specific thresholds
- [ ] Set up monitoring and alerts
- [ ] Test integration with existing agents
- [ ] Deploy hallucination detection microservice
- [ ] Update documentation
- [ ] Train team on mitigation strategies

## Monitoring and Metrics

Track these key metrics:
- **Hallucination Rate**: Percentage of responses flagged
- **Detection Latency**: Time to detect hallucinations
- **False Positive Rate**: Incorrectly flagged responses
- **Escalation Rate**: Responses requiring human review
- **Pattern Distribution**: Types of hallucinations detected

## Next Steps

1. Start with low-risk circuits to validate integration
2. Gradually increase detection sensitivity
3. Collect feedback on false positives/negatives
4. Fine-tune thresholds based on domain
5. Expand to all critical circuits

For questions or issues, see main [Neuron documentation](../README.md).
