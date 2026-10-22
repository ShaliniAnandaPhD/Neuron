# Neuron Industry Agents

One Neuron agent, configured for different industry use cases. The agent code lives in
[`neuron_agent.py`](neuron_agent.py). Each use case is a small JSON file in
[`use_cases/`](use_cases) that says which industry it serves, what the use case is, how the
agent should behave, and which compliance standards apply.

## Use cases

| Industry | Use case | What it delivers | Compliance |
|----------|----------|------------------|------------|
| Healthcare | [Secure Patient Data Management](use_cases/healthcare-secure-patient-data-management.json) | Securely store and retrieve patient data while ensuring regulatory adherence. | HIPAA, FDA, HITECH |
| Financial | [Fraud Detection & Prevention](use_cases/financial-fraud-detection-and-prevention.json) | Identify suspicious transactions and prevent financial crime with robust analysis. | PCI-DSS, SOX, GDPR |
| Insurance | [Claims Processing & Validation](use_cases/insurance-claims-processing-and-validation.json) | Efficiently and accurately process claims, identifying inconsistencies. | NAIC, Solvency II, ISO-27001 |
| Legal | [Automated Document Analysis](use_cases/legal-automated-document-analysis.json) | Rapidly review and extract key information from contracts, briefs, and legal texts. | ABA, Legal Professional Privilege, GDPR |
| Manufacturing | [Production Optimization](use_cases/manufacturing-production-optimization.json) | Optimize manufacturing schedules, material flow, and resource utilization. | ISO-9001, OSHA, ISO-14001 |
| Retail | [Personalized Customer Experience](use_cases/retail-personalized-customer-experience.json) | Deliver tailored recommendations and interactions based on past behavior and preferences. | PCI-DSS, GDPR, FTC Guidelines |

Use case names and descriptions come from the industry map in
[`LEGO BLOCKS.xlsx`](../LEGO%20BLOCKS.xlsx), which lists more use cases per industry that can
be added the same way (see [Adding a use case](#adding-a-use-case)).

## Quick start

No dependencies are needed to run the agent (Python 3.9+ standard library only).

```bash
cd agents
python neuron_agent.py --list                       # show every use case
python neuron_agent.py --use-case healthcare        # interactive CLI
python neuron_agent.py --use-case legal --smoke-test
python neuron_agent.py --use-case financial --profile analyst
```

`--use-case` takes a full key from `--list`, or just the industry when that industry has
one use case.

Run the tests (every test runs against every use case):

```bash
pip install -r requirements.txt
python -m pytest test_neuron_agent.py -v
```

Or with Docker:

```bash
docker build -t neuron-agent agents/
docker run -it neuron-agent --use-case retail
```

## How the agent works

`NeuronSystem` routes each request to one of three agents. A request looks like
`{"type": "<agent>_<operation>", "payload": {...}}`.

| Agent | Operations | Notes |
|-------|------------|-------|
| `memory` | `store`, `retrieve`, `search` | In memory key/value store with keyword search. Nothing is written to disk. |
| `reasoning` | `analyze`, `solve`, `predict` | The behavior profile decides the strategy. `predict` fits a straight line through the series. `analyze` returns one representative pattern per strategy; it does not yet compute patterns from the data. |
| `reliability` | `health_check`, `compliance`, `metrics` | Health is measured from real request counts, errors and response times. `compliance` lists the standards that apply to the use case; it does not audit against them. |

```python
import asyncio
from neuron_agent import NeuronSystem, load_use_case

async def main():
    system = NeuronSystem(load_use_case("insurance"))
    await system.start()
    result = await system.process_request({
        "type": "reasoning_solve",
        "payload": {"problem": "Flag inconsistent claims before payout"},
    })
    print(result["recommended"])
    await system.stop()

asyncio.run(main())
```

### Behavior profiles

| Profile | Strategy | Character |
|---------|----------|-----------|
| `balanced` | systematic | Every trait at 0.5. Proposes a step by step plan. |
| `explorer` | creative | High curiosity, creativity and autonomy, low caution. |
| `analyst` | analytical | High rationality, persistence and caution. |

Each use case sets a default profile; `--profile` overrides it for one run.

## Adding a use case

```bash
cd agents
python add_use_case.py --industry Healthcare --use-case "Clinical Decision Support" \
  --description "Assist in complex diagnoses and treatment plans with transparent, auditable reasoning." \
  --profile analyst
python -m pytest test_neuron_agent.py
```

This writes `use_cases/healthcare-clinical-decision-support.json`. Compliance standards
default to the industry's list in `INDUSTRY_COMPLIANCE`; pass `--compliance "A, B"` to
override. The **Advanced Neuron LEGO Agent Builder** workflow in GitHub Actions runs the
same script, runs the tests, and commits the new file.
