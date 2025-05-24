"""
Simple Agent Example

This example demonstrates how to create and use basic agents in the Neuron framework.
"""

import asyncio
import logging
from neuron import (
    initialize, start, shutdown,
    BaseAgent, ReflexAgent, DeliberativeAgent, LearningAgent,
    Message
)


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main example function."""
    try:
        # Initialize and start the framework
        logger.info("Initializing Neuron framework...")
        core = initialize()
        start()
        
        logger.info("Framework initialized and started")
        
        # Get the agent manager
        agent_manager = core.agent_manager
        
        # Create a reflex agent
        logger.info("Creating a ReflexAgent...")
        reflex_config = {
            "agent_type": ReflexAgent,
            "name": "MyReflexAgent",
            "description": "A simple reflex agent",
            "metadata": {"created_by": "example"},
            "config_params": {}
        }
        reflex_id = agent_manager.create_agent(reflex_config)
        logger.info(f"Created ReflexAgent with ID: {reflex_id}")
        
        # Create a deliberative agent
        logger.info("Creating a DeliberativeAgent...")
        deliberative_config = {
            "agent_type": DeliberativeAgent,
            "name": "MyDeliberativeAgent",
            "description": "A simple deliberative agent",
            "metadata": {"created_by": "example"},
            "config_params": {
                "planning_depth": 4,
                "evaluation_criteria": {
                    "efficiency": 0.4,
                    "completeness": 0.3,
                    "reliability": 0.3
                }
            }
        }
        deliberative_id = agent_manager.create_agent(deliberative_config)
        logger.info(f"Created DeliberativeAgent with ID: {deliberative_id}")
        
        # Create a learning agent
        logger.info("Creating a LearningAgent...")
        learning_config = {
            "agent_type": LearningAgent,
            "name": "MyLearningAgent",
            "description": "A simple learning agent",
            "metadata": {"created_by": "example"},
            "config_params": {
                "learning_rate": 0.2,
                "exploration_rate": 0.3
            }
        }
        learning_id = agent_manager.create_agent(learning_config)
        logger.info(f"Created LearningAgent with ID: {learning_id}")
        
        # Start the agents
        logger.info("Starting agents...")
        agent_manager.start_agent(reflex_id)
        agent_manager.start_agent(deliberative_id)
        agent_manager.start_agent(learning_id)
        
        # Get references to the agent instances
        reflex_agent = agent_manager.get_agent(reflex_id)
        deliberative_agent = agent_manager.get_agent(deliberative_id)
        learning_agent = agent_manager.get_agent(learning_id)
        
        # Accessing agent capabilities
        logger.info("Agent capabilities:")
        for agent_id, agent in [
            (reflex_id, reflex_agent),
            (deliberative_id, deliberative_agent),
            (learning_id, learning_agent)
        ]:
            capabilities = agent.get_capabilities()
            logger.info(f"  {agent.name} ({agent_id}): {[c.name for c in capabilities]}")
        
        # Send a message to each agent
        logger.info("Sending messages to agents...")
        
        # Create and send messages
        messages = []
        
        # Message to reflex agent
        reflex_message = asyncio.run(_create_message(
            core, "example",
            [reflex_id],
            "This is a test message for the reflex agent"
        ))
        messages.append(reflex_message)
        
        # Message to deliberative agent
        deliberative_message = asyncio.run(_create_message(
            core, "example",
            [deliberative_id],
            {
                "type": "decision_request",
                "options": ["A", "B", "C"],
                "context": "Example decision context"
            }
        ))
        messages.append(deliberative_message)
        
        # Message to learning agent
        learning_message = asyncio.run(_create_message(
            core, "example",
            [learning_id],
            {
                "type": "pattern_input",
                "pattern_key": "example_pattern",
                "pattern_value": 42
            }
        ))
        messages.append(learning_message)
        
        # Wait a bit for processing
        logger.info("Waiting for message processing...")
        import time
        time.sleep(2.0)
        
        # Get agent metrics
        logger.info("Agent metrics:")
        for agent_id, agent in [
            (reflex_id, reflex_agent),
            (deliberative_id, deliberative_agent),
            (learning_id, learning_agent)
        ]:
            metrics = agent.get_metrics()
            logger.info(f"  {agent.name} ({agent_id}):")
            logger.info(f"    - Message count: {metrics.message_count}")
            logger.info(f"    - Processing time: {metrics.processing_time:.4f}s")
            logger.info(f"    - Error count: {metrics.error_count}")
        
        # Create a custom agent by subclassing BaseAgent
        logger.info("Creating a custom agent...")
        
        class CustomAgent(BaseAgent):
            """A custom agent implementation."""
            
            def _initialize(self) -> None:
                """Agent-specific initialization."""
                logger.info(f"CustomAgent {self.id} initialized")
            
            async def process_message(self, message: Message) -> None:
                """Process a received message."""
                logger.info(f"CustomAgent {self.id} processing message: {message.content}")
                
                # Echo the message back to the sender
                await self.send_message(
                    recipients=[message.sender],
                    content=f"Echo from CustomAgent: {message.content}",
                    metadata={"in_response_to": message.id}
                )
        
        # Register the custom agent type
        agent_manager.register_agent_type(CustomAgent)
        
        # Create a custom agent instance
        custom_config = {
            "agent_type": CustomAgent,
            "name": "MyCustomAgent",
            "description": "A custom agent implementation",
            "metadata": {"created_by": "example"}
        }
        custom_id = agent_manager.create_agent(custom_config)
        logger.info(f"Created CustomAgent with ID: {custom_id}")
        
        # Start the custom agent
        agent_manager.start_agent(custom_id)
        
        # Send a message to the custom agent
        custom_message = asyncio.run(_create_message(
            core, "example",
            [custom_id],
            "Hello, CustomAgent!"
        ))
        
        # Wait a bit for processing
        time.sleep(1.0)
        
        # Shutdown
        logger.info("Shutting down framework...")
        shutdown()
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.exception(f"Error in example: {e}")
        shutdown()
        return 1
    
    return 0


async def _create_message(core, sender, recipients, content):
    """Helper to create and send a message."""
    message = Message.create(
        sender=sender,
        recipients=recipients,
        content=content
    )
    
    await core.synaptic_bus.send(message)
    return message


if __name__ == "__main__":
    exit_code = main()
    import sys
    sys.exit(exit_code)
"""
