    import argparse
    import json
    import os
    import importlib.util
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    def load_model_and_tokenizer(model_dir, device):
        """Loads a fine-tuned model and tokenizer from a directory."""
        if not os.path.isdir(model_dir):
            raise FileNotFoundError(f"Model directory not found at {model_dir}")
            
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.to(device)
        model.eval()
        return model, tokenizer

    def load_compliance_rules(rules_script_path):
        """Dynamically loads compliance rules from a specified Python script."""
        spec = importlib.util.spec_from_file_location("compliance_rules", rules_script_path)
        compliance_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(compliance_module)
        
        if not hasattr(compliance_module, 'run_compliance_tests'):
            raise AttributeError(f"Rules script {rules_script_path} must define a 'run_compliance_tests' function.")
            
        return compliance_module.run_compliance_tests

    def save_report(report_data, report_path):
        """Saves the compliance report to a JSON file."""
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=4)
        print(f"Report saved to {report_path}")

    def main():
        parser = argparse.ArgumentParser(description="Neuron Compliance Validation Script")
        parser.add_argument("--model_dir", required=True, help="Directory of the fine-tuned model")
        parser.add_argument("--rules_script", required=True, help="Python script containing compliance rules")
        parser.add_argument("--output_report_path", required=True, help="Path to save the JSON compliance report")
        args = parser.parse_args()

        print("\n--- Starting Compliance Validation ---")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {device}")

        print("Step 1: Loading model and tokenizer...")
        model, tokenizer = load_model_and_tokenizer(args.model_dir, device)
        
        print("Step 2: Loading compliance rules...")
        run_tests_function = load_compliance_rules(args.rules_script)

        print("Step 3: Executing compliance tests...")
        violations = run_tests_function(model, tokenizer, device)
        
        print(f"Found {len(violations)} compliance violations.")
        final_status = "PASS" if not violations else "FAIL"
        
        report = {
            "model_validated": args.model_dir,
            "rules_script_used": args.rules_script,
            "validation_status": final_status,
            "violations_found": violations
        }
        
        print("Step 4: Saving compliance report...")
        save_report(report, args.output_report_path)
        
        if final_status == "FAIL":
            print("\nCompliance check FAILED. Exiting with error code 1.")
            exit(1)
        else:
            print("\nCompliance check PASSED.")

    if __name__ == "__main__":
        main()
    
