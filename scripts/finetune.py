    import argparse
    import yaml
    import os
    import pandas as pd
    import torch
    from torch.utils.data import Dataset, DataLoader
    from torch.optim import AdamW
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_scheduler
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
            
            encoding = self.tokenizer(
                text,
                return_tensors='pt',
                max_length=self.max_length,
                padding='max_length',
                truncation=True
            )
            
            return {
                'input_ids': encoding['input_ids'].squeeze(),
                'attention_mask': encoding['attention_mask'].squeeze(),
                'labels': torch.tensor(label, dtype=torch.long)
            }

    def load_data(data_dir, tokenizer, config):
        """Loads CSV data and prepares PyTorch DataLoaders."""
        train_path = os.path.join(data_dir, 'train.csv')
        if not os.path.exists(train_path):
            raise FileNotFoundError(f"Training data not found at {train_path}")
            
        train_df = pd.read_csv(train_path)
        
        train_dataset = NeuronDataset(
            texts=train_df['text'].tolist(),
            labels=train_df['label'].tolist(),
            tokenizer=tokenizer
        )
        
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=config['training_params']['batch_size'],
            shuffle=True
        )
        return train_dataloader

    def run_finetuning(config, base_model_name, output_model_dir, data_dir):
        """Performs a full fine-tuning process."""
        print("\n--- Starting Fine-Tuning Process ---")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Using device: {device}")

        print(f"Step 1: Loading Tokenizer and Model from base: {base_model_name}")
        tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            base_model_name, 
            num_labels=config['model_architecture']['num_classes']
        )
        model.to(device)

        print("Step 2: Preparing data loaders...")
        train_dataloader = load_data(data_dir, tokenizer, config)

        print("Step 3: Setting up optimizer and learning rate scheduler...")
        optimizer = AdamW(model.parameters(), lr=config['training_params']['learning_rate'])
        num_epochs = config['training_params']['num_epochs']
        num_training_steps = len(train_dataloader) * num_epochs
        lr_scheduler = get_scheduler(
            name="linear",
            optimizer=optimizer,
            num_warmup_steps=0,
            num_training_steps=num_training_steps
        )

        print("Step 4: Starting training loop...")
        progress_bar = tqdm(range(num_training_steps))
        model.train()
        for epoch in range(num_epochs):
            print(f"\n--- Epoch {epoch + 1}/{num_epochs} ---")
            for batch in train_dataloader:
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = model(**batch)
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()
                progress_bar.update(1)
                progress_bar.set_description(f"Loss: {loss.item():.4f}")

        print("\nFine-tuning complete.")
        print(f"Step 5: Saving model and tokenizer to: {output_model_dir}")
        os.makedirs(output_model_dir, exist_ok=True)
        model.save_pretrained(output_model_dir)
        tokenizer.save_pretrained(output_model_dir)
        print("Model saved successfully.")

    def main():
        parser = argparse.ArgumentParser(description="Neuron Fine-Tuning Script")
        parser.add_argument("--config", required=True, help="Path to the config file")
        parser.add_argument("--data_dir", required=True, help="Path to the data directory")
        parser.add_argument("--output_model_dir", required=True, help="Directory to save the fine-tuned model")
        parser.add_argument("--base_model_name", required=True, help="Base model name from Hugging Face Hub (e.g., 'bert-base-uncased')")
        args = parser.parse_args()

        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        run_finetuning(
            config=config,
            base_model_name=args.base_model_name,
            output_model_dir=args.output_model_dir,
            data_dir=args.data_dir
        )

    if __name__ == "__main__":
        main()
    
