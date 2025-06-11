
"""
Neuron Framework: Deliberative Agent Implementation

DeliberativeAgent provides sophisticated reasoning, planning, and decision-making
capabilities. It can evaluate multiple options, maintain complex goals, and
adapt its behavior based on experience.
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from neuron.core.base import BaseAgent, Message, MessageType, AgentCapabilities, MemoryType
from neuron.memory.working import WorkingMemory

logger = logging.getLogger(__name__)

# =====================================
# Deliberative Agent Types
# =====================================

class ReasoningStrategy(Enum):
    """Different reasoning approaches"""
    LOGICAL = "logical"  # Step-by-step logical reasoning
    PROBABILISTIC = "probabilistic"  # Probability-based decisions
    HEURISTIC = "heuristic"  # Rule-of-thumb approaches
    CASE_BASED = "case_based"  # Reasoning from past cases
    MULTI_CRITERIA = "multi_criteria"  # Multiple criteria decision analysis

@dataclass
class Goal:
    """Represents an agent goal"""
    id: str
    description: str
    priority: float = 1.0
    deadline: Optional[float] = None
    progress: float = 0.0
    requirements: Dict[str, Any] = field(default_factory=dict)
    sub_goals: List[str] = field(default_factory=list)
    status: str = "active"  # active, completed, failed, suspended
    
    def is_expired(self) -> bool:
        """Check if goal has passed its deadline"""
        return self.deadline is not None and time.time() > self.deadline
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary"""
        return {
            'id': self.id,
            'description': self.description,
            'priority': self.priority,
            'deadline': self.deadline,
            'progress': self.progress,
            'requirements': self.requirements,
            'sub_goals': self.sub_goals,
            'status': self.status
        }

@dataclass
class Plan:
    """Represents an execution plan"""
    id: str
    goal_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    created_time: float = field(default_factory=time.time)
    estimated_duration: Optional[float] = None
    confidence: float = 0.5
    
    def add_step(self, action: str, parameters: Dict[str, Any] = None,
                 expected_outcome: str = None, dependencies: List[int] = None):
        """Add a step to the plan"""
        step = {
            'step_id': len(self.steps),
            'action': action,
            'parameters': parameters or {},
            'expected_outcome': expected_outcome,
            'dependencies': dependencies or [],
            'status': 'pending',  # pending, executing, completed, failed
            'start_time': None,
            'end_time': None,
            'actual_outcome': None
        }
        self.steps.append(step)
    
    def get_current_step(self) -> Optional[Dict[str, Any]]:
        """Get the current step to execute"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def advance_step(self):
        """Move to the next step"""
        if self.current_step < len(self.steps):
            self.current_step += 1
    
    def is_complete(self) -> bool:
        """Check if plan is complete"""
        return self.current_step >= len(self.steps)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary"""
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'steps': self.steps,
            'current_step': self.current_step,
            'created_time': self.created_time,
            'estimated_duration': self.estimated_duration,
            'confidence': self.confidence
        }

@dataclass
class ReasoningContext:
    """Context for reasoning operations"""
    request_id: str
    reasoning_strategy: ReasoningStrategy
    available_information: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    preferences: Dict[str, float] = field(default_factory=dict)
    time_limit: Optional[float] = None
    confidence_threshold: float = 0.7

# =====================================
# Deliberative Agent Implementation
# =====================================

