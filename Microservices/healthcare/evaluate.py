import asyncio
import json
import argparse
import matplotlib.pyplot as plt
from healthcare_integration import HealthcareDataIntegrationMicroservice

async def evaluate_against_ground_truth(dataset_path, ground_truth_path):
    """Evaluate the Healthcare Integration against human-annotated ground truth."""
    # Load dataset
    try:
        with open(dataset_path, "r") as f:
            dataset = json.load(f)
        
        with open(ground_truth_path, "r") as f:
            ground_truth = json.load(f)
    except Exception as e:
        print(f"Error loading dataset or ground truth: {str(e)}")
        return
    
    # Initialize integration service
    integrator = HealthcareDataIntegrationMicroservice(
        name="Evaluation Integrator",
        description="Healthcare integrator for evaluation against ground truth"
    )
    integrator.deploy()
    
    # Track metrics
    results = {
        "condition_detection": {
            "true_positive": 0,
            "false_positive": 0,
            "false_negative": 0
        },
        "care_gap_detection": {
            "true_positive": 0,
            "false_positive": 0,
            "false_negative": 0
        },
        "medication_resolution": {
            "correct": 0,
            "incorrect": 0
        },
        "language_detection": {
            "correct": 0,
            "incorrect": 0
        }
    }
    
    # Process the dataset
    integration_result = await integrator.integrate_patient_records(dataset)
    
    # Evaluate condition detection
    detected_conditions = set([c["name"].lower() for c in integration_result["health_data"]["conditions"]])
    true_conditions = set([c.lower() for c in ground_truth["conditions"]])
    
    for condition in detected_conditions:
        if condition in true_conditions:
            results["condition_detection"]["true_positive"] += 1
        else:
            results["condition_detection"]["false_positive"] += 1
    
    for condition in true_conditions:
        if condition not in detected_conditions:
            results["condition_detection"]["false_negative"] += 1
    
    # Evaluate care gap detection
    detected_gaps = set([g["description"].lower() for g in integration_result["health_data"]["care_gaps"]])
    true_gaps = set([g.lower() for g in ground_truth["care_gaps"]])
    
    for gap in detected_gaps:
        if any(true_gap in gap for true_gap in true_gaps):
            results["care_gap_detection"]["true_positive"] += 1
        else:
            results["care_gap_detection"]["false_positive"] += 1
    
    for gap in true_gaps:
        if not any(gap in detected_gap for detected_gap in detected_gaps):
            results["care_gap_detection"]["false_negative"] += 1
    
    # Evaluate language detection
    for i, record in enumerate(dataset):
        if i < len(ground_truth["language_annotations"]):
            true_lang = ground_truth["language_annotations"][i]
            
            # Find the corresponding processed record
            for processed in integration_result.get("original_records", []):
                if processed.get("id") == record.get("id"):
                    detected_lang = processed.get("detected_language", "unknown")
                    if detected_lang == true_lang:
                        results["language_detection"]["correct"] += 1
                    else:
                        results["language_detection"]["incorrect"] += 1
                    break
    
    # Calculate metrics
    condition_precision = results["condition_detection"]["true_positive"] / (results["condition_detection"]["true_positive"] + results["condition_detection"]["false_positive"]) if (results["condition_detection"]["true_positive"] + results["condition_detection"]["false_positive"]) > 0 else 0
    condition_recall = results["condition_detection"]["true_positive"] / (results["condition_detection"]["true_positive"] + results["condition_detection"]["false_negative"]) if (results["condition_detection"]["true_positive"] + results["condition_detection"]["false_negative"]) > 0 else 0
    condition_f1 = 2 * condition_precision * condition_recall / (condition_precision + condition_recall) if (condition_precision + condition_recall) > 0 else 0
    
    gap_precision = results["care_gap_detection"]["true_positive"] / (results["care_gap_detection"]["true_positive"] + results["care_gap_detection"]["false_positive"]) if (results["care_gap_detection"]["true_positive"] + results["care_gap_detection"]["false_positive"]) > 0 else 0
    gap_recall = results["care_gap_detection"]["true_positive"] / (results["care_gap_detection"]["true_positive"] + results["care_gap_detection"]["false_negative"]) if (results["care_gap_detection"]["true_positive"] + results["care_gap_detection"]["false_negative"]) > 0 else 0
    gap_f1 = 2 * gap_precision * gap_recall / (gap_precision + gap_recall) if (gap_precision + gap_recall) > 0 else 0
    
    language_accuracy = results["language_detection"]["correct"] / (results["language_detection"]["correct"] + results["language_detection"]["incorrect"]) if (results["language_detection"]["correct"] + results["language_detection"]["incorrect"]) > 0 else 0
    
    # Print summary
    print("\nEvaluation Results:")
    print(f"Condition Detection:")
    print(f"  Precision: {condition_precision:.2%}")
    print(f"  Recall: {condition_recall:.2%}")
    print(f"  F1 Score: {condition_f1:.2%}")
    
    print(f"\nCare Gap Detection:")
    print(f"  Precision: {gap_precision:.2%}")
    print(f"  Recall: {gap_recall:.2%}")
    print(f"  F1 Score: {gap_f1:.2%}")
    
    print(f"\nLanguage Detection:")
    print(f"  Accuracy: {language_accuracy:.2%}")
    
    # Plot results
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    
    # Condition detection metrics
    ax[0].bar(["Precision", "Recall", "F1"], [condition_precision, condition_recall, condition_f1])
    ax[0].set_ylim(0, 1)
    ax[0].set_title("Condition Detection")
    
    # Care gap detection metrics
    ax[1].bar(["Precision", "Recall", "F1"], [gap_precision, gap_recall, gap_f1])
    ax[1].set_ylim(0, 1)
    ax[1].set_title("Care Gap Detection")
    
    # Language detection accuracy
    ax[2].bar(["Accuracy"], [language_accuracy])
    ax[2].set_ylim(0, 1)
    ax[2].set_title("Language Detection")
    
    plt.tight_layout()
    plt.savefig("healthcare_evaluation_results.png")
    print("Results plot saved to healthcare_evaluation_results.png")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Healthcare Integration against ground truth")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset JSON file")
    parser.add_argument("--ground-truth", type=str, required=True, help="Path to ground truth JSON file")
    args = parser.parse_args()
    
    asyncio.run(evaluate_against_ground_truth(args.dataset, args.ground_truth))
