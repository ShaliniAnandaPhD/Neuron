# scripts/agent/main_agent.py

import os
import sys
import yaml
import importlib
import torch
import pandas as pd
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_scheduler
from tqdm.auto import tqdm

# --- Path Correction ---
# Add the project root to the Python path to allow sibling imports (e.g., from 'tools')
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ---------------------

# --- Helper function to dynamically import classes ---
def _import_class(module_path, class_name):
    """Imports a class dynamically from a given module path."""
    # We now use 'scripts.' prefix as we've added the root to the path
    full_module_path = f"scripts.{module_path}"
    module = importlib.import_module(full_module_path)
    return getattr(module, class_name)

# --- Dataset Class for training ---
class NeuronDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts, self.labels, self.tokenizer, self.max_length = texts, labels, tokenizer, max_length
    def __len__(self):
        return len(self.texts)
    def __getitem__(self, idx):
        text, label = str(self.texts[idx]), self.labels[idx]
        encoding = self.tokenizer(text, return_tensors='pt', max_length=self.max_length, padding='max_length', truncation=True)
        return {'input_ids': encoding['input_ids'].squeeze(), 'attention_mask': encoding['attention_mask'].squeeze(), 'labels': torch.tensor(label, dtype=torch.long)}

# --- The Main Agent Class ---
class NeuronAgent:
    """
    An orchestrator agent that uses a fine-tuned model, memory, and a toolbelt.
    """
    def __init__(self, config: dict):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load the base model and tokenizer
        model_config = self.config['model_architecture']
        self.tokenizer = AutoTokenizer.from_pretrained(model_config['base_model_name'])
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_config['base_model_name'],
            num_labels=model_config['num_classes']
        ).to(self.device)
        
        # Initialize memory system
        memory_config = self.config['memory_system']
        MemoryClass = _import_class('agent.memory', memory_config['class_name'])
        self.memory = MemoryClass()
        
        # Load tools into the toolbelt
        self.toolbelt = {}
        print("\n🔧 Loading tools into agent's toolbelt...")
        for tool_name in self.config.get('tools_to_load', []):
            ToolClass = _import_class(f'tools.{tool_name.lower()}', tool_name)
            self.toolbelt[tool_name] = ToolClass()
        print("✅ Toolbelt is ready.")

    def fine_tune(self, data_dir: str):
        """Fine-tunes the agent's core model."""
        print("\n🚀 Starting fine-tuning loop...")
        
        train_params = self.config['training_params']
        train_path = os.path.join(data_dir, 'train.csv')
        train_df = pd.read_csv(train_path)
        train_dataset = NeuronDataset(train_df['text'].tolist(), train_df['label'].tolist(), self.tokenizer)
        train_dataloader = DataLoader(train_dataset, batch_size=train_params['batch_size'], shuffle=True)
        
        optimizer = AdamW(self.model.parameters(), lr=train_params['learning_rate'])
        num_epochs = train_params['num_epochs']
        num_training_steps = len(train_dataloader) * num_epochs
        lr_scheduler = get_scheduler("linear", optimizer, 0, num_training_steps)
        
        progress_bar = tqdm(range(num_training_steps))
        self.model.train()
        for epoch in range(num_epochs):
            for batch in train_dataloader:
                batch = {k: v.to(self.device) for k, v in batch.items()}
                outputs = self.model(**batch)
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()
                progress_bar.update(1)
        
        print("✅ Fine-tuning complete.")
    
    def save(self, save_directory: str):
        """Saves the agent's state (model, tokenizer, and config)."""
        print(f"\n💾 Saving agent system to {save_directory}...")
        os.makedirs(save_directory, exist_ok=True)
        self.model.save_pretrained(save_directory)
        self.tokenizer.save_pretrained(save_directory)
        with open(os.path.join(save_directory, 'agent_config.yml'), 'w') as f:
            yaml.dump(self.config, f)
        print("✅ Agent system saved successfully.")

    def process_request(self, text: str):
        """A high-level method to process input."""
        self.model.eval()
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            logits = self.model(**inputs).logits
            prediction = torch.argmax(logits, dim=-1).item()
        
        self.memory.store_interaction(text, f"Classified as {prediction}")
        return f"Input text classified as label: {prediction}"


