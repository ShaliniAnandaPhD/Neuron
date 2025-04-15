# AmbiguityResolver Blueprint

## 🔍 Overview

The `AmbiguityResolver` dissects user queries to extract true intent and urgency that is often masked by polite language. This blueprint outlines the architecture, agents, and processing flow.

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

```python
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

```python
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
  "ambiguity_level": 0.3
}
```

### UrgencyScorer

**Purpose**: Calculate true urgency score beyond surface level expressions
**Inputs**: User query, tone analysis, and intent analysis
**Outputs**: Comprehensive urgency analysis with true urgency score

```python
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

```python
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
3. Results passed to `IntentResolver` to determine primary intent
4. `IntentResolver` measures ambiguity and checks for implied urgency
5. Combined analysis sent to `UrgencyScorer` for comprehensive scoring
6. `UrgencyScorer` calculates true urgency and detects mismatches
7. Final resolution formatted by `OutputAgent` with standardized structure

## 🔌 Integration Points

- **Input**: Raw text queries via API or CLI
- **Output**: Structured JSON with intent and urgency analysis
- **Logging**: Detailed analysis logs in the logs directory
- **Configuration**: Pattern databases and scoring weights can be customized

## 🔑 Key Metrics

- **Tone Masking Rate**: Percentage of queries with detected tone masking
- **Urgency Correction**: Difference between explicit and true urgency scores
- **Intent Confidence**: Confidence level in resolved intent
- **Ambiguity Level**: Degree of query ambiguity (0.0-1.0)

## 📊 Performance Considerations

- Pattern matching is optimized for speed but may have higher CPU usage with complex patterns
- Memory usage scales linearly with pattern database size
- Response time typically under 50ms for standard queries
