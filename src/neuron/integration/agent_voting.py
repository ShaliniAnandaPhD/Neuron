"""
Agent Voting Module for Neuron Architecture

Implements voting and consensus mechanisms for multi-agent
decision making and conflict resolution.

"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable
from collections import Counter, defaultdict
import numpy as np

logger = logging.getLogger(__name__)

class AgentVoting:
    """
    Provides mechanisms for agents to vote on decisions
    and reach consensus when there are conflicting outputs.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the voting system with configuration parameters.
        
        Args:
            config: Configuration for voting algorithms
        """
        self.voting_method = config.get("voting_method", "weighted_average")
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.min_voters = config.get("min_voters", 2)
        self.quorum_ratio = config.get("quorum_ratio", 0.5)  # Minimum fraction of agents that must vote
        self.tie_break_method = config.get("tie_break_method", "highest_confidence")
        self.rejection_threshold = config.get("rejection_threshold", 0.3)  # Votes below this confidence are rejected
        self.required_margin = config.get("required_margin", 0.05)  # Required margin for categorical decisions
        
        # Specialized voting configuration
        self.borda_decay = config.get("borda_decay", 0.9)  # Decay factor for Borda Count points
        self.allow_abstention = config.get("allow_abstention", True)
        self.abstention_threshold = config.get("abstention_threshold", 0.4)  # Below this, agent abstains
        
        logger.info(f"Initialized AgentVoting with method={self.voting_method}, "
                  f"threshold={self.confidence_threshold}, min_voters={self.min_voters}")
    
    def normalize_vote_type(self, value: Any) -> Tuple[str, Any]:
        """
        Determine the type of vote for appropriate handling.
        
        Args:
            value: The vote value to normalize
            
        Returns:
            vote_type: Type of vote (numeric, categorical, boolean, etc.)
            normalized_value: Normalized vote value
        """
        if value is None:
            return "null", None
            
        if isinstance(value, bool):
            return "boolean", value
            
        if isinstance(value, (int, float)):
            return "numeric", float(value)
            
        if isinstance(value, str):
            # Try to convert to numeric if it looks like a number
            try:
                float_value = float(value)
                return "numeric", float_value
            except ValueError:
                # It's a categorical string
                return "categorical", value
                
        if isinstance(value, list):
            # Check if it's a list of rankings
            if all(isinstance(item, (str, int)) for item in value):
                return "ranking", value
                
            # Otherwise treat as generic value
            return "complex", value
            
        if isinstance(value, dict):
            # Check if it's a probability distribution
            if all(isinstance(k, (str, int)) for k in value.keys()) and \
               all(isinstance(v, (int, float)) for v in value.values()):
                return "distribution", value
                
            # Otherwise treat as generic value
            return "complex", value
            
        # Default for any other types
        return "unknown", value
    
    def collect_votes(self, agent_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Collect votes from multiple agents and normalize their format.
        
        Args:
            agent_outputs: List of outputs from different agents
            
        Returns:
            normalized_votes: Standardized voting information
        """
        votes = []
        vote_types = set()
        
        # Process each agent's output
        for i, output in enumerate(agent_outputs):
            # Extract the agent's vote and confidence
            agent_id = output.get("agent_id", f"agent_{i}")
            value = output.get("value", output.get("result", None))
            confidence = output.get("confidence", 0.5)
            
            # Skip if value is missing
            if value is None:
                logger.warning(f"Agent {agent_id} provided no value to vote on")
                continue
                
            # Skip votes with very low confidence if configured
            if confidence < self.rejection_threshold:
                logger.debug(f"Rejecting vote from {agent_id} due to low confidence: {confidence:.2f}")
                continue
                
            # Normalize the vote type
            vote_type, normalized_value = self.normalize_vote_type(value)
            vote_types.add(vote_type)
            
            # Handle abstention
            if self.allow_abstention and confidence < self.abstention_threshold:
                logger.debug(f"Agent {agent_id} abstaining due to low confidence: {confidence:.2f}")
                continue
                
            # Create standardized vote record
            vote = {
                "agent_id": agent_id,
                "value": normalized_value,
                "confidence": confidence,
                "type": vote_type,
                "original_output": output
            }
            
            votes.append(vote)
        
        # Check for mixed vote types (except numeric and boolean which can be reconciled)
        if len(vote_types) > 1 and not (vote_types == {"numeric", "boolean"} or vote_types == {"boolean", "numeric"}):
            logger.warning(f"Mixed vote types detected: {vote_types}")
        
        # Check if we have enough votes
        if len(votes) < self.min_voters:
            logger.warning(f"Not enough votes: {len(votes)} < {self.min_voters}")
            
        # Determine the dominant vote type
        vote_type_counts = Counter(vote["type"] for vote in votes)
        if not vote_type_counts:
            dominant_type = "unknown"
        else:
            dominant_type = vote_type_counts.most_common(1)[0][0]
            
        return {
            "votes": votes,
            "vote_types": list(vote_types),
            "dominant_type": dominant_type,
            "total_votes": len(votes),
            "original_agents": len(agent_outputs)
        }
    
    def resolve_consensus(self, votes: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Apply the selected voting method to resolve consensus
        among agent votes.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Consensus result
            confidence: Confidence in the consensus
        """
        # Check if we have enough votes
        if votes["total_votes"] < self.min_voters:
            logger.warning(f"Not enough votes to resolve consensus: {votes['total_votes']} < {self.min_voters}")
            if votes["total_votes"] == 0:
                return None, 0.0
            elif votes["total_votes"] == 1:
                # With only one vote, just return it
                vote = votes["votes"][0]
                return vote["value"], vote["confidence"]
        
        # Check quorum requirement
        if votes["total_votes"] < math.ceil(votes["original_agents"] * self.quorum_ratio):
            logger.warning(f"Quorum not reached: {votes['total_votes']} < "
                         f"{math.ceil(votes['original_agents'] * self.quorum_ratio)}")
            
        # Select voting method based on vote type and configured method
        dominant_type = votes["dominant_type"]
        
        if dominant_type == "boolean":
            return self._boolean_vote(votes)
            
        elif dominant_type == "numeric":
            if self.voting_method == "weighted_average":
                return self._weighted_average_vote(votes)
            elif self.voting_method == "median":
                return self._median_vote(votes)
            else:
                return self._weighted_average_vote(votes)
                
        elif dominant_type == "categorical":
            if self.voting_method == "majority":
                return self._majority_vote(votes)
            elif self.voting_method == "borda_count":
                return self._borda_count(votes)
            else:
                return self._majority_vote(votes)
                
        elif dominant_type == "ranking":
            return self._rank_aggregation(votes)
            
        elif dominant_type == "distribution":
            return self._distribution_merge(votes)
            
        else:
            # Default to simple majority for unknown types
            logger.warning(f"Using majority vote for unknown vote type: {dominant_type}")
            return self._majority_vote(votes)
    
    def _weighted_average_vote(self, votes: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Implement weighted average voting based on agent confidence.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Weighted average result
            confidence: Aggregate confidence
        """
        vote_list = votes["votes"]
        
        # Extract numeric values and weights
        values = []
        weights = []
        
        for vote in vote_list:
            value = vote["value"]
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
                
            values.append(float(value))
            weights.append(vote["confidence"])
        
        # Normalize weights
        if sum(weights) > 0:
            weights = [w / sum(weights) for w in weights]
        else:
            weights = [1.0 / len(weights)] * len(weights)
        
        # Calculate weighted average
        if not values:
            return None, 0.0
            
        weighted_avg = sum(v * w for v, w in zip(values, weights))
        
        # Calculate aggregate confidence based on:
        # 1. How many agents voted (more is better)
        # 2. Average confidence of the agents
        # 3. Agreement between agents (lower variance is better)
        
        # Factor 1: Number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Factor 2: Average confidence
        avg_confidence = sum(vote["confidence"] for vote in vote_list) / len(vote_list)
        
        # Factor 3: Agreement (inverse of normalized variance)
        if len(values) > 1:
            variance = np.var(values)
            # Normalize variance by the range of values
            value_range = max(values) - min(values)
            if value_range > 0:
                normalized_variance = min(1.0, variance / (value_range ** 2))
            else:
                normalized_variance = 0.0
            
            agreement_factor = 1.0 - normalized_variance
        else:
            agreement_factor = 1.0
        
        # Combine factors
        aggregate_confidence = (agent_count_factor * 0.3 + 
                              avg_confidence * 0.4 + 
                              agreement_factor * 0.3)
        
        logger.debug(f"Weighted average: {weighted_avg:.4f}, confidence: {aggregate_confidence:.3f}")
        
        return weighted_avg, aggregate_confidence
    
    def _median_vote(self, votes: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Implement median voting for numeric values, which is robust to outliers.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Median result
            confidence: Aggregate confidence
        """
        vote_list = votes["votes"]
        
        # Extract numeric values and confidences
        values = []
        confidences = []
        
        for vote in vote_list:
            value = vote["value"]
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
                
            values.append(float(value))
            confidences.append(vote["confidence"])
        
        if not values:
            return None, 0.0
            
        # Calculate median
        median_value = np.median(values)
        
        # Calculate aggregate confidence:
        # 1. Higher for more agents
        # 2. Higher for higher individual confidences
        # 3. Higher for lower dispersion around the median
        
        # Factor 1: Number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Factor 2: Average confidence
        avg_confidence = sum(confidences) / len(confidences)
        
        # Factor 3: Agreement (inverse of median absolute deviation)
        mad = np.median([abs(v - median_value) for v in values])
        value_range = max(values) - min(values)
        if value_range > 0:
            normalized_mad = min(1.0, mad / value_range)
        else:
            normalized_mad = 0.0
            
        agreement_factor = 1.0 - normalized_mad
        
        # Combine factors
        aggregate_confidence = (agent_count_factor * 0.3 + 
                              avg_confidence * 0.4 + 
                              agreement_factor * 0.3)
        
        logger.debug(f"Median vote: {median_value:.4f}, confidence: {aggregate_confidence:.3f}")
        
        return median_value, aggregate_confidence
    
    def _majority_vote(self, votes: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Implement majority voting for categorical decisions.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Majority decision
            confidence: Proportion of agreeing votes
        """
        vote_list = votes["votes"]
        
        if not vote_list:
            return None, 0.0
            
        # Count occurrences of each value
        value_counts = defaultdict(float)
        
        for vote in vote_list:
            value = vote["value"]
            confidence = vote["confidence"]
            value_counts[value] += confidence
        
        # Find the value with the highest weighted count
        if not value_counts:
            return None, 0.0
            
        sorted_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
        top_value, top_count = sorted_counts[0]
        
        # Calculate confidence based on:
        # 1. Margin between top and second choice
        # 2. Proportion of total votes for the winner
        # 3. Number of agents voting
        
        # Check if there's a clear winner
        margin = 0.0
        if len(sorted_counts) > 1:
            second_value, second_count = sorted_counts[1]
            margin = (top_count - second_count) / (top_count + second_count)
        else:
            margin = 1.0
            
        # Calculate proportion of votes for the winner
        total_votes = sum(value_counts.values())
        proportion = top_count / total_votes if total_votes > 0 else 0.0
        
        # Factor for number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Tie detection
        if margin < self.required_margin:
            logger.debug(f"Potential tie detected: margin {margin:.3f} < {self.required_margin}")
            
            # Apply tie-breaking method
            if self.tie_break_method == "highest_confidence":
                # Find the value with the highest individual confidence
                max_confidence = 0.0
                tie_breaker_value = top_value
                
                for vote in vote_list:
                    if vote["confidence"] > max_confidence:
                        max_confidence = vote["confidence"]
                        tie_breaker_value = vote["value"]
                        
                logger.debug(f"Tie broken by highest confidence: {tie_breaker_value}")
                top_value = tie_breaker_value
                
            # Penalize confidence for ties
            margin *= 0.5
        
        # Combine factors for final confidence
        aggregate_confidence = (margin * 0.4 + proportion * 0.4 + agent_count_factor * 0.2)
        
        logger.debug(f"Majority vote: {top_value}, confidence: {aggregate_confidence:.3f}")
        
        return top_value, aggregate_confidence
    
    def _boolean_vote(self, votes: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Special case of majority voting optimized for boolean decisions.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Boolean decision
            confidence: Confidence in the decision
        """
        vote_list = votes["votes"]
        
        if not vote_list:
            return False, 0.0
            
        # Count weighted votes for True and False
        true_votes = 0.0
        false_votes = 0.0
        
        for vote in vote_list:
            value = vote["value"]
            confidence = vote["confidence"]
            
            if value:
                true_votes += confidence
            else:
                false_votes += confidence
        
        # Determine winner
        total_votes = true_votes + false_votes
        if total_votes == 0:
            return False, 0.0
            
        result = true_votes > false_votes
        winning_votes = true_votes if result else false_votes
        
        # Calculate margin
        margin = abs(true_votes - false_votes) / total_votes
        
        # Calculate proportion
        proportion = winning_votes / total_votes
        
        # Factor for number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Combine factors for final confidence
        aggregate_confidence = (margin * 0.4 + proportion * 0.4 + agent_count_factor * 0.2)
        
        logger.debug(f"Boolean vote: {result}, confidence: {aggregate_confidence:.3f} "
                   f"(T:{true_votes:.1f}/F:{false_votes:.1f})")
        
        return result, aggregate_confidence
    
    def _borda_count(self, votes: Dict[str, Any]) -> Tuple[Any, float]:
        """
        Implement Borda count voting for ranked preferences.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Winning option
            confidence: Confidence in the result
        """
        vote_list = votes["votes"]
        
        if not vote_list:
            return None, 0.0
            
        # First, collect all unique options
        all_options = set()
        for vote in vote_list:
            value = vote["value"]
            if isinstance(value, list):
                all_options.update(value)
            else:
                all_options.add(value)
        
        all_options = list(all_options)
        
        # Initialize Borda scores
        borda_scores = {option: 0.0 for option in all_options}
        
        # Calculate Borda scores
        for vote in vote_list:
            value = vote["value"]
            confidence = vote["confidence"]
            
            # Convert single value to list if needed
            if not isinstance(value, list):
                rankings = [value]
            else:
                rankings = value
                
            # Award points based on position (higher ranks get more points)
            for i, option in enumerate(rankings):
                # Apply exponential decay to points based on rank
                points = confidence * (self.borda_decay ** i)
                borda_scores[option] += points
        
        # Find the winner
        if not borda_scores:
            return None, 0.0
            
        sorted_scores = sorted(borda_scores.items(), key=lambda x: x[1], reverse=True)
        winner, top_score = sorted_scores[0]
        
        # Calculate confidence
        total_score = sum(borda_scores.values())
        
        if total_score == 0:
            return winner, 0.0
            
        # Calculate margin
        margin = 0.0
        if len(sorted_scores) > 1:
            second_option, second_score = sorted_scores[1]
            margin = (top_score - second_score) / top_score
        else:
            margin = 1.0
            
        # Calculate proportion of total score
        proportion = top_score / total_score
        
        # Factor for number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Combine factors for final confidence
        aggregate_confidence = (margin * 0.4 + proportion * 0.4 + agent_count_factor * 0.2)
        
        logger.debug(f"Borda count winner: {winner}, confidence: {aggregate_confidence:.3f}")
        
        return winner, aggregate_confidence
    
    def _rank_aggregation(self, votes: Dict[str, Any]) -> Tuple[List[Any], float]:
        """
        Aggregate multiple ranked lists into a single consensus ranking.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Aggregated ranking list
            confidence: Confidence in the ranking
        """
        vote_list = votes["votes"]
        
        if not vote_list:
            return [], 0.0
            
        # First, collect all unique items that appear in any ranking
        all_items = set()
        for vote in vote_list:
            value = vote["value"]
            if isinstance(value, list):
                all_items.update(value)
        
        all_items = list(all_items)
        
        # Initialize item scores (lower is better)
        item_scores = {item: 0.0 for item in all_items}
        item_appearances = {item: 0 for item in all_items}
        
        # Calculate scores based on positions in each ranking
        for vote in vote_list:
            value = vote["value"]
            confidence = vote["confidence"]
            
            if not isinstance(value, list):
                continue
                
            for pos, item in enumerate(value):
                # Items not in a ranking are considered to be at the end
                item_scores[item] += pos * confidence
                item_appearances[item] += 1
        
        # Calculate average position for each item, handling missing items
        for item in all_items:
            if item_appearances[item] > 0:
                item_scores[item] /= item_appearances[item]
            else:
                # Items that never appear get a penalized score
                item_scores[item] = len(all_items)
        
        # Sort items by average position (lower is better)
        sorted_items = sorted(all_items, key=lambda x: item_scores[x])
        
        # Calculate confidence based on:
        # 1. Agreement between rankings (lower variance is better)
        # 2. Average agent confidence
        # 3. Number of agents
        
        # Factor 1: Agreement between rankings
        # Calculate average Kendall tau distance between pairs of rankings
        kendall_distances = []
        
        for i, vote1 in enumerate(vote_list):
            value1 = vote1["value"]
            if not isinstance(value1, list):
                continue
                
            for vote2 in vote_list[i+1:]:
                value2 = vote2["value"]
                if not isinstance(value2, list):
                    continue
                    
                # Calculate Kendall tau distance
                distance = self._kendall_tau_distance(value1, value2)
                max_possible = (len(value1) * (len(value1) - 1)) / 2
                
                if max_possible > 0:
                    normalized_distance = distance / max_possible
                    kendall_distances.append(normalized_distance)
        
        if kendall_distances:
            avg_kendall_distance = sum(kendall_distances) / len(kendall_distances)
            agreement_factor = 1.0 - avg_kendall_distance
        else:
            agreement_factor = 0.5  # Neutral value for single ranking
        
        # Factor 2: Average confidence
        avg_confidence = sum(vote["confidence"] for vote in vote_list) / len(vote_list) if vote_list else 0.0
        
        # Factor 3: Number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Combine factors for final confidence
        aggregate_confidence = (agreement_factor * 0.4 + 
                              avg_confidence * 0.4 + 
                              agent_count_factor * 0.2)
        
        logger.debug(f"Rank aggregation result with {len(sorted_items)} items, "
                   f"confidence: {aggregate_confidence:.3f}")
        
        return sorted_items, aggregate_confidence
    
    def _kendall_tau_distance(self, ranking1: List[Any], ranking2: List[Any]) -> int:
        """
        Calculate Kendall tau distance between two rankings.
        
        Args:
            ranking1: First ranking list
            ranking2: Second ranking list
            
        Returns:
            distance: Kendall tau distance
        """
        # Create position maps for both rankings
        pos1 = {item: pos for pos, item in enumerate(ranking1)}
        pos2 = {item: pos for pos, item in enumerate(ranking2)}
        
        # Find common items
        common_items = set(pos1.keys()) & set(pos2.keys())
        common_items = list(common_items)
        
        # Count inversions
        inversions = 0
        for i in range(len(common_items)):
            for j in range(i + 1, len(common_items)):
                item_i = common_items[i]
                item_j = common_items[j]
                
                # Check if the relative order is different
                if (pos1[item_i] < pos1[item_j] and pos2[item_i] > pos2[item_j]) or \
                   (pos1[item_i] > pos1[item_j] and pos2[item_i] < pos2[item_j]):
                    inversions += 1
        
        return inversions
    
    def _distribution_merge(self, votes: Dict[str, Any]) -> Tuple[Dict[Any, float], float]:
        """
        Merge probability distributions from multiple agents.
        
        Args:
            votes: Collection of votes from agents
            
        Returns:
            result: Merged probability distribution
            confidence: Confidence in the merged distribution
        """
        vote_list = votes["votes"]
        
        if not vote_list:
            return {}, 0.0
            
        # Collect all possible categories
        all_categories = set()
        for vote in vote_list:
            value = vote["value"]
            if isinstance(value, dict):
                all_categories.update(value.keys())
        
        # Initialize merged distribution
        merged_distribution = {category: 0.0 for category in all_categories}
        
        # Merge distributions with confidence weighting
        total_weight = 0.0
        for vote in vote_list:
            value = vote["value"]
            confidence = vote["confidence"]
            
            if not isinstance(value, dict):
                continue
                
            # Normalize the distribution if needed
            dist_sum = sum(value.values())
            
            if dist_sum <= 0:
                continue
                
            normalized_dist = {k: v / dist_sum for k, v in value.items()}
            
            # Add to merged distribution with confidence weight
            for category, prob in normalized_dist.items():
                merged_distribution[category] += prob * confidence
                
            total_weight += confidence
        
        # Normalize the merged distribution
        if total_weight > 0:
            merged_distribution = {k: v / total_weight for k, v in merged_distribution.items()}
        
        # Calculate entropy of the distribution to assess confidence
        # Lower entropy means more confidence in the distribution
        entropy = 0.0
        for prob in merged_distribution.values():
            if prob > 0:
                entropy -= prob * math.log(prob)
                
        # Normalize entropy to [0, 1]
        max_entropy = math.log(len(merged_distribution)) if merged_distribution else 0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        
        # Convert to confidence (1 - normalized entropy)
        distribution_confidence = 1.0 - normalized_entropy
        
        # Factor for number of agents
        agent_count_factor = min(1.0, len(vote_list) / self.min_voters)
        
        # Average agent confidence
        avg_confidence = sum(vote["confidence"] for vote in vote_list) / len(vote_list) if vote_list else 0.0
        
        # Combine factors for final confidence
        aggregate_confidence = (distribution_confidence * 0.5 + 
                              avg_confidence * 0.3 + 
                              agent_count_factor * 0.2)
        
        logger.debug(f"Distribution merge with {len(merged_distribution)} categories, "
                   f"confidence: {aggregate_confidence:.3f}")
        
        return merged_distribution, aggregate_confidence

# Agent Voting Summary
# -------------------
# The AgentVoting module provides mechanisms for aggregating outputs from multiple
# agents to reach consensus decisions, especially when agents disagree.
#
# Key features:
#
# 1. Flexible Vote Handling:
#    - Normalizes different output formats (numeric, boolean, categorical, rankings)
#    - Handles mixed vote types appropriately
#    - Provides configurable rejection and abstention thresholds
#
# 2. Multiple Voting Methods:
#    - Weighted average for numeric values
#    - Median voting for robust numeric consensus
#    - Majority voting for categorical decisions
#    - Borda count for preference aggregation
#    - Rank aggregation for merged rankings
#    - Distribution merging for probability distributions
#
# 3. Intelligent Confidence Calculation:
#    - Factors in number of agents, individual confidences, and agreement levels
#    - Detects and handles ties with configurable tie-breaking strategies
#    - Provides quorum requirements to ensure sufficient participation
#
# 4. Consensus Quality Assessment:
#    - Analyzes the margin between top options
#    - Measures agreement between agents (variance, Kendall tau distance)
#    - Evaluates entropy of merged distributions
#
# 5. Customization Options:
#    - Configurable thresholds and voting methods
#    - Adjustable weights for different confidence factors
#    - Support for agent abstention based on confidence
#
# This module enhances multi-agent collaboration by providing principled ways to resolve
# conflicts and aggregate diverse outputs into coherent decisions with associated
# confidence scores.
