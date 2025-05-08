"""Advanced example of building a circuit with multiple specialized models."""

import torch
from neuron import initialize, CircuitDefinition
from neuron.model_providers.huggingface_provider import (
    HuggingFaceProvider,
    MistralProvider,
    LlamaProvider
)

# Initialize the Neuron framework
core = initialize()

def create_support_circuit():
    """Create a customer support circuit with specialized models.
    
    This circuit uses multiple specialized models:
    1. A small model for intent detection
    2. A small model for sentiment analysis
    3. A small model for language detection
    4. A large model for response generation
    """
    print("Creating a customer support circuit with specialized models...")
    
    # Define models based on available GPU memory
    has_gpu = torch.cuda.is_available()
    gpu_memory = torch.cuda.get_device_properties(0).total_memory if has_gpu else 0
    
    # Select appropriate models based on available resources
    if has_gpu and gpu_memory >= 16 * 1024 * 1024 * 1024:  # 16GB+ VRAM
        reasoning_model = MistralProvider(quantization="8bit")
    elif has_gpu and gpu_memory >= 8 * 1024 * 1024 * 1024:  # 8GB+ VRAM
        reasoning_model = LlamaProvider(model_version="2-7b-chat-hf", quantization="4bit")
    else:
        # For smaller GPUs or CPU, use a smaller model
        reasoning_model = HuggingFaceProvider(
            model_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            task="text-generation",
            quantization="4bit" if has_gpu else None
        )
    
    # Define the circuit with specialized models for each role
    circuit_def = CircuitDefinition.create(
        name="CustomerSupportCircuit",
        description="A circuit for handling customer support requests with specialized models",
        agents={
            "intent_detector": {
                "type": "ReflexAgent",
                "role": "CLASSIFIER",
                "name": "IntentDetector",
                "description": "Detects the intent of customer messages",
                "model_provider": HuggingFaceProvider(
                    model_id="facebook/bart-large-mnli",
                    task="zero-shot-classification"
                )
            },
            "sentiment_analyzer": {
                "type": "ReflexAgent",
                "role": "CLASSIFIER",
                "name": "SentimentAnalyzer",
                "description": "Analyzes sentiment in customer messages",
                "model_provider": HuggingFaceProvider(
                    model_id="distilbert-base-uncased-finetuned-sst-2-english",
                    task="sentiment-analysis"
                )
            },
            "language_detector": {
                "type": "ReflexAgent",
                "role": "CLASSIFIER",
                "name": "LanguageDetector",
                "description": "Detects the language of customer messages",
                "model_provider": HuggingFaceProvider(
                    model_id="papluca/xlm-roberta-base-language-detection",
                    task="text-classification"
                )
            },
            "response_generator": {
                "type": "DeliberativeAgent",
                "role": "GENERATOR",
                "name": "ResponseGenerator",
                "description": "Generates appropriate responses to customer inquiries",
                "model_provider": reasoning_model
            },
            "coordinator": {
                "type": "CoordinatorAgent",
                "role": "COORDINATOR",
                "name": "CircuitCoordinator",
                "description": "Coordinates the flow of information between agents",
                "model_provider": None  # Uses rule-based coordination
            }
        },
        connections=[
            {
                "source": "intent_detector",
                "target": "coordinator",
                "connection_type": "direct"
            },
            {
                "source": "sentiment_analyzer",
                "target": "coordinator",
                "connection_type": "direct"
            },
            {
                "source": "language_detector",
                "target": "coordinator",
                "connection_type": "direct"
            },
            {
                "source": "coordinator",
                "target": "response_generator",
                "connection_type": "direct"
            }
        ]
    )
    
    # Create and deploy the circuit
    circuit_id = core.circuit_designer.create_circuit(circuit_def)
    core.circuit_designer.deploy_circuit(circuit_id)
    
    print(f"CustomerSupportCircuit created with ID: {circuit_id}")
    return circuit_id


def test_support_circuit(circuit_id, customer_message):
    """Test the customer support circuit with a sample message."""
    print(f"\nTesting support circuit with message: '{customer_message}'")
    
    # Send input to the circuit
    result = core.circuit_designer.send_input(
        circuit_id, 
        {
            "message": customer_message,
            "customer_id": "test_customer_123",
            "timestamp": "2023-05-08T14:32:10Z"
        }
    )
    
    print("\nCircuit output:")
    print(f"Intent: {result.get('intent', 'Unknown')}")
    print(f"Sentiment: {result.get('sentiment', 'Unknown')}")
    print(f"Language: {result.get('language', 'Unknown')}")
    print(f"Response: {result.get('response', 'No response generated')}")
    
    return result


if __name__ == "__main__":
    # Create and test the customer support circuit
    circuit_id = create_support_circuit()
    
    # Test with different types of customer messages
    test_support_circuit(
        circuit_id,
        "I've been waiting for my order for 2 weeks now. When will it arrive?"
    )
    
    test_support_circuit(
        circuit_id,
        "Your product is amazing! I love how easy it is to use."
    )
    
    test_support_circuit(
        circuit_id,
        "Je voudrais savoir comment retourner un produit défectueux."
    )
    
    print("\nCircuit testing completed successfully!")
