"""Basic example of using Hugging Face models with Neuron."""

from neuron import initialize, create_agent, ReflexAgent, DeliberativeAgent
from neuron.model_providers.huggingface_provider import HuggingFaceProvider, MistralProvider

# Initialize the Neuron framework
core = initialize()

# Example 1: Create a text generation agent with Mistral
print("Creating a reasoning agent with Mistral...")
reasoning_agent = create_agent(
    DeliberativeAgent,
    name="ReasoningAgent",
    description="A reasoning agent powered by Mistral",
    model_provider=MistralProvider(
        model_version="7B-Instruct-v0.2",
        quantization="4bit"  # Use 4-bit quantization for efficiency
    )
)

# Example 2: Create a sentiment analysis agent
print("Creating a sentiment analysis agent...")
sentiment_agent = create_agent(
    ReflexAgent,
    name="SentimentDetector",
    description="Detects sentiment in customer messages",
    model_provider=HuggingFaceProvider(
        model_id="distilbert-base-uncased-finetuned-sst-2-english",
        task="sentiment-analysis"
    )
)

# Example 3: Create an embeddings agent
print("Creating an embeddings agent...")
embedding_agent = create_agent(
    ReflexAgent,
    name="EmbeddingGenerator",
    description="Generates embeddings for semantic search",
    model_provider=HuggingFaceProvider(
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        task="feature-extraction"
    )
)

# Test the agents
if __name__ == "__main__":
    # Test reasoning agent
    print("\nTesting reasoning agent...")
    response = reasoning_agent.process("Explain the concept of neural networks in simple terms")
    print(f"Response: {response}")
    
    # Test sentiment agent
    print("\nTesting sentiment agent...")
    sentiment_positive = sentiment_agent.process("I love this product!")
    sentiment_negative = sentiment_agent.process("This is terrible service.")
    print(f"Positive sentiment: {sentiment_positive}")
    print(f"Negative sentiment: {sentiment_negative}")
    
    # Test embedding agent
    print("\nTesting embedding agent...")
    embedding1 = embedding_agent.process("Machine learning is fascinating")
    embedding2 = embedding_agent.process("AI and ML are revolutionary technologies")
    print(f"Embedding 1 length: {len(embedding1)}")
    print(f"Embedding 2 length: {len(embedding2)}")
    
    print("\nAll agents tested successfully!")
