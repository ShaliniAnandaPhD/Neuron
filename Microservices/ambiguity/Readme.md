# 🧠 Ambiguity Resolver

**What Breaks First: Polite Language Masking Urgency**

The `AmbiguityResolver` is a microservice in the Neuron framework that detects and resolves ambiguity in user queries, with a focus on detecting hidden urgency behind polite language.

[![🛠️ Ambiguity CI Setup Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_ci_setup_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_ci_setup_check.yml)
[![🎭 Politeness Phrase Detection](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/check-tone-phrase.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/check-tone-phrase.yml)
[![📥 Validate Input Test Files](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_input_validation.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_input_validation.yml)
[![🔌 Ambiguity Core Components Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_core_components.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_core_components.yml)
[![📘 Ambiguity Documentation Presence](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_documentation_presence.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_documentation_presence.yml)
[![📁 Ambiguity Output Directory Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_output_directory_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_output_directory_check.yml)
[![🎨 Ambiguity Visual Blueprint Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_visual_asset_check.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/ambiguity_visual_asset_check.yml)


## 🔍 Problem Statement

AI systems commonly misunderstand the true intent and urgency of polite user requests. Phrases like:

> "Just wondering if someone could help me with my account issue."

Are processed at face value, when they often mask urgency:

> "I need immediate help with my account which is preventing me from working."

The AmbiguityResolver specifically targets this "politeness-urgency gap" by analyzing message tone, detecting true intent, and calculating a more accurate urgency score.

## ✨ Features

- **Tone Analysis:** Detects politeness markers (hedges, subjunctives, minimizers) and urgency signals
- **Intent Resolution:** Identifies the true underlying intent behind ambiguous requests
- **Urgency Scoring:** Calculates a corrected urgency score based on both explicit and implied urgency
- **Tone Masking Detection:** Identifies when polite language is masking high urgency
- **Comprehensive Resolution:** Provides a final assessment with confidence scores

## 🧰 Components

The microservice is composed of three primary agents:

### 1. ToneAgent

Analyzes the tone of the message to detect:
- Politeness markers (hedges, subjunctives, apologies, minimizers)
- Urgency signals (time constraints, consequences, escalation, repeats)
- Politeness-to-urgency ratio to detect tone masking

### 2. IntentResolver

Identifies the true intent behind the message:
- Categorizes the primary intent (request_help, report_problem, account_issue, etc.)
- Measures intent confidence and ambiguity level
- Connects tone analysis to determine if urgency is implied
- Uses pattern-based detection to identify various intent types

### 3. UrgencyScorer

Calculates a more accurate urgency score:
- Combines explicit urgency from tone analysis
- Incorporates implied urgency from intent analysis
- Applies intent-specific base urgency levels
- Detects mismatches between stated and implied urgency
- Produces final resolution with confidence metrics

### 4. OutputAgent

Formats and logs the final results:
- Creates consistent JSON output format 
- Timestamps and assigns unique IDs to each resolution
- Logs comprehensive analysis for auditing and refinement
- Organizes data for downstream systems

## 🚀 Pipeline Flow

![Ambiguity Resolution Pipeline](docs/blueprints/ambiguity_pipeline.svg)

The agents work in sequence to analyze and resolve ambiguity:

1. ToneAgent analyzes politeness and urgency markers
2. IntentResolver determines the underlying intent
3. UrgencyScorer calculates the true urgency score
4. OutputAgent formats and returns the final resolution

## 💻 Usage

### Command Line

The `AmbiguityResolver` can be used directly from the command line:

```bash
python cli_resolver.py --query "Just wondering if someone could help me with my account issue."
```

For batch processing, use a JSON file:

```bash
python cli_resolver.py --file examples/ambiguous_request.json --output results.json
```

### Python API

```python
from microservices.ambiguity.ambiguity_resolver import AmbiguityResolverMicroservice

async def analyze_query(query):
    # Create and deploy the microservice
    resolver = AmbiguityResolverMicroservice(
        name="Ambiguity Resolver",
        description="Resolves ambiguity in user queries"
    )
    resolver.deploy()
    
    # Process the query
    result = await resolver.resolve_ambiguity(query)
    print(f"Intent: {result['resolution']['resolved_intent']}")
    print(f"Urgency: {result['resolution']['resolved_urgency_level']}")
    
    return result
```

## 📊 Example Output

For the query: "Just wondering if someone could help me with my account issue."

```json
{
  "original_query": "Just wondering if someone could help me with my account issue.",
  "resolution": {
    "resolved_intent": "account_issue",
    "resolved_urgency_level": "medium",
    "resolved_urgency_score": 0.65,
    "tone_masking_detected": true,
    "urgency_mismatch_detected": true,
    "confidence": 0.82,
    "timestamp": "2025-04-15T14:30:45.123456"
  },
  "resolution_id": "8f7e6d5c-4b3a-2c1d-0e9f-8a7b6c5d4e3f",
  "timestamp": "2025-04-15T14:30:45.123456"
}
```

## 🔧 Configuration

The behavior of the `AmbiguityResolver` can be customized by modifying the following:

- **Tone Patterns**: Edit the politeness and urgency marker patterns in `ToneAgent`
- **Intent Patterns**: Adjust the intent detection patterns in `IntentResolver`
- **Urgency Factors**: Tune the urgency calculation weights in `UrgencyScorer`

## 🔌 Integration

The `AmbiguityResolver` is designed to be used as:

1. **Standalone Service**: Process queries directly through the CLI or API
2. **Support Pipeline Component**: Integrate with customer support systems
3. **Preprocessing Filter**: Use before routing conversations to specific agents
4. **Dataset Generator**: Create labeled datasets of ambiguous queries

## 📈 Future Enhancements

- **Memory Integration**: Add context from previous user interactions
- **Fine-tuning**: Adapt to domain-specific politeness and urgency patterns
- **Multilingual Support**: Extend analysis to multiple languages
- **Cultural Adaptation**: Adjust for cultural-specific communication patterns
- **Temporal Analysis**: Track changing urgency over conversation history

## 🤝 Contributing

Contributions are welcome! Particularly in these areas:

- Adding new intent categories
- Improving pattern detection for different domains
- Extending tone analysis for domain-specific language
- Creating integration examples with other systems

## 📚 Related Microservices

The `AmbiguityResolver` can be used in conjunction with:

- `BrokenThreadIntegrator`: For reconstructing context across platforms
- `FrustrationIntentMapper`: For tracking escalating urgency over time
- `MultilingualContradictionHandler`: For cross-language intent analysis

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
