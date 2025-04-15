import asyncio
import json
import argparse
import matplotlib.pyplot as plt
from ambiguity_resolver import AmbiguityResolverMicroservice

async def evaluate_against_ground_truth(dataset_path):
    """Evaluate the AmbiguityResolver against human-annotated ground truth."""
    # Load dataset
    try:
        with open(dataset_path, "r") as f:
            dataset = json.load(f)
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        return
    
    # Initialize resolver
    resolver = AmbiguityResolverMicroservice(
        name="Evaluation Resolver",
        description="Resolver for evaluation against ground truth"
    )
    resolver.deploy()
    
    # Track metrics
    results = {
        "intent_accuracy": [],
        "urgency_accuracy": [],
        "tone_masking_detection": {
            "true_positive": 0,
            "false_positive": 0,
            "true_negative": 0,
            "false_negative": 0
        }
    }
    
    # Process each example
    for i, example in enumerate(dataset):
        query = example["query"]
        expected_intent = example["intent"]
        expected_urgency = example["urgency_level"]
        expected_tone_masking = example.get("tone_masking", False)
        
        # Process query
        result = await resolver.resolve_ambiguity(query)
        
        # Evaluate intent accuracy
        intent_match = result["resolution"]["resolved_intent"] == expected_intent
        results["intent_accuracy"].append(intent_match)
        
        # Evaluate urgency accuracy
        urgency_match = result["resolution"]["resolved_urgency_level"] == expected_urgency
        results["urgency_accuracy"].append(urgency_match)
        
        # Evaluate tone masking detection
        detected_tone_masking = result["resolution"]["tone_masking_detected"]
        if detected_tone_masking and expected_tone_masking:
            results["tone_masking_detection"]["true_positive"] += 1
        elif detected_tone_masking and not expected_tone_masking:
            results["tone_masking_detection"]["false_positive"] += 1
        elif not detected_tone_masking and not expected_tone_masking:
            results["tone_masking_detection"]["true_negative"] += 1
        elif not detected_tone_masking and expected_tone_masking:
            results["tone_masking_detection"]["false_negative"] += 1
        
        # Print progress
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{len(dataset)} examples")
    
    # Calculate summary metrics
    intent_accuracy = sum(results["intent_accuracy"]) / len(results["intent_accuracy"])
    urgency_accuracy = sum(results["urgency_accuracy"]) / len(results["urgency_accuracy"])
    
    tp = results["tone_masking_detection"]["true_positive"]
    fp = results["tone_masking_detection"]["false_positive"]
    tn = results["tone_masking_detection"]["true_negative"]
    fn = results["tone_masking_detection"]["false_negative"]
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    # Print summary
    print("\nEvaluation Results:")
    print(f"Intent accuracy: {intent_accuracy:.2%}")
    print(f"Urgency accuracy: {urgency_accuracy:.2%}")
    print(f"Tone masking detection:")
    print(f"  Precision: {precision:.2%}")
    print(f"  Recall: {recall:.2%}")
    print(f"  F1 Score: {f1_score:.2%}")
    
    # Plot results
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    
    # Intent and urgency accuracy
    ax[0].bar(["Intent", "Urgency"], [intent_accuracy, urgency_accuracy])
    ax[0].set_ylim(0, 1)
    ax[0].set_title("Accuracy")
    ax[0].set_ylabel("Accuracy Score")
    
    # Tone masking metrics
    ax[1].bar(["Precision", "Recall", "F1 Score"], [precision, recall, f1_score])
    ax[1].set_ylim(0, 1)
    ax[1].set_title("Tone Masking Detection")
    
    plt.tight_layout()
    plt.savefig("evaluation_results.png")
    print("Results plot saved to evaluation_results.png")
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate AmbiguityResolver against ground truth")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset JSON file")
    args = parser.parse_args()
    
    asyncio.run(evaluate_against_ground_truth(args.dataset))
