"""
Circuit Router Module for Neuron Architecture

Handles dynamic routing of information between agents and memory systems
based on context, confidence, and execution state.

Author: [Your Name]
Created: May 12, 2025
"""

import logging
import uuid
import time
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Route:
    """Data class representing a routing path between components."""
    route_id: str
    source_id: str
    target_id: str
    condition: Optional[Callable] = None
    transformation: Optional[Callable] = None
    priority: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class CircuitRouter:
    """
    Manages the dynamic routing of information through the circuit,
    adapting execution paths based on real-time feedback and context.
    """
    
    def __init__(self, synaptic_bus, config: Dict[str, Any]):
        """
        Initialize the CircuitRouter with connection to the synaptic bus
        and configuration parameters.
        
        Args:
            synaptic_bus: Central messaging system
            config: Configuration parameters for routing decisions
        """
        self.synaptic_bus = synaptic_bus
        self.config = config
        self.routes: Dict[str, Route] = {}
        self.route_history: List[Dict[str, Any]] = []
        self.execution_state: Dict[str, Any] = {}
        
        # Initialize reliability router if available
        self.reliability_router = None
        if config.get("use_reliability_routing", False):
            try:
                from neuron.integration.reliability_router import ReliabilityRouter
                self.reliability_router = ReliabilityRouter(config.get("reliability_config", {}))
                logger.info("ReliabilityRouter initialized for CircuitRouter")
            except ImportError:
                logger.warning("ReliabilityRouter not available, falling back to static routing")
        
        # Register with synaptic bus for message routing
        self._register_message_handlers()
    
    def _register_message_handlers(self) -> None:
        """Register message handlers with the synaptic bus."""
        self.synaptic_bus.register_handler(
            topic="circuit.route_request", 
            handler=self._handle_route_request
        )
        self.synaptic_bus.register_handler(
            topic="circuit.route_feedback", 
            handler=self._handle_route_feedback
        )
        logger.debug("CircuitRouter registered message handlers with SynapticBus")
    
    def _handle_route_request(self, message: Dict[str, Any]) -> None:
        """
        Handle routing requests from the synaptic bus.
        
        Args:
            message: Routing request message
        """
        source_id = message.get("source_id")
        data = message.get("data")
        context = message.get("context", {})
        
        if not source_id or data is None:
            logger.warning("Invalid route request: missing source_id or data")
            return
        
        # Find and execute applicable routes
        targets = self._find_applicable_routes(source_id, data, context)
        
        for target_id, route_id, transformed_data in targets:
            self._record_route_execution(route_id, source_id, target_id, data, transformed_data)
            self.synaptic_bus.publish(
                topic=f"component.{target_id}.input",
                message={
                    "source_id": source_id,
                    "data": transformed_data,
                    "context": context,
                    "route_id": route_id
                }
            )
            logger.debug(f"Routed message from {source_id} to {target_id} via route {route_id}")
    
    def _handle_route_feedback(self, message: Dict[str, Any]) -> None:
        """
        Handle feedback about route effectiveness.
        
        Args:
            message: Feedback message about route performance
        """
        route_id = message.get("route_id")
        success = message.get("success", True)
        confidence = message.get("confidence", 1.0)
        latency = message.get("latency")
        
        if not route_id or route_id not in self.routes:
            logger.warning(f"Feedback for unknown route: {route_id}")
            return
        
        feedback_data = {
            "route_id": route_id,
            "timestamp": message.get("timestamp", time.time()),
            "success": success,
            "confidence": confidence,
            "latency": latency,
            "metadata": message.get("metadata", {})
        }
        
        # Record feedback for future adaptation
        if "feedback_history" not in self.routes[route_id].metadata:
            self.routes[route_id].metadata["feedback_history"] = []
            
        self.routes[route_id].metadata["feedback_history"].append(feedback_data)
        
        # Update reliability metrics if available
        if self.reliability_router:
            source_id = self.routes[route_id].source_id
            target_id = self.routes[route_id].target_id
            self.reliability_router.update_reliability(
                source_id=source_id,
                target_id=target_id,
                success=success,
                confidence=confidence,
                latency=latency
            )
        
        logger.debug(f"Recorded feedback for route {route_id}: success={success}, confidence={confidence}")
    
    def register_route(self, source_id: str, target_id: str, 
                      condition: Optional[Callable] = None, 
                      transformation: Optional[Callable] = None,
                      priority: int = 0,
                      metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a potential route between components with optional
        conditional execution and data transformation.
        
        Args:
            source_id: ID of the source component
            target_id: ID of the target component
            condition: Optional function to determine if route should be taken
            transformation: Optional function to transform data before routing
            priority: Route priority (higher values = higher priority)
            metadata: Additional metadata about the route
            
        Returns:
            route_id: Unique identifier for the registered route
        """
        route_id = str(uuid.uuid4())
        
        route = Route(
            route_id=route_id,
            source_id=source_id,
            target_id=target_id,
            condition=condition,
            transformation=transformation,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.routes[route_id] = route
        logger.info(f"Registered route from {source_id} to {target_id} with ID {route_id}")
        
        return route_id
    
    def update_route(self, route_id: str, 
                    condition: Optional[Callable] = None,
                    transformation: Optional[Callable] = None,
                    priority: Optional[int] = None) -> bool:
        """
        Update an existing route's properties.
        
        Args:
            route_id: ID of the route to update
            condition: New condition function (or None to keep existing)
            transformation: New transformation function (or None to keep existing)
            priority: New priority (or None to keep existing)
            
        Returns:
            success: Whether the update was successful
        """
        if route_id not in self.routes:
            logger.warning(f"Cannot update non-existent route: {route_id}")
            return False
            
        route = self.routes[route_id]
        
        if condition is not None:
            route.condition = condition
            
        if transformation is not None:
            route.transformation = transformation
            
        if priority is not None:
            route.priority = priority
            
        logger.debug(f"Updated route {route_id} properties")
        return True
    
    def remove_route(self, route_id: str) -> bool:
        """
        Remove a registered route.
        
        Args:
            route_id: ID of the route to remove
            
        Returns:
            success: Whether the removal was successful
        """
        if route_id not in self.routes:
            logger.warning(f"Cannot remove non-existent route: {route_id}")
            return False
            
        source_id = self.routes[route_id].source_id
        target_id = self.routes[route_id].target_id
        del self.routes[route_id]
        
        logger.info(f"Removed route {route_id} from {source_id} to {target_id}")
        return True
    
    def _find_applicable_routes(self, source_id: str, data: Any, 
                               context: Dict[str, Any]) -> List[Tuple[str, str, Any]]:
        """
        Find all applicable routes for the given source and data.
        
        Args:
            source_id: ID of the source component
            data: Data to be routed
            context: Context information for condition evaluation
            
        Returns:
            List of tuples (target_id, route_id, transformed_data)
        """
        applicable_routes = []
        
        # Find routes where source matches and condition evaluates to True
        for route_id, route in self.routes.items():
            if route.source_id != source_id:
                continue
                
            # Check condition if provided
            if route.condition and not route.condition(data, context):
                continue
                
            # Apply transformation if provided
            transformed_data = data
            if route.transformation:
                try:
                    transformed_data = route.transformation(data, context)
                except Exception as e:
                    logger.error(f"Error in transformation for route {route_id}: {e}")
                    continue
            
            applicable_routes.append((route.target_id, route_id, transformed_data, route.priority))
        
        # Sort by priority (descending)
        applicable_routes.sort(key=lambda x: x[3], reverse=True)
        
        # Remove priority from result
        return [(target_id, route_id, data) for target_id, route_id, data, _ in applicable_routes]
    
    def _record_route_execution(self, route_id: str, source_id: str, 
                              target_id: str, input_data: Any, 
                              output_data: Any) -> None:
        """
        Record route execution for history and analysis.
        
        Args:
            route_id: ID of the executed route
            source_id: ID of the source component
            target_id: ID of the target component
            input_data: Original input data
            output_data: Transformed output data
        """
        record = {
            "timestamp": self.synaptic_bus.get_current_time(),
            "route_id": route_id,
            "source_id": source_id,
            "target_id": target_id,
            "has_transformation": input_data is not output_data
        }
        
        self.route_history.append(record)
        
        # Limit history size
        max_history = self.config.get("max_route_history", 1000)
        if len(self.route_history) > max_history:
            self.route_history = self.route_history[-max_history:]
    
    def get_route_history(self, limit: Optional[int] = None, 
                         route_id: Optional[str] = None, 
                         source_id: Optional[str] = None,
                         target_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get route execution history with optional filtering.
        
        Args:
            limit: Maximum number of history items to return
            route_id: Filter by specific route
            source_id: Filter by source component
            target_id: Filter by target component
            
        Returns:
            Filtered route history
        """
        filtered_history = self.route_history
        
        if route_id:
            filtered_history = [h for h in filtered_history if h["route_id"] == route_id]
            
        if source_id:
            filtered_history = [h for h in filtered_history if h["source_id"] == source_id]
            
        if target_id:
            filtered_history = [h for h in filtered_history if h["target_id"] == target_id]
            
        if limit:
            filtered_history = filtered_history[-limit:]
            
        return filtered_history
    
    def adapt_routes(self) -> None:
        """
        Adapt routing strategies based on execution feedback
        and performance metrics.
        """
        if not self.reliability_router:
            logger.debug("Route adaptation skipped: ReliabilityRouter not available")
            return
            
        # For each route, check if we have better alternatives based on reliability
        for route_id, route in list(self.routes.items()):
            source_id = route.source_id
            current_target = route.target_id
            
            # Get alternative targets with higher reliability
            alternatives = self.reliability_router.get_alternatives(
                source_id=source_id,
                current_target=current_target
            )
            
            if not alternatives:
                continue
                
            # For now, just log the suggestion - could automatically update routes
            best_alternative, reliability = alternatives[0]
            logger.info(
                f"Route adaptation suggestion: {source_id} → {current_target} "
                f"could be improved by routing to {best_alternative} "
                f"(reliability: {reliability:.2f})"
            )
    
    def execute_routing(self, circuit_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the routing logic based on the current circuit state,
        determining which components should receive which information.
        
        Args:
            circuit_state: Current state of the circuit execution
            
        Returns:
            updated_state: Updated circuit state after routing
        """
        # Update internal execution state
        self.execution_state.update(circuit_state)
        
        # Process any pending route adaptations
        if self.config.get("auto_adapt_routes", False):
            self.adapt_routes()
            
        # Return the updated state
        return self.execution_state
    
    def get_routes_for_source(self, source_id: str) -> List[Route]:
        """
        Get all routes registered for a specific source component.
        
        Args:
            source_id: ID of the source component
            
        Returns:
            routes: List of routes for the source
        """
        return [route for route in self.routes.values() if route.source_id == source_id]
    
    def get_routes_for_target(self, target_id: str) -> List[Route]:
        """
        Get all routes registered for a specific target component.
        
        Args:
            target_id: ID of the target component
            
        Returns:
            routes: List of routes for the target
        """
        return [route for route in self.routes.values() if route.target_id == target_id]
    
    def clear_routes(self) -> None:
        """Clear all registered routes."""
        route_count = len(self.routes)
        self.routes.clear()
        logger.info(f"Cleared {route_count} routes from CircuitRouter")
    
    def get_route_feedback_stats(self, route_id: str) -> Dict[str, Any]:
        """
        Get statistics about a route's feedback history.
        
        Args:
            route_id: ID of the route
            
        Returns:
            stats: Dictionary with feedback statistics
        """
        if route_id not in self.routes:
            logger.warning(f"Cannot get stats for non-existent route: {route_id}")
            return {}
            
        route = self.routes[route_id]
        feedback_history = route.metadata.get("feedback_history", [])
        
        if not feedback_history:
            return {
                "count": 0,
                "success_rate": None,
                "avg_confidence": None,
                "avg_latency": None
            }
            
        success_count = sum(1 for f in feedback_history if f.get("success", False))
        confidences = [f.get("confidence", 0.0) for f in feedback_history if f.get("confidence") is not None]
        latencies = [f.get("latency") for f in feedback_history if f.get("latency") is not None]
        
        stats = {
            "count": len(feedback_history),
            "success_rate": success_count / len(feedback_history) if feedback_history else 0,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
            "avg_latency": sum(latencies) / len(latencies) if latencies else None
        }
        
        return stats

# Circuit Router Summary
# ---------------------
# The CircuitRouter module implements a dynamic routing system for the Neuron architecture 
# that controls the flow of information between different components in the neural circuit.
# 
# Key features:
# 
# 1. Dynamic Route Management: 
#    - Registers, updates, and removes routes between components
#    - Defines conditions for when routes should be active
#    - Allows for data transformations between components
# 
# 2. Intelligent Routing Decisions:
#    - Routes messages based on source, content, and context
#    - Prioritizes routes using configurable priorities
#    - Evaluates conditions to determine which routes apply
# 
# 3. Feedback-Based Adaptation:
#    - Collects feedback on route performance (success, confidence, latency)
#    - Analyzes historical performance to suggest better routing
#    - Integrates with the ReliabilityRouter for trust-based routing
# 
# 4. Execution Tracing:
#    - Records detailed history of routing actions
#    - Provides filtering and querying of route history
#    - Supports debugging and performance analysis
# 
# 5. Integration with Synaptic Bus:
#    - Registers handlers for routing requests
#    - Handles message passing between components
#    - Publishes transformed data to target components
# 
# This module is a critical part of the Neuron architecture, enabling flexible,
# context-sensitive information flow that can adapt to changing conditions and
# component performance. It effectively serves as the "nervous system" of the
# AI framework, directing signals between various cognitive components and memory systems.
