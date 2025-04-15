"""
behavior_controller.py - Advanced Agent Behavior Control for Neuron Framework

This module implements advanced behavior control mechanisms for agents in the
Neuron framework, allowing for dynamic modification of agent behavior based
on context, goals, and learning.

The behavior controller is inspired by how the brain's prefrontal cortex and
other executive functions regulate and modulate behavior based on context,
goals, and past experiences.
"""

import asyncio
import copy
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .agent import BaseAgent
from .config import config
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class BehaviorTrait(Enum):
    """
    Behavioral traits that can be adjusted for agents.
    
    These represent fundamental aspects of an agent's behavior that
    can be adjusted to achieve different behavioral profiles.
    """
    CURIOSITY = "curiosity"          # Propensity to explore and learn
    CAUTION = "caution"              # Tendency to avoid risky actions
    PERSISTENCE = "persistence"      # Inclination to continue despite challenges
    COOPERATION = "cooperation"      # Willingness to work with other agents
    CREATIVITY = "creativity"        # Tendency to generate novel approaches
    RATIONALITY = "rationality"      # Reliance on logical reasoning
    RESPONSIVENESS = "responsiveness"  # Speed of reaction to stimuli
    AUTONOMY = "autonomy"            # Independence in decision-making


class BehaviorMode(Enum):
    """
    Operating modes for agent behavior.
    
    These represent high-level behavior patterns that influence
    how an agent approaches its tasks and interactions.
    """
    NORMAL = "normal"                # Standard balanced behavior
    LEARNING = "learning"            # Focused on acquiring knowledge
    PERFORMANCE = "performance"      # Optimized for task efficiency
    COLLABORATIVE = "collaborative"  # Oriented towards teamwork
    CREATIVE = "creative"            # Focused on novel solutions
    CONSERVATIVE = "conservative"    # Risk-averse and cautious
    AGGRESSIVE = "aggressive"        # Proactive and risk-tolerant
    ADAPTIVE = "adaptive"            # Dynamically adjusts to context


@dataclass
class BehaviorProfile:
    """
    Defines a complete behavioral profile for an agent.
    
    A BehaviorProfile includes trait values, selected mode, and
    additional behavioral parameters that together determine
    how an agent will behave.
    """
    traits: Dict[BehaviorTrait, float] = field(default_factory=dict)  # Trait values (0.0 to 1.0)
    mode: BehaviorMode = BehaviorMode.NORMAL  # Operating mode
    parameters: Dict[str, Any] = field(default_factory=dict)  # Additional parameters
    
    def __post_init__(self):
        """Initialize default trait values if not provided."""
        # Set default values for any missing traits
        for trait in BehaviorTrait:
            if trait not in self.traits:
                self.traits[trait] = 0.5  # Default value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "mode": self.mode.value,
            "parameters": self.parameters,
            "traits": {t.value: v for t, v in self.traits.items()}
        }
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BehaviorProfile':
        """Create from dictionary representation."""
        profile = cls(
            mode=BehaviorMode(data["mode"]),
            parameters=data.get("parameters", {})
        )
        
        # Convert trait strings to enums
        for trait_str, value in data.get("traits", {}).items():
            try:
                trait = BehaviorTrait(trait_str)
                profile.traits[trait] = value
            except ValueError:
                logger.warning(f"Unknown behavior trait: {trait_str}")
        
        return profile
    
    def set_trait(self, trait: BehaviorTrait, value: float) -> None:
        """
        Set a trait value.
        
        Args:
            trait: Trait to set
            value: Value for the trait (0.0 to 1.0)
            
        Raises:
            ValueError: If the value is outside the valid range
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Trait value must be between 0.0 and 1.0, got {value}")
        
        self.traits[trait] = value
    
    def get_trait(self, trait: BehaviorTrait) -> float:
        """
        Get a trait value.
        
        Args:
            trait: Trait to get
            
        Returns:
            Value of the trait
        """
        return self.traits.get(trait, 0.5)
    
    def set_mode(self, mode: BehaviorMode) -> None:
        """
        Set the behavior mode.
        
        Args:
            mode: Mode to set
        """
        self.mode = mode
    
    def set_parameter(self, key: str, value: Any) -> None:
        """
        Set a behavior parameter.
        
        Args:
            key: Parameter key
            value: Parameter value
        """
        self.parameters[key] = value
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get a behavior parameter.
        
        Args:
            key: Parameter key
            default: Default value if not found
            
        Returns:
            Parameter value or default
        """
        return self.parameters.get(key, default)


