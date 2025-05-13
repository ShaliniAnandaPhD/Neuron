"""
Fallback Handler Module for Neuron Architecture

Provides standardized error handling and fallback mechanisms
when agents fail or return low-confidence results.

"""

import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from enum import Enum, auto
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class FailureType(Enum):
    """Types of agent failures that can occur."""
    TIMEOUT = auto()            # Agent took too long to respond
    EXCEPTION = auto()          # Agent threw an exception
    EMPTY_RESULT = auto()       # Agent returned no result
    LOW_CONFIDENCE = auto()     # Agent returned result with low confidence
    INVALID_FORMAT = auto()     # Agent returned improperly formatted result
    CONSISTENCY_ERROR = auto()  # Agent result inconsistent with other agents/context
    HALLUCINATION = auto()      # Agent provided information not grounded in facts
    AUTHORIZATION = auto()      # Agent lacked permission for requested action
    RESOURCE_LIMIT = auto()     # Agent hit resource/rate limits
    CONNECTION_ERROR = auto()   # Agent couldn't connect to required service
    OTHER = auto()              # Unclassified failure

class FallbackStrategy(Enum):
    """Available strategies for handling agent failures."""
    RETRY = auto()              # Retry the same agent with same input
    RETRY_WITH_BACKOFF = auto() # Retry with exponential backoff
    RETRY_WITH_PARAMS = auto()  # Retry with modified parameters
    ALTERNATIVE_AGENT = auto()  # Route to an alternative agent
    DECOMPOSE_TASK = auto()     # Break task into simpler sub-tasks
    DEFAULT_VALUE = auto()      # Return a safe default value
    HUMAN_ESCALATION = auto()   # Escalate to human operator
    GRACEFUL_DEGRADATION = auto() # Continue with reduced functionality
    ABORT = auto()              # Abort the current operation
    CACHED_RESULT = auto()      # Use cached result from previous execution
    USER_PROMPT = auto()        # Ask user how to proceed

@dataclass
class FailureRecord:
    """Record of an agent failure occurrence."""
    failure_id: str
    agent_id: str
    failure_type: FailureType
    timestamp: float
    input_data: Any
    error_message: str
    error_details: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None

@dataclass
class FallbackResult:
    """Result of a fallback operation."""
    success: bool
    fallback_id: str
    agent_id: str
    original_failure: FailureRecord
    strategy_used: FallbackStrategy
    result_data: Any
    confidence: float = 0.0
    execution_time: float = 0.0
    attempts: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

