# AmbiguityResolver Blueprint

## 🔍 Overview

The `AmbiguityResolver` microservice detects and resolves ambiguity in user queries with a focus on uncovering hidden urgency masked by polite language. This blueprint outlines the architecture, components, and processing flow.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AmbiguityResolver Circuit                    │
│                                                                 │
│  ┌─────────────┐      ┌───────────────┐      ┌───────────────┐  │
│  │  ToneAgent  │──────▶ IntentResolver ├─────▶ UrgencyScorer │  │
│  └─────────────┘      └───────────────┘      └───────┬───────┘  │
│         ▲                                            │          │
│         │                                            ▼          │
│    User Query                                   OutputAgent     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🧩 Components

### ToneAgent 

**Purpose**: Analyze message tone, detecting politeness and urgency markers  
**Inputs**: Raw user query text  
**Outputs**: Tone analysis with politeness and urgency scores

**Key Features**:
- Detects hedges, subjunctives, apologies, and minimizers
- Identifies urgency signals such as time constraints, escalation markers
- Calculates politeness-to-urgency ratio
- Flags potential tone masking

**Example Output**:
```json
{
  "politeness_score": 0.85,
  "urgency_score": 0.35,
  "detected_patterns": {
    "politeness": [
      {
        "category": "hedges",
        "instances": ["just", "wondering"]
      },
      {
        "category": "minimizers",
        "instances": ["bit of"]
      }
    ],
    "urgency": [
      {
        "category": "time_constraints",
        "instances": ["as soon as"]
      }
    ]
  },
  "tone_masking_detected": true
}
```

### IntentResolver

**Purpose**: Determine the true intent behind ambiguous language  
**Inputs**: User query and tone analysis  
**Outputs**: Intent analysis with confidence scores and ambiguity assessment

**Key Features**:
- Categorizes primary intent (account_issue, billing_issue, etc.)
- Calculates confidence based on pattern matches
- Measures ambiguity level using intent distribution
- Tracks conversation history to detect escalation
- Uses similarity matching for repeated intents

**Example Output**:
```json
{
  "primary_intent": "account_issue",
  "intent_confidence": 0.75,
  "detected_intents": {
    "account_issue": {
      "score": 3,
      "matches": ["account", "login", "password"]
    },
    "request_help": {
      "score": 1,
      "matches": ["help"]
    }
  },
  "implied_urgency": true,
  "ambiguity_level": 0.3,
  "escalation_detected": false
}
```

### UrgencyScorer

**Purpose**: Calculate true urgency score beyond surface level expressions  
**Inputs**: User query, tone analysis, and intent analysis  
**Outputs**: Comprehensive urgency analysis with true urgency score

**Key Features**:
- Combines explicit urgency signals with implied urgency
- Applies intent-specific base urgency levels
- Considers conversation history for escalation patterns
- Detects mismatches between stated and implied urgency
- Calculates final urgency score with confidence level

**Example Output**:
```json
{
  "explicit_urgency": 0.35,
  "implied_urgency": 0.65,
  "intent_based_urgency": 0.60,
  "true_urgency": 0.68,
  "urgency_mismatch": true
}
```

### OutputAgent

**Purpose**: Format and standardize final resolution output  
**Inputs**: Combined analysis from all previous agents  
**Outputs**: Final structured resolution with metadata

**Key Features**:
- Creates consistent JSON output format
- Assigns resolution ID and timestamps
- Logs comprehensive analysis for auditing
- Generates performance metrics
- Provides metadata for downstream systems

**Example Output**:
```json
{
  "original_query": "Just wondering if someone could help with my account issue.",
  "resolution": {
    "resolved_intent": "account_issue",
    "resolved_urgency_level": "medium",
    "resolved_urgency_score": 0.68,
    "tone_masking_detected": true,
    "urgency_mismatch_detected": true,
    "confidence": 0.75,
    "timestamp": "2025-04-15T14:30:45.123456"
  },
  "resolution_id": "8f7e6d5c-4b3a-2c1d-0e9f-8a7b6c5d4e3f",
  "timestamp": "2025-04-15T14:30:45.123456"
}
```

## 🔄 Process Flow

1. User query is received by the `ToneAgent`
2. `ToneAgent` analyzes politeness markers and urgency signals
3. Analysis is passed to `IntentResolver` to determine primary intent
4. `IntentResolver` measures ambiguity and checks for implied urgency
5. Combined analysis is sent to `UrgencyScorer` for comprehensive scoring
6. `UrgencyScorer` calculates true urgency and detects mismatches
7. Final resolution is formatted by `OutputAgent` with standardized structure

## 🛠️ Implementation Details

### Configuration Parameters

The microservice can be configured via `config.yaml`:
```yaml
tone_agent:
  politeness_thresholds:
    high: 0.6
    medium: 0.3
    low: 0.0
  urgency_thresholds:
    high: 0.6
    medium: 0.3
    low: 0.0

intent_resolver:
  confidence_thresholds:
    high: 0.8
    medium: 0.5
    low: 0.2

urgency_scorer:
  urgency_factors:
    tone_multiplier: 1.5
    intent_multiplier: 1.2
    ambiguity_penalty: 0.8
  base_intent_urgency:
    report_problem: 0.7
    account_issue: 0.6
    billing_issue: 0.8
    request_help: 0.5
```

### Memory Usage
- Stores interaction history for each user
- Maintains last 10 interactions 
- Detects escalation patterns over time
- Tracks similarity between queries for repeat detection

### Performance Metrics
- Tone masking detection rate
- Urgency mismatch detection rate 
- Intent classification accuracy
- Processing time per query
- Memory usage per session

## 🔌 Integration Points

- **Input**: Raw text queries via API, CLI, or function call
- **Output**: Structured JSON with intent and urgency analysis
- **API**: RESTful endpoints for integration with web applications
- **Logging**: Detailed analysis logs in the logs directory
- **Configuration**: YAML configuration for tuning parameters
- **Events**: Optional event hooks for real-time monitoring
- **Memory**: Session storage for conversation context

## 🔑 Key Metrics

- **Tone Masking Rate**: Percentage of queries with detected tone masking
- **Urgency Correction**: Difference between explicit and true urgency scores
- **Intent Confidence**: Average confidence level in resolved intent
- **Ambiguity Level**: Average degree of query ambiguity (0.0-1.0)
- **Processing Efficiency**: Average query processing time

## 📊 Performance Considerations

- Pattern matching is optimized for speed using compiled regex
- Memory usage scales linearly with user count × history length
- Response time typically under 50ms for standard queries
- Configuration can be tuned for precision vs. recall tradeoff
- Designed for stateless operation with optional context persistence

## 🧪 Testing Methodology

- Unit tests for each agent component
- Integration tests for entire pipeline
- Evaluation against human-labeled ground truth dataset
- Performance benchmarking under load
- Rate of false positives/negatives in tone masking detection

## 📈 Future Development

- Extend with machine learning models for improved pattern recognition
- Add multilingual support via language-specific pattern databases
- Implement cultural context adaptation for regional politeness norms
- Develop temporal analysis for long-term conversation tracking
- Create specialized domain-specific intent recognition