class BehaviorModifier(ABC):
    """
    Abstract base class for behavior modifiers.
    
    Behavior modifiers are components that can adjust an agent's
    behavior based on specific conditions or contexts. They provide
    a way to implement adaptive behavior.
    """
    
    @abstractmethod
    def apply(self, profile: BehaviorProfile, context: Dict[str, Any]) -> BehaviorProfile:
        """
        Apply the modifier to a behavior profile.
        
        Args:
            profile: Behavior profile to modify
            context: Context information for making decisions
            
        Returns:
            Modified behavior profile
        """
        pass
    
    @abstractmethod
    def should_apply(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this modifier should be applied.
        
        Args:
            context: Context information for making decisions
            
        Returns:
            True if the modifier should be applied, False otherwise
        """
        pass


class ContextualModifier(BehaviorModifier):
    """
    Modifier that adjusts behavior based on contextual factors.
    
    Contextual modifiers respond to specific situations or environments,
    adjusting behavior to suit the current context.
    """
    
    def __init__(self, name: str, condition: Callable[[Dict[str, Any]], bool],
                trait_adjustments: Dict[BehaviorTrait, float] = None,
                mode_override: BehaviorMode = None,
                parameter_overrides: Dict[str, Any] = None):
        """
        Initialize a contextual modifier.
        
        Args:
            name: Name of the modifier
            condition: Function that determines if the modifier should apply
            trait_adjustments: Adjustments to apply to traits
            mode_override: Mode to switch to, if any
            parameter_overrides: Parameters to override
        """
        self.name = name
        self.condition = condition
        self.trait_adjustments = trait_adjustments or {}
        self.mode_override = mode_override
        self.parameter_overrides = parameter_overrides or {}
    
    def should_apply(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this modifier should be applied.
        
        Args:
            context: Context information for making decisions
            
        Returns:
            True if the modifier should be applied, False otherwise
        """
        try:
            return self.condition(context)
        except Exception as e:
            logger.error(f"Error evaluating condition for modifier {self.name}: {e}")
            return False
    
    def apply(self, profile: BehaviorProfile, context: Dict[str, Any]) -> BehaviorProfile:
        """
        Apply the modifier to a behavior profile.
        
        Args:
            profile: Behavior profile to modify
            context: Context information for making decisions
            
        Returns:
            Modified behavior profile
        """
        # Create a copy to avoid modifying the original
        modified = copy.deepcopy(profile)
        
        # Apply trait adjustments
        for trait, adjustment in self.trait_adjustments.items():
            current = modified.get_trait(trait)
            modified.set_trait(trait, max(0.0, min(1.0, current + adjustment)))
        
        # Apply mode override
        if self.mode_override:
            modified.set_mode(self.mode_override)
        
        # Apply parameter overrides
        for key, value in self.parameter_overrides.items():
            modified.set_parameter(key, value)
        
        return modified


class GoalBasedModifier(BehaviorModifier):
    """
    Modifier that adjusts behavior based on goals.
    
    Goal-based modifiers optimize behavior to achieve specific
    goals or objectives, emphasizing traits and modes that are
    conducive to the current goal.
    """
    
    def __init__(self, name: str, goal_type: str,
                trait_profiles: Dict[BehaviorTrait, float] = None,
                mode: BehaviorMode = None,
                parameters: Dict[str, Any] = None):
        """
        Initialize a goal-based modifier.
        
        Args:
            name: Name of the modifier
            goal_type: Type of goal this modifier applies to
            trait_profiles: Ideal trait values for this goal
            mode: Behavior mode for this goal
            parameters: Behavior parameters for this goal
        """
        self.name = name
        self.goal_type = goal_type
        self.trait_profiles = trait_profiles or {}
        self.mode = mode
        self.parameters = parameters or {}
    
    def should_apply(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this modifier should be applied.
        
        Args:
            context: Context information for making decisions
            
        Returns:
            True if the modifier should be applied, False otherwise
        """
        # Check if the current goal matches this modifier's goal type
        current_goal = context.get("current_goal", {})
        return current_goal.get("type") == self.goal_type
    
    def apply(self, profile: BehaviorProfile, context: Dict[str, Any]) -> BehaviorProfile:
        """
        Apply the modifier to a behavior profile.
        
        Args:
            profile: Behavior profile to modify
            context: Context information for making decisions
            
        Returns:
            Modified behavior profile
        """
        # Create a copy to avoid modifying the original
        modified = copy.deepcopy(profile)
        
        # Get goal weight (how important is this goal)
        current_goal = context.get("current_goal", {})
        goal_weight = current_goal.get("weight", 0.5)
        
        # Apply trait profile with weighting
        for trait, ideal_value in self.trait_profiles.items():
            current = modified.get_trait(trait)
            # Blend current and ideal values based on goal weight
            new_value = current * (1 - goal_weight) + ideal_value * goal_weight
            modified.set_trait(trait, new_value)
        
        # Apply mode if specified
        if self.mode:
            modified.set_mode(self.mode)
        
        # Apply parameters
        for key, value in self.parameters.items():
            modified.set_parameter(key, value)
        
        return modified


class LearningModifier(BehaviorModifier):
    """
    Modifier that adjusts behavior based on learning and experience.
    
    Learning modifiers adapt behavior based on past experiences and
    feedback, allowing agents to improve their behavior over time.
    """
    
    def __init__(self, name: str, trait_learning_rates: Dict[BehaviorTrait, float] = None):
        """
        Initialize a learning modifier.
        
        Args:
            name: Name of the modifier
            trait_learning_rates: Learning rates for each trait
        """
        self.name = name
        self.trait_learning_rates = trait_learning_rates or {}
        
        # Default learning rates
        for trait in BehaviorTrait:
            if trait not in self.trait_learning_rates:
                self.trait_learning_rates[trait] = 0.1
        
        # Track trait adjustments from feedback
        self.trait_adjustments = {trait: 0.0 for trait in BehaviorTrait}
        
        # Experience tracking
        self.experience_count = 0
        self.last_feedback = {}
    
    def should_apply(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this modifier should be applied.
        
        Args:
            context: Context information for making decisions
            
        Returns:
            True if the modifier should be applied, False otherwise
        """
        # Apply if there's feedback or experience data
        return ("feedback" in context or 
                "experience" in context or 
                self.experience_count > 0)
    
    def apply(self, profile: BehaviorProfile, context: Dict[str, Any]) -> BehaviorProfile:
        """
        Apply the modifier to a behavior profile.
        
        Args:
            profile: Behavior profile to modify
            context: Context information for making decisions
            
        Returns:
            Modified behavior profile
        """
        # Create a copy to avoid modifying the original
        modified = copy.deepcopy(profile)
        
        # Process new feedback
        feedback = context.get("feedback", {})
        if feedback and feedback != self.last_feedback:
            self._process_feedback(feedback)
            self.last_feedback = copy.deepcopy(feedback)
        
        # Process new experience
        experience = context.get("experience", {})
        if experience:
            self._process_experience(experience)
        
        # Apply accumulated trait adjustments
        for trait, adjustment in self.trait_adjustments.items():
            current = modified.get_trait(trait)
            modified.set_trait(trait, max(0.0, min(1.0, current + adjustment)))
        
        # Apply mode based on experience level
        if self.experience_count > 100:
            # Experienced agent - emphasize performance
            modified.set_mode(BehaviorMode.PERFORMANCE)
        elif self.experience_count > 50:
            # Moderately experienced - balance learning and performance
            modified.set_mode(BehaviorMode.ADAPTIVE)
        elif self.experience_count > 0:
            # Novice agent - emphasize learning
            modified.set_mode(BehaviorMode.LEARNING)
        
        # Update parameters based on experience
        if self.experience_count > 0:
            decay_factor = min(1.0, self.experience_count / 1000)  # Increases with experience
            modified.set_parameter("learning_rate_decay", decay_factor)
        
        return modified
    
    def _process_feedback(self, feedback: Dict[str, Any]) -> None:
        """
        Process feedback to adjust behavior.
        
        Args:
            feedback: Feedback data
        """
        # Extract overall score
        score = feedback.get("score", 0.0)
        
        # Extract trait-specific feedback
        trait_feedback = feedback.get("traits", {})
        
        # Update trait adjustments based on feedback
        for trait in BehaviorTrait:
            trait_score = trait_feedback.get(trait.value, score)
            learning_rate = self.trait_learning_rates[trait]
            
            # Positive feedback reinforces traits, negative feedback reduces them
            if trait_score > 0:
                self.trait_adjustments[trait] += trait_score * learning_rate
            else:
                self.trait_adjustments[trait] += trait_score * learning_rate
            
            # Limit accumulated adjustments
            self.trait_adjustments[trait] = max(-0.5, min(0.5, self.trait_adjustments[trait]))
    
    def _process_experience(self, experience: Dict[str, Any]) -> None:
        """
        Process experience data to adjust behavior.
        
        Args:
            experience: Experience data
        """
        # Increment experience counter
        self.experience_count += 1
        
        # Extract outcome information
        outcome = experience.get("outcome", "neutral")
        
        # Adjust traits based on outcome
        if outcome == "success":
            # Reinforce current behavior slightly
            for trait in BehaviorTrait:
                self.trait_adjustments[trait] *= 1.05  # Small reinforcement
        elif outcome == "failure":
            # Reduce current behavior slightly
            for trait in BehaviorTrait:
                self.trait_adjustments[trait] *= 0.95  # Small reduction


class SocialModifier(BehaviorModifier):
    """
    Modifier that adjusts behavior based on social context.
    
    Social modifiers adapt behavior to the social environment,
    adjusting how an agent interacts with other agents based
    on relationships and social dynamics.
    """
    
    def __init__(self, name: str):
        """
        Initialize a social modifier.
        
        Args:
            name: Name of the modifier
        """
        self.name = name
        
        # Track relationships with other agents
        self.relationships = {}  # agent_id -> relationship_score (-1.0 to 1.0)
        
        # Track group affiliation
        self.group_affiliation = {}  # group_id -> affiliation_score (0.0 to 1.0)
    
    def should_apply(self, context: Dict[str, Any]) -> bool:
        """
        Determine if this modifier should be applied.
        
        Args:
            context: Context information for making decisions
            
        Returns:
            True if the modifier should be applied, False otherwise
        """
        # Apply if there's social context
        return "social" in context or "interaction_agent" in context
    
    def apply(self, profile: BehaviorProfile, context: Dict[str, Any]) -> BehaviorProfile:
        """
        Apply the modifier to a behavior profile.
        
        Args:
            profile: Behavior profile to modify
            context: Context information for making decisions
            
        Returns:
            Modified behavior profile
        """
        # Create a copy to avoid modifying the original
        modified = copy.deepcopy(profile)
        
        # Update social information
        social_context = context.get("social", {})
        if social_context:
            self._update_social_data(social_context)
        
        # Get interaction agent
        interaction_agent = context.get("interaction_agent")
        
        # Adjust behavior based on relationship if interacting with specific agent
        if interaction_agent and interaction_agent in self.relationships:
            relationship = self.relationships[interaction_agent]
            
            # Adjust cooperation based on relationship
            cooperation = modified.get_trait(BehaviorTrait.COOPERATION)
            modified.set_trait(
                BehaviorTrait.COOPERATION,
                max(0.1, min(0.9, cooperation + relationship * 0.3))
            )
            
            # Adjust caution based on relationship (more cautious with negative relationships)
            caution = modified.get_trait(BehaviorTrait.CAUTION)
            modified.set_trait(
                BehaviorTrait.CAUTION,
                max(0.1, min(0.9, caution - relationship * 0.2))
            )
        
        # Adjust behavior based on group context
        group_context = social_context.get("group")
        if group_context:
            group_id = group_context.get("id")
            group_role = group_context.get("role")
            
            if group_id and group_id in self.group_affiliation:
                affiliation = self.group_affiliation[group_id]
                
                # Stronger group affiliation increases cooperation
                cooperation = modified.get_trait(BehaviorTrait.COOPERATION)
                modified.set_trait(
                    BehaviorTrait.COOPERATION,
                    max(0.2, min(0.9, cooperation + affiliation * 0.3))
                )
                
                # Leadership role increases autonomy
                if group_role == "leader":
                    autonomy = modified.get_trait(BehaviorTrait.AUTONOMY)
                    modified.set_trait(BehaviorTrait.AUTONOMY, max(0.6, autonomy))
                    
                    # Leaders tend to be more responsive
                    responsiveness = modified.get_trait(BehaviorTrait.RESPONSIVENESS)
                    modified.set_trait(BehaviorTrait.RESPONSIVENESS, max(0.6, responsiveness))
                
                # Support role increases rationality
                elif group_role == "support":
                    rationality = modified.get_trait(BehaviorTrait.RATIONALITY)
                    modified.set_trait(BehaviorTrait.RATIONALITY, max(0.6, rationality))
        
        # Set collaborative mode if in a strong social context
        if (interaction_agent and interaction_agent in self.relationships and 
            self.relationships[interaction_agent] > 0.5):
            modified.set_mode(BehaviorMode.COLLABORATIVE)
        
        return modified
    
    def _update_social_data(self, social_context: Dict[str, Any]) -> None:
        """
        Update social data from context.
        
        Args:
            social_context: Social context information
        """
        # Update relationships
        interactions = social_context.get("interactions", [])
        for interaction in interactions:
            agent_id = interaction.get("agent_id")
            quality = interaction.get("quality", 0.0)  # -1.0 to 1.0
            
            if agent_id:
                # Update relationship with exponential moving average
                current = self.relationships.get(agent_id, 0.0)
                alpha = 0.2  # Learning rate
                self.relationships[agent_id] = current * (1 - alpha) + quality * alpha
        
        # Update group affiliations
        groups = social_context.get("groups", [])
        for group in groups:
            group_id = group.get("id")
            affiliation = group.get("affiliation", 0.5)  # 0.0 to 1.0
            
            if group_id:
                # Update affiliation with exponential moving average
                current = self.group_affiliation.get(group_id, 0.0)
                alpha = 0.1  # Learning rate
                self.group_affiliation[group_id] = current * (1 - alpha) + affiliation * alpha


class BehaviorController:
    """
    Controls and manages agent behavior.
    
    The BehaviorController implements a behavior modification system
    that dynamically adjusts how agents behave based on various factors,
    allowing for adaptive and context-sensitive agent behavior.
    """
    
    def __init__(self):
        """Initialize the behavior controller."""
        self._base_profile = BehaviorProfile()  # Default profile
        self._current_profile = None  # Currently active profile
        self._modifiers = []  # List of behavior modifiers
        self._lock = threading.RLock()
        
        # Initialize with default modifiers
        self._setup_default_modifiers()
        
        logger.debug("Initialized BehaviorController")
    
    def _setup_default_modifiers(self) -> None:
        """Set up default behavior modifiers."""
        # Create a learning modifier
        learning_modifier = LearningModifier("default_learning")
        self.add_modifier(learning_modifier)
        
        # Create a social modifier
        social_modifier = SocialModifier("default_social")
        self.add_modifier(social_modifier)
        
        # Create some contextual modifiers
        
        # High workload modifier
        high_workload = ContextualModifier(
            name="high_workload",
            condition=lambda ctx: ctx.get("workload", 0) > 0.8,
            trait_adjustments={
                BehaviorTrait.RESPONSIVENESS: 0.2,
                BehaviorTrait.CAUTION: -0.1,
                BehaviorTrait.CREATIVITY: -0.1
            },
            mode_override=BehaviorMode.PERFORMANCE,
            parameter_overrides={"timeout_multiplier": 0.8}
        )
        self.add_modifier(high_workload)
        
        # Error recovery modifier
        error_recovery = ContextualModifier(
            name="error_recovery",
            condition=lambda ctx: ctx.get("error_count", 0) > 3,
            trait_adjustments={
                BehaviorTrait.CAUTION: 0.3,
                BehaviorTrait.RATIONALITY: 0.2,
                BehaviorTrait.PERSISTENCE: 0.2
            },
            mode_override=BehaviorMode.CONSERVATIVE,
            parameter_overrides={"validation_level": "strict"}
        )
        self.add_modifier(error_recovery)
        
        # Create some goal-based modifiers
        
        # Learning goal modifier
        learning_goal = GoalBasedModifier(
            name="learning_goal",
            goal_type="learn",
            trait_profiles={
                BehaviorTrait.CURIOSITY: 0.9,
                BehaviorTrait.PERSISTENCE: 0.7,
                BehaviorTrait.CREATIVITY: 0.6
            },
            mode=BehaviorMode.LEARNING,
            parameters={"exploration_rate": 0.3}
        )
        self.add_modifier(learning_goal)
        
        # Problem-solving goal modifier
        problem_solving = GoalBasedModifier(
            name="problem_solving",
            goal_type="solve",
            trait_profiles={
                BehaviorTrait.RATIONALITY: 0.8,
                BehaviorTrait.PERSISTENCE: 0.8,
                BehaviorTrait.CREATIVITY: 0.7
            },
            mode=BehaviorMode.ADAPTIVE,
            parameters={"solution_depth": 3}
        )
        self.add_modifier(problem_solving)
        
        # Collaborative goal modifier
        collaboration = GoalBasedModifier(
            name="collaboration",
            goal_type="collaborate",
            trait_profiles={
                BehaviorTrait.COOPERATION: 0.9,
                BehaviorTrait.RESPONSIVENESS: 0.8,
                BehaviorTrait.AUTONOMY: 0.4
            },
            mode=BehaviorMode.COLLABORATIVE,
            parameters={"message_frequency": "high"}
        )
        self.add_modifier(collaboration)
    
    def set_base_profile(self, profile: BehaviorProfile) -> None:
        """
        Set the base behavior profile.
        
        Args:
            profile: Base behavior profile
        """
        with self._lock:
            self._base_profile = copy.deepcopy(profile)
            logger.debug("Set new base behavior profile")
    
    def get_base_profile(self) -> BehaviorProfile:
        """
        Get the base behavior profile.
        
        Returns:
            Base behavior profile
        """
        with self._lock:
            return copy.deepcopy(self._base_profile)
    
    def add_modifier(self, modifier: BehaviorModifier) -> None:
        """
        Add a behavior modifier.
        
        Args:
            modifier: Behavior modifier to add
        """
        with self._lock:
            self._modifiers.append(modifier)
            logger.debug(f"Added behavior modifier: {modifier.name}")
    
    def remove_modifier(self, modifier_name: str) -> bool:
        """
        Remove a behavior modifier.
        
        Args:
            modifier_name: Name of the modifier to remove
            
        Returns:
            True if the modifier was removed, False if not found
        """
        with self._lock:
            for i, modifier in enumerate(self._modifiers):
                if hasattr(modifier, 'name') and modifier.name == modifier_name:
                    del self._modifiers[i]
                    logger.debug(f"Removed behavior modifier: {modifier_name}")
                    return True
            return False
    
    def get_current_profile(self, context: Dict[str, Any] = None) -> BehaviorProfile:
        """
        Get the current behavior profile.
        
        This computes a behavior profile based on the base profile
        and applicable modifiers for the given context.
        
        Args:
            context: Context information for behavior decisions
            
        Returns:
            Current behavior profile
        """
        with self._lock:
            # Start with the base profile
            profile = copy.deepcopy(self._base_profile)
            
            # Default empty context
            if context is None:
                context = {}
            
            # Apply modifiers that should be applied for this context
            for modifier in self._modifiers:
                if modifier.should_apply(context):
                    profile = modifier.apply(profile, context)
            
            # Cache the current profile
            self._current_profile = profile
            
            return copy.deepcopy(profile)
    
    def get_trait_value(self, trait: BehaviorTrait, context: Dict[str, Any] = None) -> float:
        """
        Get the current value of a behavior trait.
        
        Args:
            trait: Behavior trait to get
            context: Context information for behavior decisions
            
        Returns:
            Current value of the trait
        """
        profile = self.get_current_profile(context)
        return profile.get_trait(trait)
    
    def get_current_mode(self, context: Dict[str, Any] = None) -> BehaviorMode:
        """
        Get the current behavior mode.
        
        Args:
            context: Context information for behavior decisions
            
        Returns:
            Current behavior mode
        """
        profile = self.get_current_profile(context)
        return profile.mode
    
    def get_parameter(self, key: str, default: Any = None, 
                    context: Dict[str, Any] = None) -> Any:
        """
        Get a behavior parameter.
        
        Args:
            key: Parameter key
            default: Default value if not found
            context: Context information for behavior decisions
            
        Returns:
            Parameter value or default
        """
        profile = self.get_current_profile(context)
        return profile.get_parameter(key, default)
    
    def provide_feedback(self, feedback: Dict[str, Any]) -> None:
        """
        Provide feedback for learning.
        
        This updates learning-based modifiers with feedback
        on agent performance.
        
        Args:
            feedback: Feedback data
        """
        with self._lock:
            # Create a context with just the feedback
            context = {"feedback": feedback}
            
            # Apply to learning modifiers
            for modifier in self._modifiers:
                if isinstance(modifier, LearningModifier) and modifier.should_apply(context):
                    # Apply feedback (the modifier will update its internal state)
                    modifier.apply(self._base_profile, context)
    
    def record_experience(self, experience: Dict[str, Any]) -> None:
        """
        Record an experience for learning.
        
        This updates learning-based modifiers with experience data.
        
        Args:
            experience: Experience data
        """
        with self._lock:
            # Create a context with just the experience
            context = {"experience": experience}
            
            # Apply to learning modifiers
            for modifier in self._modifiers:
                if isinstance(modifier, LearningModifier) and modifier.should_apply(context):
                    # Apply experience (the modifier will update its internal state)
                    modifier.apply(self._base_profile, context)
    
    def update_social_context(self, social_context: Dict[str, Any]) -> None:
        """
        Update social context information.
        
        This updates social modifiers with new social context data.
        
        Args:
            social_context: Social context data
        """
        with self._lock:
            # Create a context with just the social information
            context = {"social": social_context}
            
            # Apply to social modifiers
            for modifier in self._modifiers:
                if isinstance(modifier, SocialModifier) and modifier.should_apply(context):
                    # Apply social context (the modifier will update its internal state)
                    modifier.apply(self._base_profile, context)
    
    def create_profile_from_template(self, template_name: str) -> BehaviorProfile:
        """
        Create a behavior profile from a named template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            New behavior profile
            
        Raises:
            ValueError: If the template is not recognized
        """
        # Define some common behavior templates
        templates = {
            "balanced": BehaviorProfile(
                traits={t: 0.5 for t in BehaviorTrait},
                mode=BehaviorMode.NORMAL
            ),
            "explorer": BehaviorProfile(
                traits={
                    BehaviorTrait.CURIOSITY: 0.9,
                    BehaviorTrait.CREATIVITY: 0.7,
                    BehaviorTrait.AUTONOMY: 0.8,
                    BehaviorTrait.PERSISTENCE: 0.6,
                    BehaviorTrait.CAUTION: 0.3,
                    BehaviorTrait.COOPERATION: 0.4,
                    BehaviorTrait.RATIONALITY: 0.5,
                    BehaviorTrait.RESPONSIVENESS: 0.6
                },
                mode=BehaviorMode.CREATIVE,
                parameters={"exploration_rate": 0.3}
            ),
            "analyst": BehaviorProfile(
                traits={
                    BehaviorTrait.CURIOSITY: 0.6,
                    BehaviorTrait.CREATIVITY: 0.5,
                    BehaviorTrait.AUTONOMY: 0.4,
                    BehaviorTrait.PERSISTENCE: 0.7,
                    BehaviorTrait.CAUTION: 0.7,
                    BehaviorTrait.COOPERATION: 0.5,
                    BehaviorTrait.RATIONALITY: 0.9,
                    BehaviorTrait.RESPONSIVENESS: 0.4
                },
                mode=BehaviorMode.CONSERVATIVE,
                parameters={"analysis_depth": "high"}
            ),
            "team_player": BehaviorProfile(
                traits={
                    BehaviorTrait.CURIOSITY: 0.5,
                    BehaviorTrait.CREATIVITY: 0.5,
                    BehaviorTrait.AUTONOMY: 0.3,
                    BehaviorTrait.PERSISTENCE: 0.6,
                    BehaviorTrait.CAUTION: 0.5,
                    BehaviorTrait.COOPERATION: 0.9,
                    BehaviorTrait.RATIONALITY: 0.6,
                    BehaviorTrait.RESPONSIVENESS: 0.8
                },
                mode=BehaviorMode.COLLABORATIVE,
                parameters={"communication_frequency": "high"}
            ),
            "innovator": BehaviorProfile(
                traits={
                    BehaviorTrait.CURIOSITY: 0.8,
                    BehaviorTrait.CREATIVITY: 0.9,
                    BehaviorTrait.AUTONOMY: 0.7,
                    BehaviorTrait.PERSISTENCE: 0.7,
                    BehaviorTrait.CAUTION: 0.3,
                    BehaviorTrait.COOPERATION: 0.5,
                    BehaviorTrait.RATIONALITY: 0.6,
                    BehaviorTrait.RESPONSIVENESS: 0.5
                },
                mode=BehaviorMode.CREATIVE,
                parameters={"innovation_focus": "high"}
            ),
            "reliable": BehaviorProfile(
                traits={
                    BehaviorTrait.CURIOSITY: 0.4,
                    BehaviorTrait.CREATIVITY: 0.4,
                    BehaviorTrait.AUTONOMY: 0.5,
                    BehaviorTrait.PERSISTENCE: 0.8,
                    BehaviorTrait.CAUTION: 0.7,
                    BehaviorTrait.COOPERATION: 0.6,
                    BehaviorTrait.RATIONALITY: 0.7,
                    BehaviorTrait.RESPONSIVENESS: 0.7
                },
                mode=BehaviorMode.PERFORMANCE,
                parameters={"reliability_focus": "high"}
            )
        }
        
        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        return copy.deepcopy(templates[template_name])


class BehaviorControllerAgent:
    """
    Mixin class for agents with behavior control.
    
    This mixin adds behavior control capabilities to an agent,
    allowing it to utilize the BehaviorController for dynamic
    behavior modification.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the behavior controller mixin."""
        # Initialize the parent class
        super().__init__(*args, **kwargs)
        
        # Create a behavior controller
        self._behavior_controller = BehaviorController()
        
        # Initialize with a balanced profile
        balanced_profile = self._behavior_controller.create_profile_from_template("balanced")
        self._behavior_controller.set_base_profile(balanced_profile)
    
    def get_behavior_controller(self) -> BehaviorController:
        """
        Get the behavior controller.
        
        Returns:
            Behavior controller instance
        """
        return self._behavior_controller
    
    def get_behavior_context(self) -> Dict[str, Any]:
        """
        Get the current behavior context.
        
        This should be implemented by subclasses to provide
        relevant context information for behavior decisions.
        
        Returns:
            Behavior context
        """
        # Default implementation
        return {
            "workload": len(getattr(self, '_message_queue', [])) / 100,
            "error_count": getattr(self, '_metrics', Dict[str, Any]()).get("error_count", 0)
        }
    
    def get_trait_value(self, trait: BehaviorTrait) -> float:
        """
        Get the current value of a behavior trait.
        
        Args:
            trait: Behavior trait to get
            
        Returns:
            Current value of the trait
        """
        context = self.get_behavior_context()
        return self._behavior_controller.get_trait_value(trait, context)
    
    def get_current_mode(self) -> BehaviorMode:
        """
        Get the current behavior mode.
        
        Returns:
            Current behavior mode
        """
        context = self.get_behavior_context()
        return self._behavior_controller.get_current_mode(context)
    
    def get_behavior_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get a behavior parameter.
        
        Args:
            key: Parameter key
            default: Default value if not found
            
        Returns:
            Parameter value or default
        """
        context = self.get_behavior_context()
        return self._behavior_controller.get_parameter(key, default, context)
    
    def provide_feedback(self, feedback: Dict[str, Any]) -> None:
        """
        Provide feedback for learning.
        
        Args:
            feedback: Feedback data
        """
        self._behavior_controller.provide_feedback(feedback)
    
    def record_experience(self, experience: Dict[str, Any]) -> None:
        """
        Record an experience for learning.
        
        Args:
            experience: Experience data
        """
        self._behavior_controller.record_experience(experience)
    
    def update_social_context(self, social_context: Dict[str, Any]) -> None:
        """
        Update social context information.
        
        Args:
            social_context: Social context data
        """
        self._behavior_controller.update_social_context(social_context)
    
    def set_behavior_profile(self, profile: Union[BehaviorProfile, str]) -> None:
        """
        Set the base behavior profile.
        
        Args:
            profile: Behavior profile or template name
            
        Raises:
            ValueError: If the profile or template is invalid
        """
        if isinstance(profile, str):
            # Create from template
            profile = self._behavior_controller.create_profile_from_template(profile)
        
        self._behavior_controller.set_base_profile(profile)


def with_behavior_control(agent_class: Type) -> Type:
    """
    Decorator to add behavior control to an agent class.
    
    Args:
        agent_class: Agent class to enhance with behavior control
        
    Returns:
        Enhanced agent class
    """
    # Create a new class that inherits from BehaviorControllerAgent and the original class
    class BehaviorEnhancedAgent(BehaviorControllerAgent, agent_class):
        pass
    
    # Use the original class name
    BehaviorEnhancedAgent.__name__ = f"BehaviorEnhanced{agent_class.__name__}"
    BehaviorEnhancedAgent.__qualname__ = BehaviorEnhancedAgent.__name__
    
    return BehaviorEnhancedAgent
"""
