from typing import Dict, Any, List, Optional
import json
import uuid
import logging
import os
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
        
        # Set up logging
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(log_dir, f"{self.name.replace(' ', '_').lower()}.log"),
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.name)
        
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
        
        try:
            self.logger.info(f"Processing input: {json.dumps(input_data)[:100]}...")
            result = await self.circuit.run(input_data)
            self.logger.info(f"Processing complete")
            return result
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}")
            raise