class FallbackHandler:
    """
    Provides error handling and fallback mechanisms when agents fail
    or return low-confidence results.
    """
    
    def __init__(self, config: Dict[str, Any], circuit_router=None):
        """
        Initialize the fallback handler with configuration parameters.
        
        Args:
            config: Configuration for fallback behavior
            circuit_router: Optional reference to circuit router for rerouting
        """
        # Configuration parameters
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.max_retry_attempts = config.get("max_retry_attempts", 3)
        self.backoff_base = config.get("backoff_base", 2.0)
        self.timeout_threshold = config.get("timeout_threshold", 30.0)  # seconds
        self.failure_history_limit = config.get("failure_history_limit", 1000)
        
        # Default strategies for different failure types
        self.default_strategies = config.get("default_strategies", {
            FailureType.TIMEOUT.name: FallbackStrategy.RETRY_WITH_BACKOFF.name,
            FailureType.EXCEPTION.name: FallbackStrategy.RETRY.name,
            FailureType.EMPTY_RESULT.name: FallbackStrategy.ALTERNATIVE_AGENT.name,
            FailureType.LOW_CONFIDENCE.name: FallbackStrategy.ALTERNATIVE_AGENT.name,
            FailureType.INVALID_FORMAT.name: FallbackStrategy.RETRY_WITH_PARAMS.name,
            FailureType.CONSISTENCY_ERROR.name: FallbackStrategy.DECOMPOSE_TASK.name,
            FailureType.HALLUCINATION.name: FallbackStrategy.ALTERNATIVE_AGENT.name,
            FailureType.AUTHORIZATION.name: FallbackStrategy.HUMAN_ESCALATION.name,
            FailureType.RESOURCE_LIMIT.name: FallbackStrategy.RETRY_WITH_BACKOFF.name,
            FailureType.CONNECTION_ERROR.name: FallbackStrategy.RETRY_WITH_BACKOFF.name,
            FailureType.OTHER.name: FallbackStrategy.ALTERNATIVE_AGENT.name
        })
        
        # Convert string enum names to actual enum values
        self.default_strategies = {
            FailureType[k] if isinstance(k, str) else k: 
            FallbackStrategy[v] if isinstance(v, str) else v 
            for k, v in self.default_strategies.items()
        }
        
        # Alternative agent mappings
        self.alternative_agents = config.get("alternative_agents", {})
        
        # Custom handlers for specific failure types
        self.custom_handlers = {}
        
        # Circuit router reference for rerouting
        self.circuit_router = circuit_router
        
        # State
        self.failure_history: List[FailureRecord] = []
        self.fallback_history: List[FallbackResult] = []
        self.agent_performance_stats: Dict[str, Dict[str, Any]] = {}
        
        # Register trace logger if available
        self.trace_logger = None
        try:
            from neuron.observability.trace_logger import TraceLogger
            if "trace_logger" in config:
                self.trace_logger = config["trace_logger"]
                logger.info("Using provided TraceLogger for fallback tracking")
        except ImportError:
            logger.debug("TraceLogger not available for fallback tracking")
            
        # Load simulation planner if available
        self.simulation_planner = None
        try:
            from neuron.agents.simulation_planner import SimulationPlanner
            if "simulation_planner" in config:
                self.simulation_planner = config["simulation_planner"]
                logger.info("Using provided SimulationPlanner for predictive fallbacks")
        except ImportError:
            logger.debug("SimulationPlanner not available for predictive fallbacks")
            
        logger.info(f"Initialized FallbackHandler with confidence_threshold={self.confidence_threshold}, "
                  f"max_retry_attempts={self.max_retry_attempts}")
    
    def handle_failure(self, agent_id: str, failure_type: Union[str, FailureType], 
                     input_data: Any, error_message: str = "",
                     error_details: Optional[Dict[str, Any]] = None,
                     context: Optional[Dict[str, Any]] = None) -> FallbackResult:
        """
        Handle an agent failure by applying appropriate fallback strategies.
        
        Args:
            agent_id: ID of the failed agent
            failure_type: Type of failure that occurred
            input_data: Input that was provided to the agent
            error_message: Error message from the failure
            error_details: Additional details about the error
            context: Execution context when the failure occurred
            
        Returns:
            result: Result of the fallback operation
        """
        # Convert string failure type to enum if needed
        if isinstance(failure_type, str):
            try:
                failure_type = FailureType[failure_type.upper()]
            except KeyError:
                logger.warning(f"Unknown failure type: {failure_type}, using OTHER")
                failure_type = FailureType.OTHER
                
        # Create failure record
        failure_record = FailureRecord(
            failure_id=str(uuid.uuid4()),
            agent_id=agent_id,
            failure_type=failure_type,
            timestamp=time.time(),
            input_data=input_data,
            error_message=error_message,
            error_details=error_details or {},
            context=context or {},
            trace_id=context.get("trace_id") if context else None
        )
        
        # Add to history
        self._add_to_failure_history(failure_record)
        
        # Log the failure
        self._log_failure(failure_record)
        
        # Determine appropriate fallback strategy
        strategy = self._determine_strategy(failure_record)
        
        # Apply strategy
        start_time = time.time()
        result = self._apply_strategy(strategy, failure_record)
        execution_time = time.time() - start_time
        
        # Update result with execution time
        result.execution_time = execution_time
        
        # Add to fallback history
        self._add_to_fallback_history(result)
        
        # Log the fallback result
        self._log_fallback_result(result)
        
        # Update agent performance statistics
        self._update_agent_stats(agent_id, failure_type, strategy, result.success)
        
        return result
    
    def register_custom_handler(self, failure_type: Union[str, FailureType], 
                              handler: Callable[[FailureRecord], Any]) -> None:
        """
        Register a custom handler function for a specific failure type.
        
        Args:
            failure_type: Type of failure to handle
            handler: Function to call when this failure occurs
        """
        # Convert string failure type to enum if needed
        if isinstance(failure_type, str):
            try:
                failure_type = FailureType[failure_type.upper()]
            except KeyError:
                logger.warning(f"Unknown failure type: {failure_type}, using OTHER")
                failure_type = FailureType.OTHER
                
        self.custom_handlers[failure_type] = handler
        logger.info(f"Registered custom handler for {failure_type.name}")
    
    def register_alternative_agent(self, primary_agent_id: str, 
                                 alternative_agent_id: str,
                                 for_failure_types: Optional[List[Union[str, FailureType]]] = None) -> None:
        """
        Register an alternative agent to use when a primary agent fails.
        
        Args:
            primary_agent_id: ID of the primary agent
            alternative_agent_id: ID of the alternative agent
            for_failure_types: Optional list of failure types this alternative handles
        """
        if primary_agent_id not in self.alternative_agents:
            self.alternative_agents[primary_agent_id] = []
            
        # Convert string failure types to enum if provided
        if for_failure_types:
            failure_types = []
            for ft in for_failure_types:
                if isinstance(ft, str):
                    try:
                        ft = FailureType[ft.upper()]
                    except KeyError:
                        logger.warning(f"Unknown failure type: {ft}, using OTHER")
                        ft = FailureType.OTHER
                failure_types.append(ft)
        else:
            failure_types = None
            
        # Add to alternatives with optional failure type specificity
        self.alternative_agents[primary_agent_id].append({
            "agent_id": alternative_agent_id,
            "failure_types": failure_types
        })
        
        logger.info(f"Registered alternative agent {alternative_agent_id} for {primary_agent_id}")
    
    def check_result_confidence(self, agent_id: str, result: Any, 
                              context: Optional[Dict[str, Any]] = None) -> Union[Any, FallbackResult]:
        """
        Check if an agent result has sufficient confidence, apply fallback if not.
        
        Args:
            agent_id: ID of the agent
            result: Result from the agent
            context: Execution context
            
        Returns:
            result: Original result if confident, fallback result if not
        """
        # Extract confidence from result if available
        confidence = 0.0
        
        if isinstance(result, dict):
            # Check for confidence in result dictionary
            confidence = result.get("confidence", 0.0)
        elif hasattr(result, "confidence"):
            # Check for confidence attribute
            confidence = result.confidence
        elif context and "confidence" in context:
            # Check for confidence in context
            confidence = context["confidence"]
            
        # If confidence is below threshold, handle as a low confidence failure
        if confidence < self.confidence_threshold:
            logger.debug(f"Low confidence result ({confidence:.3f} < {self.confidence_threshold}) from {agent_id}")
            
            return self.handle_failure(
                agent_id=agent_id,
                failure_type=FailureType.LOW_CONFIDENCE,
                input_data=result,  # Input data is the result itself
                error_message=f"Low confidence: {confidence:.3f} < {self.confidence_threshold}",
                context=context or {}
            )
            
        # Otherwise, return the original result
        return result
    
    def predict_potential_failures(self, agent_id: str, input_data: Any,
                                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Proactively predict potential failures before execution.
        
        Args:
            agent_id: ID of the agent
            input_data: Input data to be sent to the agent
            context: Execution context
            
        Returns:
            prediction: Dictionary of failure predictions
        """
        # Default prediction
        prediction = {
            "potential_failures": [],
            "failure_probability": 0.0,
            "recommendation": None
        }
        
        # Use history to identify common failure patterns
        agent_failures = [f for f in self.failure_history if f.agent_id == agent_id]
        
        # If no history, return default prediction
        if not agent_failures:
            return prediction
            
        # Calculate basic failure statistics
        failure_count = len(agent_failures)
        failure_types = {}
        
        for failure in agent_failures:
            failure_type = failure.failure_type
            if failure_type not in failure_types:
                failure_types[failure_type] = 0
            failure_types[failure_type] += 1
            
        # Calculate failure probabilities by type
        total_failures = sum(failure_types.values())
        failure_probabilities = {
            ft: count / total_failures
            for ft, count in failure_types.items()
        }
        
        # Sort by probability (highest first)
        sorted_failures = sorted(
            failure_probabilities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Use simulation planner if available for more detailed prediction
        if self.simulation_planner:
            try:
                # Create an action representing the agent execution
                action = {
                    "type": "agent_execution",
                    "agent_id": agent_id,
                    "input_data": input_data,
                    "context": context
                }
                
                # Simulate the action
                simulation = self.simulation_planner.simulate_action(
                    action=action,
                    current_state=context or {},
                    agent_id="fallback_handler"
                )
                
                # Extract risks that look like failures
                if simulation.risks:
                    for risk in simulation.risks:
                        risk_prob = risk.get("probability", 0)
                        risk_severity = risk.get("severity", 0)
                        risk_desc = risk.get("description", "")
                        
                        # Map risk to failure type if possible
                        failure_type = None
                        for ft in FailureType:
                            if ft.name.lower() in risk_desc.lower():
                                failure_type = ft
                                break
                                
                        if failure_type:
                            prediction["potential_failures"].append({
                                "failure_type": failure_type.name,
                                "probability": risk_prob,
                                "severity": risk_severity,
                                "description": risk_desc
                            })
                
                # Update overall failure probability
                prediction["failure_probability"] = 1.0 - simulation.confidence
                
                # Add fallback recommendation
                if prediction["failure_probability"] > 0.5:
                    # Get the strategy for the most likely failure
                    if prediction["potential_failures"]:
                        most_likely = prediction["potential_failures"][0]
                        failure_type = FailureType[most_likely["failure_type"]]
                        strategy = self.default_strategies.get(failure_type, FallbackStrategy.ALTERNATIVE_AGENT)
                        prediction["recommendation"] = {
                            "strategy": strategy.name,
                            "reason": f"High probability of {failure_type.name} failure"
                        }
                
            except Exception as e:
                logger.warning(f"Error in simulation-based failure prediction: {e}")
        
        # If no simulation or simulation failed, use history-based prediction
        if not prediction["potential_failures"] and sorted_failures:
            for failure_type, probability in sorted_failures[:3]:  # Top 3 failure types
                prediction["potential_failures"].append({
                    "failure_type": failure_type.name,
                    "probability": probability,
                    "severity": 0.7,  # Default severity
                    "description": f"Historical {failure_type.name} failure pattern"
                })
                
            prediction["failure_probability"] = sum(
                f["probability"] for f in prediction["potential_failures"]
            ) / len(prediction["potential_failures"]) if prediction["potential_failures"] else 0.0
            
            # Add fallback recommendation
            if prediction["failure_probability"] > 0.3:
                most_likely = prediction["potential_failures"][0]
                failure_type = FailureType[most_likely["failure_type"]]
                strategy = self.default_strategies.get(failure_type, FallbackStrategy.ALTERNATIVE_AGENT)
                prediction["recommendation"] = {
                    "strategy": strategy.name,
                    "reason": f"Historical pattern of {failure_type.name} failures"
                }
        
        return prediction
    
    def get_failure_history(self, agent_id: Optional[str] = None, 
                         failure_type: Optional[Union[str, FailureType]] = None,
                         time_range: Optional[Tuple[float, float]] = None) -> List[FailureRecord]:
        """
        Get history of failures, optionally filtered.
        
        Args:
            agent_id: Optional agent ID to filter by
            failure_type: Optional failure type to filter by
            time_range: Optional (start_time, end_time) tuple
            
        Returns:
            history: List of matching failure records
        """
        # Convert string failure type to enum if needed
        if isinstance(failure_type, str):
            try:
                failure_type = FailureType[failure_type.upper()]
            except KeyError:
                logger.warning(f"Unknown failure type: {failure_type}, using OTHER")
                failure_type = FailureType.OTHER
                
        # Apply filters
        filtered_history = self.failure_history
        
        if agent_id:
            filtered_history = [f for f in filtered_history if f.agent_id == agent_id]
            
        if failure_type:
            filtered_history = [f for f in filtered_history if f.failure_type == failure_type]
            
        if time_range:
            start_time, end_time = time_range
            filtered_history = [
                f for f in filtered_history 
                if start_time <= f.timestamp <= end_time
            ]
            
        return filtered_history
    
    def get_agent_failure_rate(self, agent_id: str, 
                             time_window: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate failure rate statistics for an agent.
        
        Args:
            agent_id: ID of the agent
            time_window: Optional time window in seconds (default: all time)
            
        Returns:
            stats: Dictionary of failure statistics
        """
        # Get agent failures
        failures = self.get_failure_history(agent_id=agent_id)
        
        # Filter by time window if provided
        if time_window:
            current_time = time.time()
            failures = [f for f in failures if current_time - f.timestamp <= time_window]
            
        # Get agent performance stats
        agent_stats = self.agent_performance_stats.get(agent_id, {})
        total_executions = agent_stats.get("total_executions", 0)
        
        # Calculate failure rate
        failure_count = len(failures)
        
        if total_executions == 0:
            failure_rate = 0.0
        else:
            failure_rate = failure_count / total_executions
            
        # Count by failure type
        failure_counts = {}
        for failure in failures:
            failure_type = failure.failure_type.name
            if failure_type not in failure_counts:
                failure_counts[failure_type] = 0
            failure_counts[failure_type] += 1
            
        # Calculate success rate of fallbacks
        fallbacks = [fb for fb in self.fallback_history 
                    if fb.original_failure.agent_id == agent_id]
        
        successful_fallbacks = [fb for fb in fallbacks if fb.success]
        
        if not fallbacks:
            fallback_success_rate = 0.0
        else:
            fallback_success_rate = len(successful_fallbacks) / len(fallbacks)
            
        # Calculate strategy effectiveness
        strategy_stats = {}
        
        for fb in fallbacks:
            strategy = fb.strategy_used.name
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {"total": 0, "success": 0}
                
            strategy_stats[strategy]["total"] += 1
            if fb.success:
                strategy_stats[strategy]["success"] += 1
                
        # Calculate success rates for each strategy
        for strategy, stats in strategy_stats.items():
            if stats["total"] > 0:
                stats["success_rate"] = stats["success"] / stats["total"]
            else:
                stats["success_rate"] = 0.0
                
        return {
            "agent_id": agent_id,
            "total_executions": total_executions,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
            "failure_counts_by_type": failure_counts,
            "fallback_success_rate": fallback_success_rate,
            "strategy_stats": strategy_stats,
            "time_window": time_window
        }
    
    def clear_history(self) -> None:
        """Clear failure and fallback history."""
        self.failure_history = []
        self.fallback_history = []
        logger.info("Cleared failure and fallback history")
    
    def _add_to_failure_history(self, failure: FailureRecord) -> None:
        """
        Add a failure record to history, pruning if needed.
        
        Args:
            failure: Failure record to add
        """
        self.failure_history.append(failure)
        
        # Prune if over limit
        if len(self.failure_history) > self.failure_history_limit:
            self.failure_history = self.failure_history[-self.failure_history_limit:]
    
    def _add_to_fallback_history(self, result: FallbackResult) -> None:
        """
        Add a fallback result to history, pruning if needed.
        
        Args:
            result: Fallback result to add
        """
        self.fallback_history.append(result)
        
        # Prune if over limit
        if len(self.fallback_history) > self.failure_history_limit:
            self.fallback_history = self.fallback_history[-self.failure_history_limit:]
    
    def _log_failure(self, failure: FailureRecord) -> None:
        """
        Log a failure to the logger and trace logger if available.
        
        Args:
            failure: Failure record to log
        """
        # Log to standard logger
        error_summary = f"{failure.error_message[:50]}..." if len(failure.error_message) > 50 else failure.error_message
        logger.warning(f"Agent failure: {failure.agent_id} - {failure.failure_type.name} - {error_summary}")
        
        # Log to trace logger if available
        if self.trace_logger:
            self.trace_logger.log_event(
                event_type="agent_failure",
                component_id=failure.agent_id,
                data={
                    "failure_id": failure.failure_id,
                    "failure_type": failure.failure_type.name,
                    "error_message": failure.error_message,
                    "error_details": failure.error_details,
                    "context": failure.context
                }
            )
    
    def _log_fallback_result(self, result: FallbackResult) -> None:
        """
        Log a fallback result to the logger and trace logger if available.
        
        Args:
            result: Fallback result to log
        """
        # Log to standard logger
        status = "succeeded" if result.success else "failed"
        logger.info(f"Fallback {status}: {result.agent_id} - {result.strategy_used.name} - attempts: {result.attempts}")
        
        # Log to trace logger if available
        if self.trace_logger:
            self.trace_logger.log_event(
                event_type="fallback_result",
                component_id="fallback_handler",
                data={
                    "fallback_id": result.fallback_id,
                    "agent_id": result.agent_id,
                    "strategy": result.strategy_used.name,
                    "success": result.success,
                    "attempts": result.attempts,
                    "execution_time": result.execution_time,
                    "confidence": result.confidence,
                    "original_failure_type": result.original_failure.failure_type.name
                }
            )
    
    def _update_agent_stats(self, agent_id: str, failure_type: FailureType,
                          strategy: FallbackStrategy, success: bool) -> None:
        """
        Update agent performance statistics.
        
        Args:
            agent_id: ID of the agent
            failure_type: Type of the failure
            strategy: Fallback strategy used
            success: Whether the fallback was successful
        """
        # Initialize agent stats if not exist
        if agent_id not in self.agent_performance_stats:
            self.agent_performance_stats[agent_id] = {
                "total_executions": 0,
                "total_failures": 0,
                "failure_types": {},
                "fallback_strategies": {},
                "fallback_successes": 0,
                "fallback_failures": 0
            }
            
        # Update stats
        stats = self.agent_performance_stats[agent_id]
        
        # Count failure
        stats["total_failures"] += 1
        
        # Count by failure type
        failure_type_name = failure_type.name
        if failure_type_name not in stats["failure_types"]:
            stats["failure_types"][failure_type_name] = 0
        stats["failure_types"][failure_type_name] += 1
        
        # Count by strategy
        strategy_name = strategy.name
        if strategy_name not in stats["fallback_strategies"]:
            stats["fallback_strategies"][strategy_name] = {
                "total": 0,
                "success": 0,
                "failure": 0
            }
            
        strategy_stats = stats["fallback_strategies"][strategy_name]
        strategy_stats["total"] += 1
        
        if success:
            strategy_stats["success"] += 1
            stats["fallback_successes"] += 1
        else:
            strategy_stats["failure"] += 1
            stats["fallback_failures"] += 1
    
    def _determine_strategy(self, failure: FailureRecord) -> FallbackStrategy:
        """
        Determine the best fallback strategy for a failure.
        
        Args:
            failure: Failure record to determine strategy for
            
        Returns:
            strategy: Selected fallback strategy
        """
        # Check for custom handler
        if failure.failure_type in self.custom_handlers:
            return FallbackStrategy.RETRY_WITH_PARAMS  # Will use custom handler
            
        # Check if there's a specific strategy for this failure type
        if failure.failure_type in self.default_strategies:
            return self.default_strategies[failure.failure_type]
            
        # Default to alternative agent
        return FallbackStrategy.ALTERNATIVE_AGENT
    
    def _apply_strategy(self, strategy: FallbackStrategy, 
                      failure: FailureRecord) -> FallbackResult:
        """
        Apply the selected fallback strategy to handle a failure.
        
        Args:
            strategy: Strategy to apply
            failure: Failure record to handle
            
        Returns:
            result: Result of applying the strategy
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        # Create base result
        result = FallbackResult(
            success=False,
            fallback_id=str(uuid.uuid4()),
            agent_id=agent_id,
            original_failure=failure,
            strategy_used=strategy,
            result_data=None,
            confidence=0.0,
            attempts=1
        )
        
        # Apply selected strategy
        try:
            if strategy == FallbackStrategy.RETRY:
                result = self._apply_retry(failure, result)
                
            elif strategy == FallbackStrategy.RETRY_WITH_BACKOFF:
                result = self._apply_retry_with_backoff(failure, result)
                
            elif strategy == FallbackStrategy.RETRY_WITH_PARAMS:
                result = self._apply_retry_with_params(failure, result)
                
            elif strategy == FallbackStrategy.ALTERNATIVE_AGENT:
                result = self._apply_alternative_agent(failure, result)
                
            elif strategy == FallbackStrategy.DECOMPOSE_TASK:
                result = self._apply_decompose_task(failure, result)
                
            elif strategy == FallbackStrategy.DEFAULT_VALUE:
                result = self._apply_default_value(failure, result)
                
            elif strategy == FallbackStrategy.HUMAN_ESCALATION:
                result = self._apply_human_escalation(failure, result)
                
            elif strategy == FallbackStrategy.GRACEFUL_DEGRADATION:
                result = self._apply_graceful_degradation(failure, result)
                
            elif strategy == FallbackStrategy.ABORT:
                result = self._apply_abort(failure, result)
                
            elif strategy == FallbackStrategy.CACHED_RESULT:
                result = self._apply_cached_result(failure, result)
                
            elif strategy == FallbackStrategy.USER_PROMPT:
                result = self._apply_user_prompt(failure, result)
                
            else:
                logger.warning(f"Unknown fallback strategy: {strategy.name}, using retry")
                result = self._apply_retry(failure, result)
                
        except Exception as e:
            logger.error(f"Error applying fallback strategy {strategy.name}: {e}")
            result.success = False
            result.result_data = None
            result.metadata["error"] = str(e)
            
        return result
    
    def _apply_retry(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the RETRY strategy: retry the same agent with the same input.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying RETRY strategy for {agent_id}")
        
        # Execute the agent again
        try:
            # This would use the actual agent execution logic
            # For now, mock a successful result
            # In practice, this would call something like:
            # result_data = self.circuit_router.execute_agent(agent_id, input_data, context)
            
            # Mock result for demonstration
            result_data = {"success": True, "data": "Retry result", "confidence": 0.8}
            
            result.success = True
            result.result_data = result_data
            result.confidence = result_data.get("confidence", 0.8)
            
        except Exception as e:
            result.success = False
            result.result_data = None
            result.metadata["retry_error"] = str(e)
            
        return result
    
    def _apply_retry_with_backoff(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the RETRY_WITH_BACKOFF strategy: retry with exponential backoff.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying RETRY_WITH_BACKOFF strategy for {agent_id}")
        
        # Try multiple times with exponential backoff
        for attempt in range(1, self.max_retry_attempts + 1):
            result.attempts = attempt
            
            try:
                # Calculate backoff delay
                delay = self.backoff_base ** (attempt - 1)
                
                logger.debug(f"Retry attempt {attempt}/{self.max_retry_attempts} with {delay:.2f}s delay")
                
                # Sleep for backoff delay
                time.sleep(delay)
                
                # Execute the agent again
                # For now, mock a successful result
                # In practice, this would call something like:
                # result_data = self.circuit_router.execute_agent(agent_id, input_data, context)
                
                # Mock result for demonstration - succeed on later attempts
                if attempt >= self.max_retry_attempts - 1:
                    result_data = {"success": True, "data": f"Retry result (attempt {attempt})", "confidence": 0.8}
                    
                    result.success = True
                    result.result_data = result_data
                    result.confidence = result_data.get("confidence", 0.8)
                    result.metadata["successful_attempt"] = attempt
                    
                    break
                else:
                    # Simulate continued failure
                    raise Exception(f"Simulated failure on attempt {attempt}")
                    
            except Exception as e:
                result.success = False
                result.result_data = None
                result.metadata[f"retry_error_{attempt}"] = str(e)
                
                # Continue to next attempt
                
        return result
    
    def _apply_retry_with_params(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the RETRY_WITH_PARAMS strategy: retry with modified parameters.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying RETRY_WITH_PARAMS strategy for {agent_id}")
        
        # Check for custom handler first
        if failure.failure_type in self.custom_handlers:
            handler = self.custom_handlers[failure.failure_type]
            
            try:
                # Call custom handler
                handler_result = handler(failure)
                
                # Update result
                result.success = True
                result.result_data = handler_result
                result.confidence = 0.8  # Default confidence for custom handlers
                result.metadata["custom_handler"] = "used"
                
                return result
                
            except Exception as e:
                logger.error(f"Error in custom handler for {failure.failure_type.name}: {e}")
                # Fall through to default implementation
        
        # Determine parameter modifications
        modified_input = input_data
        modified_context = context.copy() if context else {}
        
        # Apply modifications based on failure type
        if failure.failure_type == FailureType.TIMEOUT:
            # Increase timeout
            modified_context["timeout"] = modified_context.get("timeout", 30) * 1.5
            
        elif failure.failure_type == FailureType.LOW_CONFIDENCE:
            # Add hint for better confidence
            if isinstance(modified_input, dict):
                modified_input = modified_input.copy()
                modified_input["require_high_confidence"] = True
                
            modified_context["min_confidence"] = self.confidence_threshold
            
        elif failure.failure_type == FailureType.INVALID_FORMAT:
            # Add format guidance
            if isinstance(modified_input, dict):
                modified_input = modified_input.copy()
                modified_input["strict_format"] = True
                
            modified_context["validate_format"] = True
            
        # Execute with modified parameters
        try:
            # For now, mock a successful result
            # In practice, this would call something like:
            # result_data = self.circuit_router.execute_agent(agent_id, modified_input, modified_context)
            
            # Mock result for demonstration
            result_data = {
                "success": True, 
                "data": "Result with modified parameters", 
                "confidence": 0.85
            }
            
            result.success = True
            result.result_data = result_data
            result.confidence = result_data.get("confidence", 0.85)
            result.metadata["parameter_modifications"] = {
                "input_modified": input_data != modified_input,
                "context_modified": context != modified_context
            }
            
        except Exception as e:
            result.success = False
            result.result_data = None
            result.metadata["retry_error"] = str(e)
            
        return result
    
    def _apply_alternative_agent(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the ALTERNATIVE_AGENT strategy: route to an alternative agent.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        failure_type = failure.failure_type
        
        logger.debug(f"Applying ALTERNATIVE_AGENT strategy for {agent_id}")
        
        # Find alternative agents
        alternatives = self.alternative_agents.get(agent_id, [])
        
        # Filter by failure type if specified
        valid_alternatives = []
        
        for alt in alternatives:
            alt_id = alt["agent_id"]
            failure_types = alt.get("failure_types")
            
            # If no failure types specified, valid for all
            if not failure_types or failure_type in failure_types:
                valid_alternatives.append(alt_id)
                
        # If no valid alternatives, try to find one using ReliabilityRouter
        if not valid_alternatives and self.circuit_router:
            try:
                # See if ReliabilityRouter has methods for finding alternatives
                if hasattr(self.circuit_router, "reliability_router") and self.circuit_router.reliability_router:
                    reliability_router = self.circuit_router.reliability_router
                    
                    # See if there's a method for getting alternatives
                    if hasattr(reliability_router, "get_alternatives"):
                        alternatives = reliability_router.get_alternatives(
                            source_id="fallback_handler",
                            current_target=agent_id
                        )
                        
                        if alternatives:
                            # Use the most reliable alternative
                            best_alt, _ = alternatives[0]
                            valid_alternatives.append(best_alt)
                            
            except Exception as e:
                logger.warning(f"Error finding alternatives through ReliabilityRouter: {e}")
                
        # If still no valid alternatives, return failure
        if not valid_alternatives:
            result.success = False
            result.result_data = None
            result.metadata["error"] = "No valid alternative agents available"
            
            return result
            
        # Try each alternative until one succeeds
        for alt_id in valid_alternatives:
            try:
                logger.debug(f"Trying alternative agent: {alt_id}")
                
                # Execute the alternative agent
                # For now, mock a successful result
                # In practice, this would call something like:
                # result_data = self.circuit_router.execute_agent(alt_id, input_data, context)
                
                # Mock result for demonstration
                result_data = {
                    "success": True, 
                    "data": f"Result from alternative agent {alt_id}", 
                    "confidence": 0.85
                }
                
                result.success = True
                result.result_data = result_data
                result.confidence = result_data.get("confidence", 0.85)
                result.metadata["alternative_agent"] = alt_id
                
                # Update agent_id to reflect the alternative
                result.agent_id = alt_id
                
                # Successfully used alternative, so break loop
                break
                
            except Exception as e:
                logger.warning(f"Alternative agent {alt_id} also failed: {e}")
                # Continue to next alternative
                
        # If all alternatives failed, result will still have success=False
        return result
    
    def _apply_decompose_task(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the DECOMPOSE_TASK strategy: break into simpler sub-tasks.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying DECOMPOSE_TASK strategy for {agent_id}")
        
        # This would typically use a task decomposition agent
        # For now, we'll mock a simple decomposition
        
        # Check if input can be decomposed
        if not isinstance(input_data, dict):
            result.success = False
            result.result_data = None
            result.metadata["error"] = "Cannot decompose non-dictionary input"
            
            return result
            
        try:
            # Mock task decomposition
            # In practice, this would use a planning agent or similar
            
            # Example: if input has a "query" field with multiple parts
            if "query" in input_data and isinstance(input_data["query"], str):
                query = input_data["query"]
                
                # Mock splitting into sub-queries
                sub_queries = query.split(". ")
                
                if len(sub_queries) == 1:
                    # Can't decompose, try simpler version
                    simpler_query = query.split(" ")
                    if len(simpler_query) > 5:
                        simpler_query = " ".join(simpler_query[:5]) + "?"
                        sub_queries = [simpler_query]
                    else:
                        result.success = False
                        result.result_data = None
                        result.metadata["error"] = "Cannot decompose query further"
                        
                        return result
                
                # Execute each sub-query
                sub_results = []
                
                for i, sub_query in enumerate(sub_queries):
                    # Create sub-input
                    sub_input = input_data.copy()
                    sub_input["query"] = sub_query
                    sub_input["is_subtask"] = True
                    sub_input["subtask_index"] = i
                    
                    # Execute sub-task
                    # For now, mock successful results
                    # In practice, would call circuit_router.execute_agent
                    
                    sub_result = {
                        "success": True,
                        "data": f"Result for sub-query: {sub_query}",
                        "confidence": 0.9,
                        "subtask_index": i
                    }
                    
                    sub_results.append(sub_result)
                    
                # Combine sub-results
                combined_result = {
                    "success": True,
                    "data": "\n".join(sr["data"] for sr in sub_results),
                    "confidence": sum(sr["confidence"] for sr in sub_results) / len(sub_results),
                    "decomposed": True,
                    "subtask_count": len(sub_results)
                }
                
                result.success = True
                result.result_data = combined_result
                result.confidence = combined_result["confidence"]
                result.metadata["decomposition"] = {
                    "original_query": query,
                    "sub_queries": sub_queries,
                    "subtask_count": len(sub_queries)
                }
                
            else:
                result.success = False
                result.result_data = None
                result.metadata["error"] = "Input format not suitable for decomposition"
                
        except Exception as e:
            result.success = False
            result.result_data = None
            result.metadata["error"] = f"Error in task decomposition: {str(e)}"
            
        return result
    
    def _apply_default_value(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the DEFAULT_VALUE strategy: return a safe default value.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying DEFAULT_VALUE strategy for {agent_id}")
        
        # Determine appropriate default value based on context
        default_value = None
        confidence = 0.5  # Default confidence for default values
        
        # Check for default value in context
        if context and "default_value" in context:
            default_value = context["default_value"]
            confidence = context.get("default_confidence", 0.5)
            
        # If no default in context, use agent-specific defaults
        elif agent_id in self.agent_performance_stats:
            # Check if we have default values defined for agent
            agent_stats = self.agent_performance_stats[agent_id]
            
            if "default_values" in agent_stats:
                defaults = agent_stats["default_values"]
                
                # Try to match input pattern
                for pattern, value in defaults.items():
                    # Simple pattern matching for demonstration
                    if pattern in str(input_data):
                        default_value = value
                        break
                        
        # If still no default, use generic defaults based on failure type
        if default_value is None:
            if failure.failure_type == FailureType.EMPTY_RESULT:
                default_value = []
            elif failure.failure_type == FailureType.LOW_CONFIDENCE:
                default_value = {"result": "uncertain", "confidence": 0.5}
            else:
                default_value = {"error": "No result available", "success": False}
                
        result.success = True  # Default values are always "successful"
        result.result_data = default_value
        result.confidence = confidence
        result.metadata["is_default_value"] = True
        
        return result
    
    def _apply_human_escalation(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the HUMAN_ESCALATION strategy: escalate to human operator.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying HUMAN_ESCALATION strategy for {agent_id}")
        
        # In a real system, this would integrate with a human-in-the-loop system
        # For now, we just log the escalation and return a placeholder
        
        # Create escalation record
        escalation_id = str(uuid.uuid4())
        escalation = {
            "escalation_id": escalation_id,
            "agent_id": agent_id,
            "failure_id": failure.failure_id,
            "failure_type": failure.failure_type.name,
            "input_data": input_data,
            "context": context,
            "timestamp": time.time(),
            "status": "pending",
            "priority": self._determine_escalation_priority(failure)
        }
        
        # Log escalation
        logger.info(f"Human escalation: {escalation_id} - {agent_id} - "
                   f"{failure.failure_type.name} - Priority: {escalation['priority']}")
        
        # In practice, would submit to escalation queue
        # For now, simulate pending escalation
        
        result.success = True  # Mark as success since we successfully escalated
        result.result_data = {
            "escalation_id": escalation_id,
            "status": "pending",
            "message": "This request has been escalated to a human operator",
            "estimated_response_time": "24 hours"
        }
        result.confidence = 0.99  # High confidence that escalation is correct
        result.metadata["escalation"] = escalation
        
        return result
    
    def _apply_graceful_degradation(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the GRACEFUL_DEGRADATION strategy: continue with reduced functionality.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying GRACEFUL_DEGRADATION strategy for {agent_id}")
        
        # Determine what subset of functionality can still be provided
        
        # For now, mock degraded functionality
        try:
            # Check if input has specific features that can be degraded
            degraded_features = []
            
            if isinstance(input_data, dict):
                # Example: if requesting multiple data types, return only available ones
                requested_data = input_data.get("requested_data", [])
                
                if requested_data:
                    # Mock: pretend only some data types are available
                    available_data = requested_data[:len(requested_data)//2]
                    degraded_features.append(f"Limited data: {available_data}")
                    
                # Example: if requesting high precision, return lower precision
                if input_data.get("high_precision", False):
                    degraded_features.append("Using standard precision")
                    
            # Create degraded result
            degraded_result = {
                "success": True,
                "message": "Operation completed with reduced functionality",
                "degraded_features": degraded_features,
                "is_degraded": True
            }
            
            # Add some mock data
            if isinstance(input_data, dict) and "query" in input_data:
                degraded_result["data"] = f"Degraded result for: {input_data['query']}"
            else:
                degraded_result["data"] = "Partial results available"
                
            result.success = True
            result.result_data = degraded_result
            result.confidence = 0.6  # Lower confidence for degraded results
            result.metadata["degraded_features"] = degraded_features
            
        except Exception as e:
            result.success = False
            result.result_data = None
            result.metadata["error"] = f"Error in graceful degradation: {str(e)}"
            
        return result
    
    def _apply_abort(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the ABORT strategy: abort the current operation.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying ABORT strategy for {agent_id}")
        
        # Create abort result
        abort_result = {
            "success": False,
            "aborted": True,
            "reason": f"Operation aborted due to {failure.failure_type.name}",
            "error_message": failure.error_message,
            "error_details": failure.error_details
        }
        
        # Check if there are any cleanup actions needed
        cleanup_actions = []
        
        if context and "resources" in context:
            # Mock cleanup of resources
            resources = context["resources"]
            
            if isinstance(resources, list):
                for resource in resources:
                    cleanup_actions.append(f"Released: {resource}")
            elif isinstance(resources, dict):
                for resource_id, resource in resources.items():
                    cleanup_actions.append(f"Released: {resource_id}")
                    
        if cleanup_actions:
            abort_result["cleanup_actions"] = cleanup_actions
            
        # Apply circuit abort if circuit_router available
        if self.circuit_router and hasattr(self.circuit_router, "abort_circuit"):
            try:
                circuit_id = context.get("circuit_id") if context else None
                
                if circuit_id:
                    # In practice, would call circuit_router.abort_circuit
                    # circuit_router.abort_circuit(circuit_id, reason=abort_result["reason"])
                    abort_result["circuit_aborted"] = circuit_id
            except Exception as e:
                logger.warning(f"Error aborting circuit: {e}")
                
        result.success = False  # Abort is always a failure
        result.result_data = abort_result
        result.confidence = 0.99  # High confidence that abort is correct
        result.metadata["abort_reason"] = abort_result["reason"]
        result.metadata["cleanup_actions"] = cleanup_actions if cleanup_actions else None
        
        return result
    
    def _apply_cached_result(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the CACHED_RESULT strategy: use cached result from previous execution.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying CACHED_RESULT strategy for {agent_id}")
        
        # In practice, would use a cache system
        # For now, look for similar previous executions in history
        
        # Look for successful fallbacks for the same agent
        successful_fallbacks = [
            fb for fb in self.fallback_history
            if fb.agent_id == agent_id and fb.success
        ]
        
        # Simple cache hit: exact input match
        cache_hit = None
        
        for fb in successful_fallbacks:
            if fb.original_failure.input_data == input_data:
                cache_hit = fb
                break
                
        # If exact match found, use it
        if cache_hit:
            logger.debug(f"Found exact cache match: {cache_hit.fallback_id}")
            
            # Create copy of cached result
            cached_data = cache_hit.result_data
            
            # Adjust confidence based on age
            age = time.time() - cache_hit.original_failure.timestamp
            age_hours = age / 3600
            
            # Decay confidence based on age
            original_confidence = cache_hit.confidence
            decayed_confidence = original_confidence * (0.95 ** age_hours)
            
            # Create result with cache metadata
            result.success = True
            result.result_data = cached_data
            result.confidence = decayed_confidence
            result.metadata["cache_hit"] = "exact"
            result.metadata["original_confidence"] = original_confidence
            result.metadata["cache_age_hours"] = age_hours
            result.metadata["source_fallback_id"] = cache_hit.fallback_id
            
            return result
            
        # No exact match, try fuzzy matching for text inputs
        if isinstance(input_data, dict) and "query" in input_data:
            query = input_data["query"]
            
            # Simple fuzzy match by looking for overlapping words
            best_match = None
            best_score = 0
            
            for fb in successful_fallbacks:
                fb_input = fb.original_failure.input_data
                
                if isinstance(fb_input, dict) and "query" in fb_input:
                    fb_query = fb_input["query"]
                    
                    # Calculate similarity score
                    query_words = set(query.lower().split())
                    fb_words = set(fb_query.lower().split())
                    
                    overlap = len(query_words.intersection(fb_words))
                    max_words = max(len(query_words), len(fb_words))
                    
                    if max_words > 0:
                        score = overlap / max_words
                        
                        if score > best_score and score > 0.7:  # At least 70% similar
                            best_score = score
                            best_match = fb
                            
            # If good fuzzy match found, use it
            if best_match:
                logger.debug(f"Found fuzzy cache match: {best_match.fallback_id} (score: {best_score:.2f})")
                
                # Create copy of cached result
                cached_data = best_match.result_data
                
                # Adjust confidence based on match score and age
                age = time.time() - best_match.original_failure.timestamp
                age_hours = age / 3600
                
                # Decay confidence based on age and match score
                original_confidence = best_match.confidence
                decayed_confidence = original_confidence * best_score * (0.95 ** age_hours)
                
                # Create result with cache metadata
                result.success = True
                result.result_data = cached_data
                result.confidence = decayed_confidence
                result.metadata["cache_hit"] = "fuzzy"
                result.metadata["match_score"] = best_score
                result.metadata["original_confidence"] = original_confidence
                result.metadata["cache_age_hours"] = age_hours
                result.metadata["source_fallback_id"] = best_match.fallback_id
                
                return result
                
        # No cache hit
        result.success = False
        result.result_data = None
        result.metadata["cache_hit"] = "miss"
        
        return result
    
    def _apply_user_prompt(self, failure: FailureRecord, result: FallbackResult) -> FallbackResult:
        """
        Apply the USER_PROMPT strategy: ask user how to proceed.
        
        Args:
            failure: The failure record
            result: The fallback result to update
            
        Returns:
            updated_result: Updated fallback result
        """
        agent_id = failure.agent_id
        input_data = failure.input_data
        context = failure.context
        
        logger.debug(f"Applying USER_PROMPT strategy for {agent_id}")
        
        # In a real system, this would prompt the user for input
        # For now, just return a placeholder response
        
        # Create user prompt
        prompt_id = str(uuid.uuid4())
        prompt_message = f"The agent '{agent_id}' encountered a {failure.failure_type.name} error. How would you like to proceed?"
        
        # Create options based on failure type
        options = []
        
        if failure.failure_type == FailureType.TIMEOUT:
            options.append({"id": "retry", "label": "Retry with longer timeout"})
            options.append({"id": "skip", "label": "Skip this step"})
            
        elif failure.failure_type == FailureType.LOW_CONFIDENCE:
            options.append({"id": "alt_agent", "label": "Try a different agent"})
            options.append({"id": "human", "label": "Escalate to human"})
            options.append({"id": "accept", "label": "Accept low confidence result"})
            
        elif failure.failure_type == FailureType.INVALID_FORMAT:
            options.append({"id": "retry_format", "label": "Retry with format guidance"})
            options.append({"id": "alt_agent", "label": "Try a different agent"})
            
        else:
            # Default options
            options.append({"id": "retry", "label": "Retry operation"})
            options.append({"id": "abort", "label": "Abort operation"})
            options.append({"id": "human", "label": "Escalate to human"})
            
        # Create prompt result
        prompt_result = {
            "prompt_id": prompt_id,
            "message": prompt_message,
            "options": options,
            "requires_user_input": True,
            "error_details": {
                "agent_id": agent_id,
                "failure_type": failure.failure_type.name,
                "error_message": failure.error_message
            }
        }
        
        result.success = True  # Mark as success since we successfully created prompt
        result.result_data = prompt_result
        result.confidence = 0.99  # High confidence that user prompt is appropriate
        result.metadata["prompt_id"] = prompt_id
        result.metadata["prompt_options"] = [opt["id"] for opt in options]
        
        return result
    
    def _determine_escalation_priority(self, failure: FailureRecord) -> str:
        """
        Determine the priority level for a human escalation.
        
        Args:
            failure: The failure record
            
        Returns:
            priority: Priority level (high, medium, low)
        """
        # Default to medium
        priority = "medium"
        
        # Adjust based on failure type
        if failure.failure_type in (FailureType.AUTHORIZATION, FailureType.CONSISTENCY_ERROR):
            priority = "high"
        elif failure.failure_type in (FailureType.EMPTY_RESULT, FailureType.LOW_CONFIDENCE):
            priority = "low"
            
        # Check for critical keywords in error message
        critical_keywords = ["critical", "urgent", "emergency", "security", "breach", "data loss"]
        
        if failure.error_message:
            for keyword in critical_keywords:
                if keyword in failure.error_message.lower():
                    priority = "high"
                    break
                    
        # Check for VIP users in context
        context = failure.context or {}
        if context.get("user_type") == "vip" or context.get("priority") == "high":
            # Increase priority by one level
            if priority == "low":
                priority = "medium"
            elif priority == "medium":
                priority = "high"
                
        return priority

# Fallback Handler Summary
# -----------------------
# The FallbackHandler module provides standardized error handling and fallback
# mechanisms when agents fail or return low-confidence results.
#
# Key features:
#
# 1. Failure Detection and Classification:
#    - Identifies various types of agent failures (timeouts, exceptions, etc.)
#    - Monitors agent confidence levels and triggers fallbacks when needed
#    - Maintains detailed history of failures for analysis and learning
#
# 2. Diverse Fallback Strategies:
#    - Implements multiple fallback approaches (retry, alternative agents, etc.)
#    - Matches failure types to appropriate strategies automatically
#    - Supports custom handlers for specific failure scenarios
#
# 3. Agent Substitution:
#    - Maintains mappings of alternative agents for different tasks
#    - Routes to appropriate alternatives based on failure type
#    - Integrates with ReliabilityRouter for trust-based routing
#
# 4. Graceful Degradation:
#    - Provides partial results when complete results are unavailable
#    - Uses cached results when appropriate
#    - Supports task decomposition for complex failures
#
# 5. Predictive Failure Handling:
#    - Integrates with SimulationPlanner for anticipating potential failures
#    - Recommends proactive fallback strategies based on historical patterns
#    - Monitors agent reliability metrics to guide fallback decisions
#
# This module enhances system resilience by providing consistent, intelligent
# responses to agent failures, ensuring that the Neuron architecture can recover
# gracefully from errors and maintain operational continuity even when individual
# components encounter problems.
