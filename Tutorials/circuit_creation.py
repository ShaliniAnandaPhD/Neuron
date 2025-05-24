"""
Circuit Creation Example

This example demonstrates how to create and use circuits in the Neuron framework.
Circuits are networks of connected agents that work together to accomplish tasks.
"""

import asyncio
import logging
import time
from neuron import (
    initialize, start, shutdown, run_context,
    ReflexAgent, DeliberativeAgent, LearningAgent, CoordinatorAgent,
    CircuitDefinition, Message
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    try:
        # Initialize the framework
        logger.info("Initializing Neuron framework...")
        core = initialize()
        
        # Get the circuit designer
        circuit_designer = core.circuit_designer
        
        # Define a simple sequential circuit
        logger.info("Creating a sequential processing circuit...")
        sequential_circuit_def = CircuitDefinition.create(
            name="SequentialCircuit",
            description="A simple sequential processing circuit",
            agents={
                "input": {
                    "type": "ReflexAgent",
                    "role": "INPUT",
                    "name": "Input Agent",
                    "description": "Receives input and passes it to the processor"
                },
                "processor": {
                    "type": "DeliberativeAgent",
                    "role": "PROCESSOR",
                    "name": "Processor Agent",
                    "description": "Processes the input data"
                },
                "output": {
                    "type": "ReflexAgent",
                    "role": "OUTPUT",
                    "name": "Output Agent",
                    "description": "Receives processed data and produces output"
                }
            },
            connections=[
                {
                    "source": "input",
                    "target": "processor",
                    "connection_type": "direct"
                },
                {
                    "source": "processor",
                    "target": "output",
                    "connection_type": "direct"
                }
            ],
            metadata={"circuit_type": "sequential"}
        )
        
        # Create the sequential circuit
        sequential_id = await circuit_designer.create_circuit(sequential_circuit_def)
        logger.info(f"Created sequential circuit with ID: {sequential_id}")
        
        # Define a star network circuit with a coordinator
        logger.info("Creating a star network circuit...")
        star_circuit_def = CircuitDefinition.create(
            name="StarNetwork",
            description="A star network with a coordinator and worker agents",
            agents={
                "input": {
                    "type": "ReflexAgent",
                    "role": "INPUT",
                    "name": "Input Agent",
                    "description": "Receives input and passes it to the coordinator"
                },
                "coordinator": {
                    "type": "CoordinatorAgent",
                    "role": "COORDINATOR",
                    "name": "Coordinator",
                    "description": "Coordinates work among worker agents"
                },
                "worker1": {
                    "type": "DeliberativeAgent",
                    "role": "PROCESSOR",
                    "name": "Worker 1",
                    "description": "First worker agent"
                },
                "worker2": {
                    "type": "LearningAgent",
                    "role": "PROCESSOR",
                    "name": "Worker 2",
                    "description": "Second worker agent"
                },
                "worker3": {
                    "type": "ReflexAgent",
                    "role": "PROCESSOR",
                    "name": "Worker 3",
                    "description": "Third worker agent"
                },
                "output": {
                    "type": "ReflexAgent",
                    "role": "OUTPUT",
                    "name": "Output Agent",
                    "description": "Produces final output"
                }
            },
            connections=[
                {
                    "source": "input",
                    "target": "coordinator",
                    "connection_type": "direct"
                },
                {
                    "source": "coordinator",
                    "target": "worker1",
                    "connection_type": "direct"
                },
                {
                    "source": "coordinator",
                    "target": "worker2",
                    "connection_type": "direct"
                },
                {
                    "source": "coordinator",
                    "target": "worker3",
                    "connection_type": "direct"
                },
                {
                    "source": "worker1",
                    "target": "coordinator",
                    "connection_type": "direct"
                },
                {
                    "source": "worker2",
                    "target": "coordinator",
                    "connection_type": "direct"
                },
                {
                    "source": "worker3",
                    "target": "coordinator",
                    "connection_type": "direct"
                },
                {
                    "source": "coordinator",
                    "target": "output",
                    "connection_type": "direct"
                }
            ],
            metadata={"circuit_type": "star_network"}
        )
        
        # Create the star network circuit
        star_id = await circuit_designer.create_circuit(star_circuit_def)
        logger.info(f"Created star network circuit with ID: {star_id}")
        
        # Create a circuit from a template
        logger.info("Creating a circuit from a template...")
        template_id = await circuit_designer.create_from_template(
            "sequential_pipeline",
            {
                "processor1_type": "DeliberativeAgent",
                "processor2_type": "LearningAgent"
            }
        )
        logger.info(f"Created circuit from template with ID: {template_id}")
        
        # Start the framework
        logger.info("Starting the framework...")
        start()
        
        # Deploy the circuits
        logger.info("Deploying circuits...")
        await circuit_designer.deploy_circuit(sequential_id)
        await circuit_designer.deploy_circuit(star_id)
        await circuit_designer.deploy_circuit(template_id)
        
        logger.info("Circuits deployed successfully")
        
        # Send input to the sequential circuit
        logger.info("Sending input to sequential circuit...")
        await circuit_designer.send_input(
            sequential_id,
            {
                "type": "text",
                "content": "This is a test input for the sequential circuit."
            }
        )
        
        # Send input to the star network circuit
        logger.info("Sending input to star network circuit...")
        await circuit_designer.send_input(
            star_id,
            {
                "type": "task",
                "task": "process_data",
                "data": [1, 2, 3, 4, 5],
                "parameters": {"mode": "sum"}
            }
        )
        
        # Send input to the template circuit
        logger.info("Sending input to template circuit...")
        await circuit_designer.send_input(
            template_id,
            {
                "type": "analysis",
                "data": "Sample data for analysis",
                "options": {"detailed": True}
            }
        )
        
        # Wait for processing to complete
        logger.info("Waiting for circuits to process inputs...")
        await asyncio.sleep(3.0)
        
        # Get circuit information
        logger.info("Circuit information:")
        
        for circuit_id in [sequential_id, star_id, template_id]:
            circuit = circuit_designer.get_circuit(circuit_id)
            info = circuit.to_dict()
            
            logger.info(f"  {info['name']} ({circuit_id}):")
            logger.info(f"    - Status: {info['status']}")
            logger.info(f"    - Agents: {len(info['agents'])}")
            logger.info(f"    - Connections: {len(info['connections'])}")
        
        # Pause one of the circuits
        logger.info("Pausing the sequential circuit...")
        await circuit_designer.pause_circuit(sequential_id)
        
        # Resume the circuit
        logger.info("Resuming the sequential circuit...")
        await circuit_designer.resume_circuit(sequential_id)
        
        # Create a more complex circuit with filtered connections
        logger.info("Creating a more complex circuit with filtered connections...")
        complex_circuit_def = CircuitDefinition.create(
            name="ComplexCircuit",
            description="A circuit with filtered connections",
            agents={
                "input": {
                    "type": "ReflexAgent",
                    "role": "INPUT",
                    "name": "Input Agent"
                },
                "filter": {
                    "type": "ReflexAgent",
                    "role": "PROCESSOR",
                    "name": "Filter Agent"
                },
                "processor_high": {
                    "type": "DeliberativeAgent",
                    "role": "PROCESSOR",
                    "name": "High Priority Processor"
                },
                "processor_low": {
                    "type": "DeliberativeAgent",
                    "role": "PROCESSOR",
                    "name": "Low Priority Processor"
                },
                "output": {
                    "type": "ReflexAgent",
                    "role": "OUTPUT",
                    "name": "Output Agent"
                }
            },
            connections=[
                {
                    "source": "input",
                    "target": "filter",
                    "connection_type": "direct"
                },
                {
                    "source": "filter",
                    "target": "processor_high",
                    "connection_type": "filtered",
                    "metadata": {
                        "filter_condition": "message.content.get('priority', 0) > 5"
                    }
                },
                {
                    "source": "filter",
                    "target": "processor_low",
                    "connection_type": "filtered",
                    "metadata": {
                        "filter_condition": "message.content.get('priority', 0) <= 5"
                    }
                },
                {
                    "source": "processor_high",
                    "target": "output",
                    "connection_type": "direct"
                },
                {
                    "source": "processor_low",
                    "target": "output",
                    "connection_type": "direct"
                }
            ]
        )
        
        # Create and deploy the complex circuit
        complex_id = await circuit_designer.create_circuit(complex_circuit_def)
        logger.info(f"Created complex circuit with ID: {complex_id}")
        
        await circuit_designer.deploy_circuit(complex_id)
        
        # Send inputs with different priorities
        logger.info("Sending inputs to complex circuit with different priorities...")
        await circuit_designer.send_input(
            complex_id,
            {
                "type": "task",
                "description": "High priority task",
                "priority": 8
            }
        )
        
        await circuit_designer.send_input(
            complex_id,
            {
                "type": "task",
                "description": "Low priority task",
                "priority": 3
            }
        )
        
        # Wait for processing to complete
        await asyncio.sleep(2.0)
        
        # Terminate all circuits
        logger.info("Terminating circuits...")
        for circuit_id in [sequential_id, star_id, template_id, complex_id]:
            await circuit_designer.terminate_circuit(circuit_id)
        
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.exception(f"Error in example: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Use the run_context to ensure proper cleanup
    with run_context() as core:
        exit_code = asyncio.run(main())
    
    import sys
    sys.exit(exit_code)
"""
