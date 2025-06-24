    import argparse
    import json
    import os
    import pandas as pd
    import torch
    from torch.utils.data import Dataset, DataLoader
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    from sklearn.metrics import classification_report
    from tqdm.auto import tqdm

    class NeuronDataset(Dataset):
        """PyTorch Dataset for loading text data."""
        def __init__(self, texts, labels, tokenizer, max_length=128):
            self.texts = texts
            self.labels = labels
            self.tokenizer = tokenizer
            self.max_length = max_length

        def __len__(self):
            return len(self.texts)

        def __getitem__(self, idx):
            text = str(self.texts[idx]) # Ensure text is string
            label = self.labels[idx]
            encoding = self.tokenizer(text, return_tensors='pt', max_length=self.max_length, padding='max_length', truncation=True)
            return {
                'input_ids': encoding['input_ids'].squeeze(),
                'attention_mask': encoding['attention_mask'].squeeze(),
                'labels': torch.tensor(label, dtype=torch.long)
            }

    def run_evaluation(model_dir, test_data_path, output_report_path):
        """Loads a fine-tuned model and evaluates it against a test set."""
        print("\n--- Starting Model Evaluation ---")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {device}")

        print(f"Step 1: Loading model from {model_dir}")
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.to(device)
        model.eval()

        print(f"Step 2: Loading test data from {test_data_path}")
        test_df = pd.read_csv(test_data_path)
        test_dataset = NeuronDataset(
            texts=test_df['text'].tolist(),
            labels=test_df['label'].tolist(),
            tokenizer=tokenizer
        )
        test_dataloader = DataLoader(test_dataset, batch_size=8)

        print("Step 3: Running inference on test data...")
        all_preds, all_labels = [], []
        with torch.no_grad():
            for batch in tqdm(test_dataloader, desc="Evaluating"):
                batch = {k: v.to(device) for k, v in batch.items()}
                labels = batch['labels']
                outputs = model(**batch)
                predictions = torch.argmax(outputs.logits, dim=-1)
                all_preds.extend(predictions.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        print("Step 4: Generating and saving classification report...")
        report = classification_report(all_labels, all_preds, output_dict=True, zero_division=0)
        
        os.makedirs(os.path.dirname(output_report_path), exist_ok=True)
        with open(output_report_path, 'w') as f:
            json.dump(report, f, indent=4)
            
        print(f"Evaluation report saved to {output_report_path}")
        print("--- Evaluation Complete ---")

    def main():
        parser = argparse.ArgumentParser(description="Neuron Model Evaluation Script")
        parser.add_argument("--model_dir", required=True, help="Directory of the fine-tuned model")
        parser.add_argument("--test_data_path", required=True, help="Path to the test.csv file")
        parser.add_argument("--output_report_path", required=True, help="Path to save the JSON evaluation report")
        args = parser.parse_args()

        run_evaluation(args.model_dir, args.test_data_path, args.output_report_path)

    if __name__ == "__main__":
        main()
    
