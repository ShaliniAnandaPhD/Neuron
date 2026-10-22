> ⚠️ **Please Read Before Proceeding**
>
> This project is released under a **modified MIT License** with strict **attribution and usage terms**.
>
> Before using, forking, or integrating any part of this repository — especially in commercial or research contexts —  
> please review the [NOTICE.md](./NOTICE.md) file carefully.
>
> Unauthorized use without proper attribution may result in license violations or academic misuse.



# 🧠 NeuronBench: Benchmarking What Breaks First in AI Systems

**NeuronBench** is a diagnostic benchmark suite designed to evaluate how different AI architectures perform under real-world failure modes — where context collapses, tone is misunderstood, and ambiguity derails resolution.

It’s not just about accuracy — it’s about **resilience**, **adaptability**, and the ability to recover when things get messy. Based on the “What Breaks First?” experiment series, this project turns diagnostic insight into reproducible benchmarks.


## What NeuronBench Tests

NeuronBench focuses on benchmarking AI systems across complex, high-friction scenarios that typically break brittle systems:

- **Ambiguity** — Indirect, polite, or unclear requests
- **Tone Masking** — Urgency hidden under courteous language
- **Translation Drift** — Meaning loss across multilingual phrasing
- **Compliance Conflicts** — Contradictory legal requirements across jurisdictions
- **Legacy Format Issues** — Ambiguous dates, mixed units, outdated schemas
- **Mixed Format Inputs** — Inputs combining plain text, JSON, shorthand, or metadata

Each test case is designed to challenge the system’s contextual awareness, decision-making hierarchy, and fallback strategies.

---

##  Folder Structure

```bash
neuron-bench/
├── datasets/     # Benchmark results and test cases (CSV, plus multilingual_drift.json)
├── scripts/      # Analysis scripts that read datasets/ and write results/
├── results/      # Generated charts and reports (not committed)
└── Readme.md
```

##  Datasets

| Group | Files |
|-------|-------|
| Failure behaviour | `what_breaks_first_testing_results.csv`, `error_analysis_dataset.csv`, `resilience_score_methodology_data.csv` |
| Capability tests | `ambiguity_politeness_detection_tests.csv`, `contradiction_implied_tests.csv`, `sarcasm_pattern_tests.csv`, `multilingual_code_switching_tests.csv`, `memory_retention_timeframe_tests.csv`, `parallel_reasoning_tests.csv` |
| Architecture tests | `modularity_component_removal_tests.csv`, `circuit_rewiring_adaptability_tests.csv`, `neural_component_visibility_tests.csv`, `observability_trace_completeness_tests.csv`, `synapticbus_communication_tests.csv` |
| Scores and gaps | `dimension_detailed_metrics.csv`, `system_performance_aggregated_metrics.csv`, `performance_over_time.csv`, `target_gap_analysis.csv`, `improvement_priorities.csv` |

---

##  Quick Start

```bash
pip install pandas numpy matplotlib seaborn scipy scikit-learn statsmodels
python neuron-bench/scripts/neuron_data_processor.py           # aggregate scores
python neuron-bench/scripts/gap_analysis_engine.py             # gaps to production targets
python neuron-bench/scripts/cross_architecture_comparison.py   # what breaks first, by architecture
python neuron-bench/scripts/neuron_visualization_dashboard.py  # dashboard charts
python neuron-bench/scripts/memory_system_analyzer.py          # memory retention
python neuron-bench/scripts/sarcasm_detector.py                # sarcasm detection
python neuron-bench/scripts/neuron_time_series.py              # trends and forecasts
```

Each script reads `neuron-bench/datasets/` and writes charts, JSON and CSV
reports to its own folder under `neuron-bench/results/`, whatever directory
you run it from. `run_multilingual_benchmark.py` is not runnable yet: it
imports `agents`, `config` and `evaluation` modules that are not in this
repository.

---

##  Output Metrics

The scripts produce:
-  Scores by dimension, component and architecture
- 🧠 Error and misclassification breakdowns
-  Gap to production targets and improvement priorities
-  Trends over time with forecasts
-  Charts: comparisons, heatmaps, error types, timelines

---

## 🧠 Why NeuronBench?

Because what fails first isn’t syntax.  
It’s **context**, **tone**, **urgency**, and **human nuance**.

NeuronBench offers a ground truth for real-world AI fragility — and demonstrates how **modular, agent-based architectures like Neuron** outperform static function-call systems or brittle rule engines.

This is a benchmark suite for:
- Researchers testing new reasoning models
- Teams evaluating robustness in production
- Builders seeking resilience over novelty

---

##  Maintainers

Built by [Shalini Ananda, PhD](https://github.com/ShaliniAnandaPhD)  
Founder of the Neuron Framework | AI researcher | Builder of systems that don’t break when the world does

---

##  How to Contribute

- Add test results as a CSV in `datasets/` (follow the columns of the existing file in the same group)
- Report edge cases and failures as GitHub issues
- Use the tag `#bench-case` or `#bench-system` on GitHub issues

---

##  License

NeuronBench is released under the MIT License with an additional Attribution requirement for benchmark content reuse. See `LICENSE` for more.

---

##  Let’s Build Systems That Don’t Break First

This isn’t just testing models.  
It’s testing the **integrity** of how systems hold up under pressure.  
Join the experiment. Fork the suite. Submit your edge case.  
Let’s redefine what AI resilience *really* means.

