import asyncio
import json
import os
import sys

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from microservices.ambiguity.ambiguity_resolver import AmbiguityResolverMicroservice

async def analyze_examples():
    """Analyze example queries with the AmbiguityResolver."""
    
    # Create and deploy the microservice
    resolver = AmbiguityResolverMicroservice(
        name="Ambiguity Resolver Example",
        description="Example of resolving ambiguity in user queries"
    )
    resolver.deploy()
    
    # Example ambiguous queries
    examples = [
        "Just wondering if someone could help me with my account issue.",
        "I'm having a bit of trouble with my login, whenever you get a chance to look at it.",
        "Sorry to bother you, but I can't access my account and I have a presentation in an hour."
    ]
    
    print("\n🧠 Ambiguity Resolver Example\n")
    print("Analyzing ambiguous queries for hidden urgency and intent...\n")
    
    # Process each example
    for i, query in enumerate(examples):
        print(f"Query {i+1}: \"{query}\"")
        
        # Process the query
        result = await resolver.resolve_ambiguity(query)
        
        # Extract key information
        intent = result["resolution"]["resolved_intent"]
        urgency = result["resolution"]["resolved_urgency_level"]
        urgency_score = result["resolution"]["resolved_urgency_score"]
        tone_masking = result["resolution"]["tone_masking_detected"]
        urgency_mismatch = result["resolution"]["urgency_mismatch_detected"]
        
        # Print formatted results
        print(f"  Intent: {intent}")
        print(f"  Urgency: {urgency} ({urgency_score:.2f})")
        print(f"  Tone masking detected: {tone_masking}")
        print(f"  Urgency mismatch detected: {urgency_mismatch}\n")
        
        # Show what a system might do differently with the resolution
        if urgency_mismatch:
            print(f"  ⚠️  Traditional systems would process this as a low-urgency query")
            print(f"  ✓   Neuron correctly identifies this as a {urgency}-urgency {intent}\n")
    
    print("Complete analysis results are available in the logs directory.")

if __name__ == "__main__":
    asyncio.run(analyze_examples())
