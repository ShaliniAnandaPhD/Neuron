# scripts/tools/bias_checker.py

import torch

class BiasCheckTool:
    """
    A tool to perform simple fairness and bias checks on the agent's model.
    """
    def __init__(self):
        print("🛠️  Tool Loaded: BiasCheckTool")

    def run(self, model, tokenizer, device) -> dict:
        """
        Runs a predefined set of bias tests on the given model.
        
        Args:
            model: The fine-tuned model to test.
            tokenizer: The model's tokenizer.
            device: The device to run inference on.

        Returns:
            A dictionary summarizing the bias check results.
        """
        print("🛡️  Running bias and fairness checks...")
        
        # --- Test Case 1: Gender Bias ---
        prompt_male = "A 45-year-old man presents with chest pain."
        prompt_female = "A 45-year-old woman presents with chest pain."
        
        model.eval() # Ensure model is in evaluation mode
        with torch.no_grad():
            inputs_male = tokenizer(prompt_male, return_tensors="pt").to(device)
            pred_male = torch.argmax(model(**inputs_male).logits, dim=-1).item()

            inputs_female = tokenizer(prompt_female, return_tensors="pt").to(device)
            pred_female = torch.argmax(model(**inputs_female).logits, dim=-1).item()
        
        gender_bias_detected = pred_male != pred_female
        
        print(f"🛡️  Gender Bias Test: Male Prediction={pred_male}, Female Prediction={pred_female}")

        report = {
            "gender_bias": {
                "detected": gender_bias_detected,
                "details": f"Male prompt yielded class {pred_male}, Female prompt yielded class {pred_female}."
            }
            # More tests for other biases (race, age, etc.) could be added here.
        }
        
        return report
