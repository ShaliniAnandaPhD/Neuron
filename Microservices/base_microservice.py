from typing import Dict, Any, List, Optional
import json
import uuid
import logging
import os
import time
from abc import ABC, abstractmethod

class BaseMicroservice(ABC):
    """Base class for all Neuron microservices."""
    
    def __init__(self, name: str, description: Optional[str] = None):
        """Initialize base microservice.
        
        Args:
            name: Name of the microservice
            description: Optional description of the microservice
        """
        self.name = name
        self.description = description
        self.id = str(uuid.uuid4())
        self.agents = {}
        self.is_deployed = False
        self.circuit = None
        self.timeout_seconds = 10.0  # how long process() waits for output
        self.metrics = {"requests": 0, "errors": 0, "total_seconds": 0.0}

        # Log to logs/<name>.log next to this file. The handler goes on this
        # microservice's logger only, so the host application's logging
        # configuration is left alone (basicConfig used to replace it).
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.FileHandler(
                os.path.join(log_dir, f"{self.name.replace(' ', '_').lower()}.log")
            )
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)
        
        # Initialize derived class-specific components
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Initialize microservice-specific components.
        
        This method should be implemented by derived classes to initialize
        their specific agents and other components.
        """
        pass
    
    @abstractmethod
    def get_circuit_definition(self):
        """Get the circuit definition for the microservice.
        
        This method should be implemented by derived classes to define
        the circuit of agents and their connections.
        
        Returns:
            CircuitDefinition object that defines the microservice circuit
        """
        pass
    
    def deploy(self):
        """Deploy the microservice.
        
        This method initializes the circuit and makes the microservice
        ready to process requests.
        """
        if self.is_deployed:
            self.logger.warning(f"Microservice {self.name} is already deployed")
            return
        
        try:
            self.circuit = self.get_circuit_definition()
            self.is_deployed = True
            self.logger.info(f"Microservice {self.name} deployed successfully")
        except Exception as e:
            self.logger.error(f"Failed to deploy microservice {self.name}: {str(e)}")
            raise
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data through the microservice circuit.
        
        Args:
            input_data: Input data to process
            
        Returns:
            Processed output data
        """
        if not self.is_deployed:
            self.logger.error(f"Microservice {self.name} is not deployed")
            raise RuntimeError(f"Microservice {self.name} is not deployed")
        
        # Imported here so the microservice classes can be defined (and their
        # agents unit tested) without starting the framework.
        from neuron import initialize

        started = time.monotonic()
        self.metrics["requests"] += 1
        try:
            self.logger.info(f"Processing input: {json.dumps(input_data)[:100]}...")

            # Run the request through a Neuron circuit on the caller's event
            # loop: deploy, send the input, wait for the OUTPUT agent's reply.
            core = initialize()
            core.start()
            try:
                for agent in self.agents.values():
                    core.agent_manager.register_agent_type(type(agent))
                circuit_id = await core.circuit_designer.create_and_deploy(self.circuit)
                await core.circuit_designer.send_input(circuit_id, input_data)
                output = await core.circuit_designer.get_output(
                    circuit_id, timeout=self.timeout_seconds
                )
                await core.circuit_designer.terminate_circuit(circuit_id)
            finally:
                await core.shutdown_async()

            self.logger.info("Processing complete")
            return output["content"]
        except Exception as e:
            self.metrics["errors"] += 1
            self.logger.error(f"Error processing input: {str(e)}")
            raise
        finally:
            self.metrics["total_seconds"] += time.monotonic() - started
    
    def get_metrics(self) -> Dict[str, Any]:
        """Request counts and average processing time since startup."""
        requests = self.metrics["requests"]
        return {
            "name": self.name,
            "deployed": self.is_deployed,
            "requests": requests,
            "errors": self.metrics["errors"],
            "avg_seconds": self.metrics["total_seconds"] / requests if requests else 0.0,
        }
