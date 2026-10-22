

> ⚠️ **Please Read Before Proceeding**
>
> This project is released under a **modified MIT License** with strict **attribution and usage terms**.
>
> Before using, forking, or integrating any part of this repository — especially in commercial or research contexts —  
> please review the [NOTICE.md](./NOTICE.md) file carefully.
>
> Unauthorized use without proper attribution may result in license violations or academic misuse.



# 🧠 Neuron Micro-Audit Services
**What Breaks First → What Gets Fixed First**

Modular agents for failure detection and repair in complex, real-world AI pipelines.

---

##  Overview

AI systems don’t break because they lack logic —  
They break because they lose **context**, misread **intent**, collapse under **ambiguity**, or fail to track emotional dynamics over time.

**Neuron Micro-Audit Services** is a growing library of **self-contained diagnostic agents**, each designed to detect and repair a specific fragility pattern in LLM-based systems. These modules are plug-and-play, composable, and explainable.

[![🧠 Intent Phrase Scan (Safe)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/check_message_intent_keyword.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/check_message_intent_keyword.yml)
[![🧠 Agent Reference Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/verify-agent-names.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/verify-agent-names.yml)
[![📊 CLI Output Confidence Check](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/inspect-cli-output-log.yml/badge.svg?branch=main)](https://github.com/ShaliniAnandaPhD/Neuron/actions/workflows/inspect-cli-output-log.yml)



---

##  Use Case Examples

| Micro-Audit | What It Detects | What It Fixes |
|-------------|------------------|----------------|
| `SarcasmAuditor` | Sarcasm misclassified as praise | Reclassifies tone using cultural + linguistic heuristics |
| `MultilingualContradictionChecker` | Translated terms that contradict intent | Resolves contradiction via primary language alignment |
| `UrgencyToneDisambiguator` | Polite masking in support requests | Escalates based on implied vs. explicit urgency |
| `ComplianceConflictResolver` | Conflicting regional requirements (e.g., GDPR vs. US BSA) | Applies jurisdictional overrides + audit trails |
| `BrokenThreadIntegrator` | Support threads with dropped context across platforms | Rebuilds continuity through identity + intent recovery |
| `LegacyParserAgent` | Invalid/mixed formatting in legacy systems (e.g., COBOL) | Normalizes inputs and validates hidden structure |

Each module is independently runnable and follows a consistent agent circuit flow.

---

##  Architecture

Each audit module is powered by the Neuron Framework’s circuit-based pipeline:

```text
[Input Stream] 
   → [Preprocessor] 
   → [Failure Signature Matcher] 
   → [Contextual Resolver] 
   → [Action or Alert]
```

All micro-audits:
- Operate independently or in composed chains
- Emit explainable failure logs
- Include confidence metrics and remediation traces
- Integrate with SynapticBus for shared memory and NeuroMonitor for observability

---

##  Getting Started

Three microservices are implemented in this folder: `ambiguity/` (tone and
urgency disambiguation), `healthcare/` (multilingual patient record
integration) and `multilingual/` (medical device documentation). The other
audits in the table above are planned, not yet built.

Each one is a Neuron circuit: `BaseMicroservice.process()` deploys the
circuit, sends the input and returns the OUTPUT agent's result. Run
everything from the repository root:

```bash
git clone https://github.com/ShaliniAnandaPhD/Neuron
cd Neuron
pip install -e .
pip install -r Microservices/ambiguity/requirements.txt

# CLI
python -m Microservices.ambiguity.cli_resolver --query "Just wondering if someone could help me with my account issue." --pretty

# API (POST /resolve, POST /resolve/batch, GET /metrics)
uvicorn Microservices.ambiguity.api:app --reload

# Evaluate against the labeled dataset
python -m Microservices.ambiguity.evaluate --dataset Microservices/ambiguity/data/evaluation_dataset.json

# Tests
python -m pytest Microservices/ambiguity/tests
```

---

##  Logging + Metrics

Each microservice:
- logs every request to `Microservices/logs/{service_name}.log`
- reports request counts, errors and average latency from `get_metrics()`
  (`GET /metrics` in the API)
- returns per-stage scores (for example tone, intent and urgency analysis)
  alongside its final answer

---

##  Why Microservices?

Because AI repair isn't monolithic — it's **patterned**.

Each failure needs:
- A dedicated listener
- A precise fixer
- A system that not only detects what broke — but also anticipates what might break next

**Neuron Micro-Audit Services** is our step toward context-aware, repairable AI.

---

##  Collaboration

for:
- Engineers building agent pipelines and LLM orchestration
- Researchers exploring cognitive repair, tone analysis, and regulatory conflicts
- Contributors who love debugging the edge cases static systems ignore

Start a [GitHub Discussion](https://github.com/ShaliniAnandaPhD/Neuron/discussions)or open an issue 


