# Neuron + Oxen: Clinical Dataset QA & Drift Recovery Pipeline

This project showcases a complete, end-to-end clinical dataset QA and drift adaptation pipeline using the Neuron agent framework and Oxen.ai for dataset versioning. It uses a real-world heart disease dataset to demonstrate how intelligent agents can identify, simulate, and fix data issues while tracking all changes for reproducibility.

## Overview
A reproducible walkthrough covering:
- Corrupting data with RedTeam simulations
- Inspecting and enhancing datasets using Neuron
- Measuring performance impact
- Tracking versioned changes with Oxen.ai

## Dataset Versions
| Version              | File Name             | Description                                  |
|----------------------|------------------------|----------------------------------------------|
| Original             | `heart.csv`            | Clean starting dataset (14 columns)          |
| Corrupted            | `heart_corrupted.csv`  | Intentionally corrupted by RedTeamAgent      |
| Enhanced             | `heart_clean.csv`      | Issues resolved and combined risk added      |

---

## Step-by-Step Pipeline

### 1. Initial Inspection (`heart.csv`)
- Found missing values in `ca`, `thal`
- Implausible age entry (`167`)
- Invalid categorical encodings (`thal=0`)
- Logical inconsistencies (e.g. chest pain vs. diagnosis)

### 2. Simulated Corruption (Red Team)
Command:
```bash
neuron redteam heart.csv --intensity medium
```
Injected:
- 7 implausible age values (103–167)
- 5 corrupted cholesterol values (<60 mg/dL)
- 4 invalid `thal` encodings (set to 0)
- 3 logical inconsistencies

Result saved as `heart_corrupted.csv`

### 3. Neuron Inspection & Enhancement
Command:
```bash
python ../heart_inspection.py heart_corrupted.csv --apply-recommendations
```
Fixes applied:
- Imputed missing values
- Fixed invalid encodings in `thal`, `ca`
- Applied normalization
- Generated `combined_risk_score` using weights from top features (ca=0.42, thal=0.38, cp=0.21)

All missing/invalid values resolved  
Model accuracy improved: 80.8% → 83.7% (+2.9%)

### 4. Dataset Versioning with Oxen
```bash
oxen init
oxen add heart.csv
oxen commit -m "Initial commit of heart disease dataset"
oxen add heart_corrupted.csv
oxen commit -m "Corrupted dataset with simulated anomalies"
oxen add heart_clean.csv
oxen commit -m "Enhanced dataset with automated data quality improvements"
oxen push origin main
```

### 5. Dataset Diff and Impact
```bash
oxen diff f4e25d8 8a76c42
```
| Change             | Result                      |
|--------------------|------------------------------|
| Columns            | +1 (`combined_risk_score`)   |
| Missing Values     | 6 → 0 (-100%)                 |
| Data Issues        | 17 → 0 (-100%)                |
| Accuracy Impact    | +2.5%                         |
| Precision Impact   | +3.1%                         |
| Recall Impact      | +2.8%                         |
| F1 Score Impact    | +2.9%                         |

Dataset published: [https://hub.oxen.ai/datasets/heart-disease](https://hub.oxen.ai/datasets/heart-disease)

---

## Powered by Neuron Agents
- `RedTeamAgent`: Simulates clinically realistic corruption
- `SchemaVerifier`, `StatisticalAnomalyDetector`, `ColumnImportanceRanker`
- `Enhancer`: Applies imputation, normalization, feature engineering
- `Evaluator`: Quantifies model impact from data changes

## Technologies Used
- [Neuron](https://github.com/ShaliniAnandaPhD/Neuron) – cognitive-agent framework for AI pipelines
- [Oxen.ai](https://github.com/oxen-io) – version control system for datasets
- Python, TensorFlow backend, CLI-driven automation

---

## Results
"From corrupted clinical chaos to enhanced, trackable data — with a +2.9% boost in accuracy."

This repo demonstrates how intelligent agents and dataset versioning tools can collaboratively improve clinical AI robustness — without retraining from scratch.

---

## Contact
Questions or ideas? Reach out via [LinkedIn](https://www.linkedin.com/in/) or drop an issue in this repo.

---

## License
MIT License

