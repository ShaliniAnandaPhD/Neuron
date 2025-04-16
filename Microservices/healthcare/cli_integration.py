import os
import sys
import json
import argparse
import asyncio
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from microservices.healthcare.healthcare_integration import HealthcareDataIntegrationMicroservice

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Healthcare Data Integration CLI')
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--records', type=str, help='JSON file containing patient records')
    
    parser.add_argument('--output', type=str, help='Output file for results (default: stdout)')
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

async def process_from_file(file_path, microservice, verbose=False):
    """Process patient records from a JSON file.
    
    Args:
        file_path: Path to JSON file with patient records
        microservice: Healthcare integration microservice instance
        verbose: Whether to print verbose output
        
    Returns:
        Integration results
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Check if the data is a list of records or a single record object
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and 'patient_records' in data:
        records = data['patient_records']
    else:
        records = [data]
    
    if verbose:
        print(f"Processing {len(records)} patient records...")
    
    # Process the records
    result = await microservice.integrate_patient_records(records)
    
    if verbose:
        print(f"Integration completed for patient {result['patient_id']}")
        print(f"Identified {len(result['health_data']['conditions'])} conditions")
        print(f"Found {len(result['health_data']['care_gaps'])} care gaps")
    
    return result

async def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Create and deploy the microservice
    microservice = HealthcareDataIntegrationMicroservice(
        name="Healthcare Integration CLI",
        description="Integrates multilingual healthcare records across providers"
    )
    microservice.deploy()
    
    # Process input
    results = await process_from_file(args.records, microservice, args.verbose)
    
    # Format output
    indent = 2 if args.pretty else None
    output_json = json.dumps(results, indent=indent)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
        if args.verbose:
            print(f"Results written to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    asyncio.run(main())
