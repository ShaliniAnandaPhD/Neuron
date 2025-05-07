import json
from pathlib import Path
from config.thresholds import load_thresholds

# === Import Neuron agents ===
from agents.tone_agent import ToneAgent
from agents.intent_resolver import IntentResolver
from agents.urgency_scorer import UrgencyScorer
from agents.fallback_agent import FallbackAgent  # Optional
from evaluation.scoring import evaluate_output  # Scoring logic

# === Setup paths ===
DATASET_PATH = Path("datasets/multilingual_drift.json")
THRESHOLDS_PATH = Path("config/thresholds.yaml")
OUTPUT_PATH = Path("results/multilingual_drift_results.json")


# === Step 1: Load benchmark cases ===
def load_test_cases(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# === Step 2: Run a single case through Neuron pipeline ===
def run_neuron_pipeline(input_text: str, expected_output: dict, thresholds: dict):
    # Initialize agents
    tone_agent = ToneAgent()
    intent_resolver = IntentResolver()
    urgency_scorer = UrgencyScorer()
    fallback_agent = FallbackAgent()  # Optional, only if needed

    # Step 1: Tone detection
    tone_result = tone_agent.analyze(input_text)
    
    # Step 2: Intent resolution
    intent_result = intent_resolver.resolve(input_text)
    
    # Step 3: Urgency scoring
    urgency_result = urgency_scorer.score(input_text, tone_result, intent_result)

    # Step 4 (Optional): Apply fallback if needed
    fallback_used = False
    if (
        tone_result["confidence"] < thresholds["tone"] or
        intent_result["confidence"] < thresholds["intent"]
    ):
        fallback_result = fallback_agent.handle(input_text)
        fallback_used = True
    else:
        fallback_result = None

    # Assemble predicted output
    predicted_output = {
        "tone": tone_result["label"],
        "intent": intent_result["label"],
        "urgency": urgency_result["label"],
        "confidence": {
            "tone": tone_result["confidence"],
            "intent": intent_result["confidence"],
            "urgency": urgency_result["confidence"]
        }
    }

    # Step 5: Evaluate against expected output
    evaluation_result = evaluate_output(predicted_output, expected_output, thresholds)
    evaluation_result.update({
        "input_text": input_text,
        "predicted_output": predicted_output,
        "fallback_used": fallback_used
    })

    return evaluation_result


# === Step 3: Run the full benchmark suite ===
def run_multilingual_benchmark(cases, thresholds):
    results = []
    print(f"Running multilingual drift benchmark on {len(cases)} cases...\n")

    for case in cases:
        case_id = case.get("id", "unknown_case")
        input_text = case["input_text"]
        expected_output = case["expected_output"]

        print(f"> [{case_id}] Input: {input_text}")
        result = run_neuron_pipeline(input_text, expected_output, thresholds)
        result["id"] = case_id
        results.append(result)

        print(f"✔ Result: {'PASS' if result['pass'] else 'FAIL'}")
        print(f"   → Scores: {result['predicted_output']['confidence']}")
        print(f"   → Fallback used: {result['fallback_used']}\n")

    return results


# === Step 4: Save results ===
def save_results(results, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Results saved to: {path}")


# === Main entry point ===
if __name__ == "__main__":
    try:
        test_cases = load_test_cases(DATASET_PATH)
        thresholds = load_thresholds(THRESHOLDS_PATH)
        results = run_multilingual_benchmark(test_cases, thresholds)
        save_results(results, OUTPUT_PATH)
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