class DeliberativeAgent(BaseAgent):
    """
    Deliberative agent with advanced reasoning and planning capabilities
    
    Features:
    - Goal-oriented behavior
    - Multi-step planning
    - Multiple reasoning strategies
    - Experience-based learning
    - Uncertainty handling
    - Resource management
    """
    
    def __init__(self, 
                 agent_id: str,
                 capabilities: AgentCapabilities = None,
                 config: Dict[str, Any] = None):
        """Initialize the deliberative agent"""
        
        # Set default capabilities for deliberative agents
        if capabilities is None:
            capabilities = AgentCapabilities(
                capabilities={"reasoning", "planning", "decision_making", "problem_solving"},
                memory_types={MemoryType.WORKING, MemoryType.EPISODIC, MemoryType.PROCEDURAL},
                max_concurrent_tasks=5
            )
        
        super().__init__(agent_id, capabilities, config)
        
        # Deliberative-specific state
        self.goals: Dict[str, Goal] = {}
        self.plans: Dict[str, Plan] = {}
        self.active_reasoning_contexts: Dict[str, ReasoningContext] = {}
        
        # Reasoning configuration
        self.default_reasoning_strategy = ReasoningStrategy(
            self.config.get('default_reasoning_strategy', 'logical')
        )
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        self.max_planning_depth = self.config.get('max_planning_depth', 10)
        self.planning_timeout = self.config.get('planning_timeout', 30.0)
        
        # Experience tracking
        self.successful_strategies: Dict[str, int] = {}
        self.failed_strategies: Dict[str, int] = {}
        
        # Setup working memory if not provided
        if MemoryType.WORKING not in self.memory_systems:
            working_memory = WorkingMemory(
                max_items=self.config.get('working_memory_size', 500),
                default_ttl=self.config.get('working_memory_ttl', 3600)  # 1 hour
            )
            self.add_memory_system(MemoryType.WORKING, working_memory)
        
        logger.info(f"DeliberativeAgent {agent_id} initialized with strategy: {self.default_reasoning_strategy.value}")
    
    # =====================================
    # Message Handling
    # =====================================
    
    async def _handle_request(self, message: Message) -> Optional[Dict[str, Any]]:
        """Handle request messages with deliberative reasoning"""
        request_type = message.content.get('type', 'general')
        
        if request_type == 'reasoning_request':
            return await self._handle_reasoning_request(message)
        elif request_type == 'planning_request':
            return await self._handle_planning_request(message)
        elif request_type == 'goal_management':
            return await self._handle_goal_management(message)
        elif request_type == 'decision_request':
            return await self._handle_decision_request(message)
        else:
            return await self._handle_general_request(message)
    
    async def _handle_response(self, message: Message) -> None:
        """Handle response messages"""
        # Check if this is a response to one of our requests
        correlation_id = message.correlation_id
        
        if correlation_id and correlation_id in self.active_reasoning_contexts:
            context = self.active_reasoning_contexts[correlation_id]
            
            # Process the response in the context of our reasoning
            await self._process_reasoning_response(message, context)
    
    async def _handle_reasoning_request(self, message: Message) -> Dict[str, Any]:
        """Handle complex reasoning requests"""
        try:
            # Extract reasoning parameters
            problem = message.content.get('problem', '')
            strategy = ReasoningStrategy(message.content.get('strategy', self.default_reasoning_strategy.value))
            context_data = message.content.get('context', {})
            time_limit = message.content.get('time_limit', self.planning_timeout)
            
            # Create reasoning context
            context = ReasoningContext(
                request_id=message.id,
                reasoning_strategy=strategy,
                available_information=context_data,
                constraints=message.content.get('constraints', []),
                preferences=message.content.get('preferences', {}),
                time_limit=time_limit,
                confidence_threshold=message.content.get('confidence_threshold', self.confidence_threshold)
            )
            
            # Store context for tracking
            self.active_reasoning_contexts[message.id] = context
            
            # Perform reasoning
            start_time = time.time()
            reasoning_result = await self._perform_reasoning(problem, context)
            reasoning_time = time.time() - start_time
            
            # Update experience tracking
            if reasoning_result.get('confidence', 0) >= context.confidence_threshold:
                self.successful_strategies[strategy.value] = self.successful_strategies.get(strategy.value, 0) + 1
            else:
                self.failed_strategies[strategy.value] = self.failed_strategies.get(strategy.value, 0) + 1
            
            # Clean up context
            if message.id in self.active_reasoning_contexts:
                del self.active_reasoning_contexts[message.id]
            
            # Store reasoning result in memory
            await self.remember(
                MemoryType.WORKING,
                f"reasoning_result_{message.id}",
                reasoning_result,
                {'request_id': message.id, 'reasoning_time': reasoning_time}
            )
            
            return {
                'success': True,
                'result': reasoning_result,
                'reasoning_time': reasoning_time,
                'strategy_used': strategy.value,
                'agent_confidence': self.metrics.confidence_score
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} reasoning error: {e}")
            return {
                'success': False,
                'error': str(e),
                'strategy_used': strategy.value if 'strategy' in locals() else 'unknown'
            }
    
    async def _handle_planning_request(self, message: Message) -> Dict[str, Any]:
        """Handle planning requests"""
        try:
            goal_description = message.content.get('goal', '')
            constraints = message.content.get('constraints', [])
            deadline = message.content.get('deadline')
            priority = message.content.get('priority', 1.0)
            
            # Create goal
            goal = Goal(
                id=f"goal_{message.id}",
                description=goal_description,
                priority=priority,
                deadline=deadline,
                requirements=message.content.get('requirements', {})
            )
            
            # Store goal
            self.goals[goal.id] = goal
            
            # Create plan
            plan = await self._create_plan(goal, constraints)
            
            if plan:
                self.plans[plan.id] = plan
                
                # Store plan in memory
                await self.remember(
                    MemoryType.WORKING,
                    f"plan_{plan.id}",
                    plan.to_dict(),
                    {'goal_id': goal.id, 'created_time': time.time()}
                )
                
                return {
                    'success': True,
                    'goal_id': goal.id,
                    'plan_id': plan.id,
                    'plan': plan.to_dict(),
                    'estimated_steps': len(plan.steps),
                    'confidence': plan.confidence
                }
            else:
                return {
                    'success': False,
                    'error': 'Unable to create plan for the given goal',
                    'goal_id': goal.id
                }
                
        except Exception as e:
            logger.error(f"Agent {self.agent_id} planning error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_goal_management(self, message: Message) -> Dict[str, Any]:
        """Handle goal management operations"""
        operation = message.content.get('operation', 'list')
        
        if operation == 'list':
            return {
                'goals': [goal.to_dict() for goal in self.goals.values()],
                'total_goals': len(self.goals)
            }
        elif operation == 'update':
            goal_id = message.content.get('goal_id')
            if goal_id in self.goals:
                updates = message.content.get('updates', {})
                goal = self.goals[goal_id]
                
                # Update goal properties
                for key, value in updates.items():
                    if hasattr(goal, key):
                        setattr(goal, key, value)
                
                return {
                    'success': True,
                    'goal': goal.to_dict()
                }
            else:
                return {
                    'success': False,
                    'error': f'Goal {goal_id} not found'
                }
        elif operation == 'delete':
            goal_id = message.content.get('goal_id')
            if goal_id in self.goals:
                del self.goals[goal_id]
                # Also remove associated plans
                plans_to_remove = [pid for pid, plan in self.plans.items() if plan.goal_id == goal_id]
                for pid in plans_to_remove:
                    del self.plans[pid]
                
                return {
                    'success': True,
                    'removed_goal': goal_id,
                    'removed_plans': len(plans_to_remove)
                }
            else:
                return {
                    'success': False,
                    'error': f'Goal {goal_id} not found'
                }
        else:
            return {
                'success': False,
                'error': f'Unknown operation: {operation}'
            }
    
    async def _handle_decision_request(self, message: Message) -> Dict[str, Any]:
        """Handle decision-making requests"""
        try:
            options = message.content.get('options', [])
            criteria = message.content.get('criteria', {})
            decision_strategy = message.content.get('strategy', 'multi_criteria')
            
            if not options:
                return {
                    'success': False,
                    'error': 'No options provided for decision'
                }
            
            # Evaluate options
            decision_result = await self._make_decision(options, criteria, decision_strategy)
            
            return {
                'success': True,
                'decision': decision_result,
                'options_evaluated': len(options),
                'strategy_used': decision_strategy
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} decision error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _handle_general_request(self, message: Message) -> Dict[str, Any]:
        """Handle general requests with basic reasoning"""
        try:
            # Extract the question or request
            query = message.content.get('query', message.content.get('message', ''))
            
            if not query:
                return {
                    'success': False,
                    'error': 'No query provided'
                }
            
            # Apply basic reasoning to the query
            reasoning_result = await self._basic_reasoning(query, message.content)
            
            return {
                'success': True,
                'response': reasoning_result.get('conclusion', 'Unable to process request'),
                'confidence': reasoning_result.get('confidence', 0.5),
                'reasoning_steps': reasoning_result.get('steps', [])
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} general request error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # =====================================
    # Core Reasoning Methods
    # =====================================
    
    async def _perform_reasoning(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Perform reasoning using the specified strategy"""
        strategy = context.reasoning_strategy
        
        if strategy == ReasoningStrategy.LOGICAL:
            return await self._logical_reasoning(problem, context)
        elif strategy == ReasoningStrategy.PROBABILISTIC:
            return await self._probabilistic_reasoning(problem, context)
        elif strategy == ReasoningStrategy.HEURISTIC:
            return await self._heuristic_reasoning(problem, context)
        elif strategy == ReasoningStrategy.CASE_BASED:
            return await self._case_based_reasoning(problem, context)
        elif strategy == ReasoningStrategy.MULTI_CRITERIA:
            return await self._multi_criteria_reasoning(problem, context)
        else:
            # Fallback to logical reasoning
            return await self._logical_reasoning(problem, context)
    
    async def _logical_reasoning(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Perform step-by-step logical reasoning"""
        steps = []
        confidence = 0.8  # Base confidence for logical reasoning
        
        # Step 1: Problem analysis
        steps.append({
            'step': 1,
            'action': 'analyze_problem',
            'description': f'Analyzing problem: {problem}',
            'result': 'Problem structure identified'
        })
        
        # Step 2: Information gathering
        available_info = context.available_information
        steps.append({
            'step': 2,
            'action': 'gather_information',
            'description': 'Collecting relevant information',
            'result': f'Found {len(available_info)} pieces of information'
        })
        
        # Step 3: Apply logical rules
        logical_conclusions = []
        
        # Simple logical inference (can be expanded)
        if 'facts' in available_info:
            for fact in available_info['facts']:
                if isinstance(fact, dict) and 'if' in fact and 'then' in fact:
                    # Simple if-then rule
                    logical_conclusions.append(fact['then'])
        
        steps.append({
            'step': 3,
            'action': 'apply_logic',
            'description': 'Applying logical rules and inference',
            'result': f'Generated {len(logical_conclusions)} logical conclusions'
        })
        
        # Step 4: Synthesis
        final_conclusion = f"Based on logical analysis of '{problem}', considering {len(available_info)} factors"
        if logical_conclusions:
            final_conclusion += f" and {len(logical_conclusions)} logical inferences"
        
        steps.append({
            'step': 4,
            'action': 'synthesize',
            'description': 'Synthesizing final conclusion',
            'result': final_conclusion
        })
        
        return {
            'strategy': 'logical',
            'conclusion': final_conclusion,
            'confidence': confidence,
            'steps': steps,
            'reasoning_time': time.time()
        }
    
    async def _probabilistic_reasoning(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Perform probability-based reasoning"""
        steps = []
        
        # Simplified probabilistic reasoning
        base_probability = 0.5
        adjustments = []
        
        # Adjust probability based on available information
        available_info = context.available_information
        
        if 'evidence' in available_info:
            evidence_count = len(available_info['evidence'])
            probability_boost = min(0.3, evidence_count * 0.1)
            base_probability += probability_boost
            adjustments.append(f"Evidence boost: +{probability_boost:.2f}")
        
        if 'constraints' in context.constraints:
            constraint_penalty = len(context.constraints) * 0.05
            base_probability -= constraint_penalty
            adjustments.append(f"Constraint penalty: -{constraint_penalty:.2f}")
        
        # Ensure probability stays in valid range
        probability = max(0.1, min(0.9, base_probability))
        
        steps.append({
            'step': 1,
            'action': 'calculate_probability',
            'description': f'Calculated probability for: {problem}',
            'result': f'Probability: {probability:.2f}'
        })
        
        conclusion = f"Probabilistic analysis suggests {probability:.1%} likelihood for: {problem}"
        
        return {
            'strategy': 'probabilistic',
            'conclusion': conclusion,
            'confidence': probability,
            'probability': probability,
            'adjustments': adjustments,
            'steps': steps,
            'reasoning_time': time.time()
        }
    
    async def _heuristic_reasoning(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Perform heuristic-based reasoning"""
        steps = []
        
        # Apply simple heuristics
        heuristics_applied = []
        confidence = 0.6  # Lower confidence for heuristic reasoning
        
        # Heuristic 1: Similarity to past cases
        similar_cases = await self._find_similar_cases(problem)
        if similar_cases:
            heuristics_applied.append("similarity_heuristic")
            confidence += 0.1
        
        # Heuristic 2: Representativeness
        if any(keyword in problem.lower() for keyword in ['typical', 'usual', 'common']):
            heuristics_applied.append("representativeness_heuristic")
            confidence += 0.1
        
        # Heuristic 3: Availability (recent/memorable information)
        recent_memories = await self.search_memory(
            MemoryType.WORKING,
            {'max_age': 3600}  # Last hour
        )
        if recent_memories:
            heuristics_applied.append("availability_heuristic")
            confidence += 0.05
        
        steps.append({
            'step': 1,
            'action': 'apply_heuristics',
            'description': f'Applied {len(heuristics_applied)} heuristics',
            'result': f'Heuristics used: {", ".join(heuristics_applied)}'
        })
        
        conclusion = f"Heuristic analysis of '{problem}' using {len(heuristics_applied)} mental shortcuts"
        
        return {
            'strategy': 'heuristic',
            'conclusion': conclusion,
            'confidence': min(0.9, confidence),
            'heuristics_applied': heuristics_applied,
            'steps': steps,
            'reasoning_time': time.time()
        }
    
    async def _case_based_reasoning(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Perform case-based reasoning"""
        steps = []
        
        # Find similar cases from memory
        similar_cases = await self._find_similar_cases(problem)
        
        steps.append({
            'step': 1,
            'action': 'retrieve_cases',
            'description': 'Searching for similar past cases',
            'result': f'Found {len(similar_cases)} similar cases'
        })
        
        if similar_cases:
            # Adapt solutions from similar cases
            adapted_solutions = []
            for case in similar_cases[:3]:  # Use top 3 similar cases
                adapted_solution = f"Adapted from case: {case.get('description', 'Unknown')}"
                adapted_solutions.append(adapted_solution)
            
            steps.append({
                'step': 2,
                'action': 'adapt_solutions',
                'description': 'Adapting solutions from similar cases',
                'result': f'Generated {len(adapted_solutions)} adapted solutions'
            })
            
            confidence = 0.7
            conclusion = f"Based on {len(similar_cases)} similar cases, recommended approach for '{problem}'"
        else:
            confidence = 0.3
            conclusion = f"No similar cases found for '{problem}'. Suggesting general approach."
        
        return {
            'strategy': 'case_based',
            'conclusion': conclusion,
            'confidence': confidence,
            'similar_cases_count': len(similar_cases),
            'steps': steps,
            'reasoning_time': time.time()
        }
    
    async def _multi_criteria_reasoning(self, problem: str, context: ReasoningContext) -> Dict[str, Any]:
        """Perform multi-criteria decision analysis"""
        steps = []
        
        # Extract criteria from context
        criteria = context.preferences
        if not criteria:
            # Use default criteria
            criteria = {
                'feasibility': 0.3,
                'effectiveness': 0.4,
                'efficiency': 0.3
            }
        
        steps.append({
            'step': 1,
            'action': 'identify_criteria',
            'description': 'Identifying decision criteria',
            'result': f'Using {len(criteria)} criteria: {list(criteria.keys())}'
        })
        
        # Score against each criterion (simplified)
        criterion_scores = {}
        overall_score = 0.0
        
        for criterion, weight in criteria.items():
            # Simplified scoring (would be more complex in real implementation)
            score = 0.6 + (hash(f"{problem}_{criterion}") % 40) / 100  # 0.6-1.0
            criterion_scores[criterion] = score
            overall_score += score * weight
        
        steps.append({
            'step': 2,
            'action': 'evaluate_criteria',
            'description': 'Evaluating against each criterion',
            'result': f'Overall weighted score: {overall_score:.2f}'
        })
        
        conclusion = f"Multi-criteria analysis of '{problem}' yields score {overall_score:.2f}/1.0"
        
        return {
            'strategy': 'multi_criteria',
            'conclusion': conclusion,
            'confidence': overall_score,
            'criterion_scores': criterion_scores,
            'overall_score': overall_score,
            'steps': steps,
            'reasoning_time': time.time()
        }
    
    async def _basic_reasoning(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Basic reasoning for general queries"""
        steps = []
        
        # Simple keyword-based reasoning
        confidence = 0.5
        
        # Check for question words
        question_words = ['what', 'why', 'how', 'when', 'where', 'who']
        is_question = any(word in query.lower() for word in question_words)
        
        if is_question:
            confidence += 0.1
            steps.append({
                'step': 1,
                'action': 'identify_question',
                'description': 'Identified as a question',
                'result': 'Applying question-answering approach'
            })
        
        # Check for context information
        if context and len(context) > 1:  # More than just the query
            confidence += 0.1
            steps.append({
                'step': 2,
                'action': 'analyze_context',
                'description': 'Analyzing provided context',
                'result': f'Found {len(context)-1} context elements'
            })
        
        # Generate basic response
        if is_question:
            conclusion = f"Analysis of question: '{query}' - requires domain-specific knowledge"
        else:
            conclusion = f"Processing request: '{query}' - applying general reasoning"
        
        steps.append({
            'step': len(steps) + 1,
            'action': 'generate_response',
            'description': 'Generating response based on analysis',
            'result': conclusion
        })
        
        return {
            'strategy': 'basic',
            'conclusion': conclusion,
            'confidence': min(0.8, confidence),
            'steps': steps,
            'reasoning_time': time.time()
        }
    
    # =====================================
    # Planning Methods
    # =====================================
    
    async def _create_plan(self, goal: Goal, constraints: List[str] = None) -> Optional[Plan]:
        """Create an execution plan for a goal"""
        try:
            plan = Plan(
                id=f"plan_{goal.id}_{int(time.time())}",
                goal_id=goal.id
            )
            
            # Simple planning algorithm - break down goal into steps
            if "flow" in goal.description.lower():
                # Kotler flow optimization plan
                plan.add_step(
                    "analyze_current_state",
                    {"focus": "flow_state", "metrics": ["challenge", "skill", "stress"]},
                    "Current flow state assessed"
                )
                plan.add_step(
                    "identify_optimization_targets",
                    {"strategy": "challenge_skill_balance"},
                    "Optimization targets identified"
                )
                plan.add_step(
                    "implement_interventions",
                    {"type": "adaptive", "real_time": True},
                    "Flow interventions implemented"
                )
                plan.add_step(
                    "monitor_progress",
                    {"metrics": ["flow_improvement", "satisfaction"]},
                    "Progress monitoring established"
                )
                plan.confidence = 0.8
                
            elif "problem" in goal.description.lower():
                # General problem-solving plan
                plan.add_step(
                    "define_problem",
                    {"approach": "systematic"},
                    "Problem clearly defined"
                )
                plan.add_step(
                    "gather_information",
                    {"sources": ["memory", "external", "analysis"]},
                    "Relevant information collected"
                )
                plan.add_step(
                    "generate_solutions",
                    {"method": "brainstorming", "minimum": 3},
                    "Multiple solutions generated"
                )
                plan.add_step(
                    "evaluate_options",
                    {"criteria": ["feasibility", "effectiveness", "resources"]},
                    "Best solution selected"
                )
                plan.add_step(
                    "implement_solution",
                    {"monitoring": True},
                    "Solution implemented and monitored"
                )
                plan.confidence = 0.7
                
            else:
                # Generic goal plan
                plan.add_step(
                    "analyze_goal",
                    {"goal": goal.description},
                    "Goal requirements analyzed"
                )
                plan.add_step(
                    "identify_resources",
                    {"type": "required"},
                    "Required resources identified"
                )
                plan.add_step(
                    "execute_actions",
                    {"approach": "systematic"},
                    "Goal-directed actions executed"
                )
                plan.add_step(
                    "verify_completion",
                    {"criteria": goal.requirements},
                    "Goal completion verified"
                )
                plan.confidence = 0.6
            
            # Apply constraints
            if constraints:
                for constraint in constraints:
                    if "time" in constraint.lower():
                        plan.estimated_duration = 300  # 5 minutes default
                    elif "resource" in constraint.lower():
                        plan.confidence *= 0.9  # Reduce confidence for resource constraints
            
            return plan
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} planning error: {e}")
            return None
    
    async def _make_decision(self, options: List[Any], criteria: Dict[str, float], 
                           strategy: str = 'multi_criteria') -> Dict[str, Any]:
        """Make a decision between multiple options"""
        try:
            if not options:
                return {'error': 'No options provided'}
            
            if len(options) == 1:
                return {
                    'selected_option': options[0],
                    'confidence': 0.8,
                    'reason': 'Only option available'
                }
            
            # Score each option
            option_scores = []
            
            for i, option in enumerate(options):
                score = 0.0
                criterion_details = {}
                
                # Apply criteria (simplified scoring)
                for criterion, weight in criteria.items():
                    # Simple scoring based on option characteristics
                    if isinstance(option, dict):
                        criterion_score = option.get(criterion, 0.5)
                    else:
                        # Hash-based scoring for consistency
                        criterion_score = 0.3 + (hash(f"{option}_{criterion}") % 70) / 100
                    
                    score += criterion_score * weight
                    criterion_details[criterion] = criterion_score
                
                option_scores.append({
                    'option': option,
                    'score': score,
                    'criteria_scores': criterion_details
                })
            
            # Sort by score (highest first)
            option_scores.sort(key=lambda x: x['score'], reverse=True)
            
            best_option = option_scores[0]
            confidence = min(0.95, best_option['score'])
            
            return {
                'selected_option': best_option['option'],
                'confidence': confidence,
                'score': best_option['score'],
                'criteria_scores': best_option['criteria_scores'],
                'all_scores': option_scores,
                'strategy': strategy,
                'reason': f'Highest score ({best_option["score"]:.2f}) using {strategy} strategy'
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} decision error: {e}")
            return {
                'error': str(e),
                'selected_option': options[0] if options else None,
                'confidence': 0.1
            }
    
    async def _find_similar_cases(self, problem: str) -> List[Dict[str, Any]]:
        """Find similar cases from memory"""
        try:
            # Search working memory for similar problems
            similar_cases = await self.search_memory(
                MemoryType.WORKING,
                {'key_pattern': 'reasoning_result'}
            )
            
            # Filter for relevance (simplified)
            relevant_cases = []
            problem_words = set(problem.lower().split())
            
            for case in similar_cases:
                if isinstance(case, dict) and 'value' in case:
                    case_data = case['value']
                    if isinstance(case_data, dict) and 'conclusion' in case_data:
                        case_words = set(case_data['conclusion'].lower().split())
                        # Simple similarity based on word overlap
                        similarity = len(problem_words & case_words) / max(len(problem_words), 1)
                        
                        if similarity > 0.2:  # 20% word overlap threshold
                            relevant_cases.append({
                                'case': case_data,
                                'similarity': similarity,
                                'description': case_data.get('conclusion', 'Unknown case')
                            })
            
            # Sort by similarity
            relevant_cases.sort(key=lambda x: x['similarity'], reverse=True)
            
            return relevant_cases[:5]  # Return top 5 similar cases
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} case search error: {e}")
            return []
    
    async def _process_reasoning_response(self, message: Message, context: ReasoningContext):
        """Process a response in the context of ongoing reasoning"""
        try:
            # Extract useful information from the response
            response_content = message.content
            
            # Update available information in context
            if 'data' in response_content:
                context.available_information.update(response_content['data'])
            
            # Store the interaction in memory
            await self.remember(
                MemoryType.WORKING,
                f"reasoning_interaction_{message.id}",
                {
                    'request_id': context.request_id,
                    'response': response_content,
                    'timestamp': time.time()
                },
                {'interaction_type': 'reasoning_response'}
            )
            
            logger.debug(f"Agent {self.agent_id} processed reasoning response for {context.request_id}")
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} error processing reasoning response: {e}")
    
    # =====================================
    # Goal and Plan Management
    # =====================================
    
    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """Execute a specific plan"""
        try:
            if plan_id not in self.plans:
                return {'success': False, 'error': 'Plan not found'}
            
            plan = self.plans[plan_id]
            goal = self.goals.get(plan.goal_id)
            
            if not goal:
                return {'success': False, 'error': 'Associated goal not found'}
            
            execution_log = []
            
            while not plan.is_complete():
                current_step = plan.get_current_step()
                if not current_step:
                    break
                
                # Execute step
                step_result = await self._execute_plan_step(current_step, goal)
                execution_log.append(step_result)
                
                # Update step status
                current_step['status'] = 'completed' if step_result['success'] else 'failed'
                current_step['end_time'] = time.time()
                current_step['actual_outcome'] = step_result.get('outcome')
                
                # Move to next step if successful
                if step_result['success']:
                    plan.advance_step()
                    goal.progress = plan.current_step / len(plan.steps)
                else:
                    # Plan failed
                    goal.status = 'failed'
                    break
            
            # Update goal status
            if plan.is_complete():
                goal.status = 'completed'
                goal.progress = 1.0
            
            return {
                'success': plan.is_complete(),
                'plan_id': plan_id,
                'goal_id': goal.id,
                'final_status': goal.status,
                'progress': goal.progress,
                'execution_log': execution_log
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} plan execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'plan_id': plan_id
            }
    
    async def _execute_plan_step(self, step: Dict[str, Any], goal: Goal) -> Dict[str, Any]:
        """Execute a single plan step"""
        try:
            step['start_time'] = time.time()
            step['status'] = 'executing'
            
            action = step['action']
            parameters = step.get('parameters', {})
            
            # Simulate step execution based on action type
            if action in ['analyze_current_state', 'analyze_goal', 'define_problem']:
                # Analysis steps
                await asyncio.sleep(0.1)  # Simulate processing time
                outcome = f"Analysis completed for {action}"
                success = True
                
            elif action in ['gather_information', 'identify_resources', 'identify_optimization_targets']:
                # Information gathering steps
                await asyncio.sleep(0.2)
                outcome = f"Information gathered for {action}"
                success = True
                
            elif action in ['implement_interventions', 'implement_solution', 'execute_actions']:
                # Implementation steps
                await asyncio.sleep(0.3)
                outcome = f"Implementation completed for {action}"
                success = True
                
            elif action in ['monitor_progress', 'verify_completion']:
                # Monitoring steps
                await asyncio.sleep(0.1)
                outcome = f"Monitoring established for {action}"
                success = True
                
            else:
                # Generic step execution
                await asyncio.sleep(0.2)
                outcome = f"Step {action} executed"
                success = True
            
            # Store step result in memory
            await self.remember(
                MemoryType.WORKING,
                f"step_result_{step.get('step_id', 'unknown')}",
                {
                    'step': step,
                    'outcome': outcome,
                    'success': success,
                    'goal_id': goal.id
                },
                {'step_execution': True}
            )
            
            return {
                'success': success,
                'outcome': outcome,
                'step_id': step.get('step_id'),
                'execution_time': time.time() - step['start_time']
            }
            
        except Exception as e:
            logger.error(f"Agent {self.agent_id} step execution error: {e}")
            return {
                'success': False,
                'outcome': f"Step failed: {str(e)}",
                'step_id': step.get('step_id'),
                'error': str(e)
            }
    
    # =====================================
    # Agent Status and Information
    # =====================================
    
    def get_deliberative_status(self) -> Dict[str, Any]:
        """Get deliberative agent specific status"""
        base_status = self.get_status()
        
        deliberative_status = {
            'goals': {
                'total': len(self.goals),
                'active': len([g for g in self.goals.values() if g.status == 'active']),
                'completed': len([g for g in self.goals.values() if g.status == 'completed']),
                'failed': len([g for g in self.goals.values() if g.status == 'failed'])
            },
            'plans': {
                'total': len(self.plans),
                'executing': len([p for p in self.plans.values() if not p.is_complete()]),
                'completed': len([p for p in self.plans.values() if p.is_complete()])
            },
            'reasoning': {
                'default_strategy': self.default_reasoning_strategy.value,
                'active_contexts': len(self.active_reasoning_contexts),
                'successful_strategies': dict(self.successful_strategies),
                'failed_strategies': dict(self.failed_strategies)
            },
            'performance': {
                'confidence_threshold': self.confidence_threshold,
                'current_confidence': self.metrics.confidence_score,
                'average_response_time': self.metrics.average_response_time
            }
        }
        
        base_status.update(deliberative_status)
        return base_status
    
    async def cleanup_expired_goals(self):
        """Remove expired goals and associated plans"""
        expired_goals = []
        
        for goal_id, goal in self.goals.items():
            if goal.is_expired():
                expired_goals.append(goal_id)
        
        for goal_id in expired_goals:
            # Remove goal
            del self.goals[goal_id]
            
            # Remove associated plans
            plans_to_remove = [pid for pid, plan in self.plans.items() if plan.goal_id == goal_id]
            for pid in plans_to_remove:
                del self.plans[pid]
            
            logger.info(f"Agent {self.agent_id} cleaned up expired goal {goal_id} and {len(plans_to_remove)} plans")
        
        return len(expired_goals)
    
    def __repr__(self) -> str:
        return f"<DeliberativeAgent(id={self.agent_id}, goals={len(self.goals)}, plans={len(self.plans)}, strategy={self.default_reasoning_strategy.value})>"

# =====================================
# Utility Functions
# =====================================

def create_deliberative_agent(agent_id: str, config: Dict[str, Any] = None) -> DeliberativeAgent:
    """Factory function to create a deliberative agent"""
    return DeliberativeAgent(agent_id, config=config)

def create_kotler_agent(agent_id: str = "kotler_optimizer") -> DeliberativeAgent:
    """Create a specialized agent for Kotler flow optimization"""
    capabilities = AgentCapabilities(
        capabilities={"flow_analysis", "kotler_optimization", "behavioral_intervention", "progress_monitoring"},
        memory_types={MemoryType.WORKING, MemoryType.EPISODIC, MemoryType.EMOTIONAL},
        max_concurrent_tasks=3
    )
    
    config = {
        'default_reasoning_strategy': 'multi_criteria',
        'confidence_threshold': 0.8,
        'working_memory_size': 200,
        'working_memory_ttl': 7200  # 2 hours for flow sessions
    }
    
    return DeliberativeAgent(agent_id, capabilities, config)
