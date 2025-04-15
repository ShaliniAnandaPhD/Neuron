import os
import sys
import json
import argparse
import asyncio
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from microservices.ambiguity.ambiguity_resolver import AmbiguityResolverMicroservice

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Ambiguity Resolver CLI')
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--query', type=str, help='Direct query to analyze')
    input_group.add_argument('--file', type=str, help='JSON file containing queries to analyze')
    
    parser.add_argument('--output', type=str, help='Output file for results (default: stdout)')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

async def process_query(query, microservice, verbose=False):
    """Process a single query through the ambiguity resolver.
    
    Args:
        query: Query string to process
        microservice: Ambiguity resolver microservice instance
        verbose: Whether to print verbose output
        
    Returns:
        Resolution result
    """
    if verbose:
        print(f"Processing query: {query}")
    
    # Run the query through the microservice
    result = await microservice.resolve_ambiguity(query)
    
    if verbose:
        print(f"Intent: {result['resolution']['resolved_intent']}, "
              f"Urgency: {result['resolution']['resolved_urgency_level']} "
              f"({result['resolution']['resolved_urgency_score']:.2f})")
    
    return result

async def process_from_file(file_path, microservice, verbose=False):
    """Process queries from a JSON file.
    
    Args:
        file_path: Path to JSON file with queries
        microservice: Ambiguity resolver microservice instance
        verbose: Whether to print verbose output
        
    Returns:
        List of resolution results
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Check if the data is a list of queries or a single query object
    if isinstance(data, list):
        queries = data
    elif isinstance(data, dict) and 'queries' in data:
        queries = data['queries']
    else:
        queries = [data]
    
    results = []
    for i, query_item in enumerate(queries):
        # Handle both simple strings and objects with a 'query' field
        if isinstance(query_item, str):
            query = query_item
        elif isinstance(query_item, dict) and 'query' in query_item:
            query = query_item['query']
        else:
            if verbose:
                print(f"Skipping invalid query item at index {i}")
            continue
        
        # Process the query
        result = await process_query(query, microservice, verbose)
        results.append(result)
    
    return results

async def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Create and deploy the microservice
    microservice = AmbiguityResolverMicroservice(
        name="Ambiguity Resolver",
        description="Resolves ambiguity and detects true urgency in user queries"
    )
    microservice.deploy()
    
    # Process input
    if args.query:
        results = [await process_query(args.query, microservice, args.verbose)]
    else:
        results = await process_from_file(args.file, microservice, args.verbose)
    
    # Format output
    output = {
        "resolution_results": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat()
    }
    
    # Output results
    indent = 2 if args.pretty else None
    output_json = json.dumps(output, indent=indent)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        if args.verbose:
            print(f"Results written to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    asyncio.run(main())
