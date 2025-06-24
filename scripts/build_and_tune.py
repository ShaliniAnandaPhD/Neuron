# scripts/build_and_tune.py

import argparse
import yaml
import os
import sys

# --- Path Correction ---
# Add the project's root directory to the Python path.
# This allows us to import modules from the 'agent' and 'tools' packages.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# ---------------------

from scripts.agent.main_agent import NeuronAgent

def main():
    """
    Main execution function to build, tune, and save a Neuron Agent.
    """
    parser = argparse.ArgumentParser(description="Build and Tune a Neuron Agent System")
    parser.add_argument("--config", required=True, help="Path to the agent YAML configuration file.")
    parser.add_argument("--data_dir", required=True, help="Path to the training data directory.")
    parser.add_argument("--output_dir", required=True, help="Directory to save the final tuned agent system.")
    args = parser.parse_args()
    
    # 1. Load configuration from YAML file
    print(f"📖 Loading configuration from: {args.config}")
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # 2. Create the Neuron Agent based on the configuration
    print("\n🤖 Instantiating Neuron Agent...")
    agent = NeuronAgent(config=config)
    
    # 3. Start the fine-tuning process
    agent.fine_tune(data_dir=args.data_dir)
    
    # 4. Save the fully configured and tuned agent
    agent.save(save_directory=args.output_dir)

    print("\n🎉 Neuron Agent creation and tuning process finished successfully!")

if __name__ == "__main__":
    main()

