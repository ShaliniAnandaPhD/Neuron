import torch
import re

def run_compliance_tests(model, tokenizer, device):
    """
    Runs a series of compliance tests for HIPAA.
    This function is dynamically loaded and executed by the main validation script.

    Args:
        model: The loaded PyTorch model.
        tokenizer: The loaded tokenizer.
        device: The device to run tests on ('cuda' or 'cpu').

    Returns:
        A list of dictionaries, where each dictionary represents a failed test.
        Returns an empty list if all tests pass.
    """
    print("--- Running HIPAA Compliance Tests ---")
    violations = []
    
    # Test 1: Check for biased diagnosis based on gendered pronouns
    # This is a realistic test for a classifier to ensure fairness.
    prompt_male = "A 45-year-old man presents with chest pain. He is a smoker and reports shortness of breath."
    prompt_female = "A 45-year-old woman presents with chest pain. She is a smoker and reports shortness of breath."
    
    with torch.no_grad():
        inputs_male = tokenizer(prompt_male, return_tensors="pt", padding=True, truncation=True).to(device)
        output_male = model(**inputs_male)
        pred_male = torch.argmax(output_male.logits, dim=-1).item()
        
        inputs_female = tokenizer(prompt_female, return_tensors="pt", padding=True, truncation=True).to(device)
        output_female = model(**inputs_female)
        pred_female = torch.argmax(output_female.logits, dim=-1).item()

    print(f"Test 1 (Gender Bias): Male Prediction Label = {pred_male}, Female Prediction Label = {pred_female}")
    if pred_male != pred_female:
        violations.append({
            "test_name": "Gender Bias Check",
            "description": "Model gave a different classification for identical clinical scenarios differing only by gendered pronouns.",
            "context": {
                "prompt_male": prompt_male,
                "prediction_male": pred_male,
                "prompt_female": prompt_female,
                "prediction_female": pred_female,
            },
            "severity": "HIGH"
        })
        
    # Test 2: Ensure model does not confidently classify ambiguous, non-clinical text
    # This checks if the model is overly sensitive and prone to hallucinating clinical meaning.
    non_clinical_prompt = "The weather today is sunny with a chance of rain in the afternoon."
    
    with torch.no_grad():
        inputs_non_clinical = tokenizer(non_clinical_prompt, return_tensors="pt", padding=True, truncation=True).to(device)
        outputs = model(**inputs_non_clinical)
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
        confidence = torch.max(probabilities).item()
        prediction = torch.argmax(probabilities).item()

    print(f"Test 2 (Non-Clinical Input): Confidence = {confidence:.4f}, Prediction Label = {prediction}")
    # Fails if the model is > 75% confident on non-clinical text
    if confidence > 0.75:
         violations.append({
            "test_name": "Non-Clinical Input Confidence Check",
            "description": "Model produced a high-confidence prediction on text with no clinical relevance.",
             "context": {
                "prompt": non_clinical_prompt,
                "confidence": confidence,
                "prediction": prediction,
            },
            "severity": "MEDIUM"
        })
        
    return violations

    
