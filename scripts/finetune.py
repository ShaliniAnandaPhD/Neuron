import argparse
import yaml
import os
import pandas as pd
import torch
import importlib # For dynamically importing agent classes
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_scheduler
from tqdm.auto import tqdm

# ======================================================================================
# Agent System Components (These would typically be in their own files)
# ======================================================================================

class BaseAgent:
    """A base class for our specialized agents."""
    def __init__(self, model, tokenizer, device, config):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device
        self.config = config
        self.name = "BaseAgent"
        print(f"-> Initialized agent component: {self.name}")

    def process(self, text):
        # Default behavior: run a standard prediction
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            logits = self.model(**inputs).logits
            return torch.argmax(logits, dim=-1).item()

class CaseAnalyzer(BaseAgent):
    """An example specialized agent."""
    def __init__(self, model, tokenizer, device, config):
        super().__init__(model, tokenizer, device, config)
        self.name = "CaseAnalyzer"
        # This agent might have its own specific resources, e.g., a knowledge base
        # self.knowledge_base = self.load_knowledge_base()

class SafetyMonitor(BaseAgent):
    """Another example agent for monitoring safety."""
    def __init__(self, model, tokenizer, device, config):
        super().__init__(model, tokenizer, device, config)
        self.name = "SafetyMonitor"

def get_agent_class(class_name):
    """Dynamically get an agent class from this script's context."""
    return globals().get(class_name)

# ======================================================================================
# Fine-Tuning Components
# ======================================================================================

class NeuronDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts, self.labels, self.tokenizer, self.max_length = texts, labels, tokenizer, max_length
    def __len__(self):
        return len(self.texts)
    def __getitem__(self, idx):
        text, label = str(self.texts[idx]), self.labels[idx]
        encoding = self.tokenizer(text, return_tensors='pt', max_length=self.max_length, padding='max_length', truncation=True)
        return {'input_ids': encoding['input_ids'].squeeze(), 'attention_mask': encoding['attention_mask'].squeeze(), 'labels': torch.tensor(label, dtype=torch.long)}

def load_data(data_dir, tokenizer, batch_size):
    train_path = os.path.join(data_dir, 'train.csv')
    train_df = pd.read_csv(train_path)
    train_dataset = NeuronDataset(train_df['text'].tolist(), train_df['label'].tolist(), tokenizer)
    return DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

# ======================================================================================
# The Merged Build and Tune Function
# ======================================================================================

def build_and_tune_agent(config, base_model_name, output_agent_dir, data_dir):
    print("\n--- Starting Agent Build and Fine-Tuning Process ---")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # --- Step 1: Load the base model (the "brain" of the agent) ---
    print(f"\nStep 1: Loading base model '{base_model_name}'...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        base_model_name, 
        num_labels=config['model_architecture']['num_classes']
    )
    model.to(device)
    
    # --- Step 2: Build the Agent System by dynamically loading components ---
    print("\nStep 2: Assembling agent system from configuration...")
    agent_system = {}
    for agent_name in config.get('agents', []):
        AgentClass = get_agent_class(agent_name)
        if AgentClass:
            agent_system[agent_name] = AgentClass(model, tokenizer, device, config)
        else:
            print(f"Warning: Agent class '{agent_name}' not found.")
    
    if not agent_system:
        raise ValueError("Configuration specifies no valid agents to build.")
        
    print("Agent system assembled successfully.")

    # --- Step 3: Fine-Tune the model within the agent context ---
    print("\nStep 3: Starting fine-tuning loop for the agent's core model...")
    train_dataloader = load_data(data_dir, tokenizer, config['training_params']['batch_size'])
    optimizer = AdamW(model.parameters(), lr=config['training_params']['learning_rate'])
    num_epochs = config['training_params']['num_epochs']
    num_training_steps = len(train_dataloader) * num_epochs
    lr_scheduler = get_scheduler("linear", optimizer, num_warmup_steps=0, num_training_steps=num_training_steps)
    progress_bar = tqdm(range(num_training_steps))
    
    model.train()
    for epoch in range(num_epochs):
        print(f"--- Epoch {epoch + 1}/{num_epochs} ---")
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

    # --- Step 4: Save the entire tuned agent system ---
    # This now saves the model/tokenizer that the instantiated agents use.
    print(f"\nStep 4: Saving tuned agent system to: {output_agent_dir}")
    os.makedirs(output_agent_dir, exist_ok=True)
    model.save_pretrained(output_agent_dir)
    tokenizer.save_pretrained(output_agent_dir)
    # Also save the config that built it, so it can be reconstructed later.
    with open(os.path.join(output_agent_dir, 'agent_config.yml'), 'w') as f:
        yaml.dump(config, f)
        
    print("Agent system saved successfully.")

def main():
    parser = argparse.ArgumentParser(description="Build and Tune a Neuron Agent System")
    parser.add_argument("--config", required=True, help="Path to the agent configuration file")
    parser.add_argument("--data_dir", required=True, help="Path to the training data directory")
    parser.add_argument("--output_agent_dir", required=True, help="Directory to save the tuned agent system")
    parser.add_argument("--base_model_name", required=True, help="Base model name from Hugging Face Hub")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    build_and_tune_agent(
        config=config,
        base_model_name=args.base_model_name,
        output_agent_dir=args.output_agent_dir,
        data_dir=args.data_dir
    )

if __name__ == "__main__":
    main()

    
