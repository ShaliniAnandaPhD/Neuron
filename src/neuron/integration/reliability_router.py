"""
Reliability Router Module for Neuron Architecture

Tracks agent performance and reliability to enable trust-based
routing of tasks to the most appropriate agents.

"""

import time
import logging
import math
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

class ReliabilityRouter:
    """
    Routes tasks based on agent historical performance and 
    reliability metrics, enabling dynamic trust-based routing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the reliability router with configuration parameters.
        
        Args:
            config: Configuration for reliability tracking and routing
        """
        # Configuration parameters
        self.decay_factor = config.get("decay_factor", 0.95)  # How quickly reliability decays
        self.success_weight = config.get("success_weight", 0.6)  # Weight of success in reliability
        self.confidence_weight = config.get("confidence_weight", 0.3)  # Weight of confidence in reliability
        self.speed_weight = config.get("speed_weight", 0.1)  # Weight of speed in reliability
        self.min_data_points = config.get("min_data_points", 5)  # Minimum observations for stable reliability
        self.default_reliability = config.get("default_reliability", 0.5)  # Default reliability for new agents
        self.reliability_memory = config.get("reliability_memory", 100)  # How many recent actions to remember
        self.window_size = config.get("window_size", 30 * 86400)  # Time window for reliability calculation (30 days)
        self.min_reliability_diff = config.get("min_reliability_diff", 0.1)  # Minimum reliability difference to suggest change
        
        # Internal state
        self.performance_history: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        self.reliability_cache: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.last_cache_update = 0.0
        self.cache_validity = config.get("cache_validity", 3600)  # Cache valid for 1 hour by default
        
        logger.info(f"Initialized ReliabilityRouter with decay_factor={self.decay_factor}, "
                  f"window_size={self.window_size/86400:.1f} days")
    
    def update_reliability(self, source_id: str, target_id: str, 
                         success: bool, confidence: float,
                         latency: Optional[float] = None) -> None:
        """
        Update reliability metrics based on agent performance.
        
        Args:
            source_id: ID of the source component
            target_id: ID of the target component
            success: Whether the interaction was successful
            confidence: Confidence level of the interaction
            latency: Optional latency measurement
        """
        timestamp = time.time()
        
        # Create performance record
        record = {
            "timestamp": timestamp,
            "success": success,
            "confidence": confidence,
            "latency": latency
        }
        
        # Add to performance history
        self.performance_history[source_id][target_id].append(record)
        
        # Trim history if needed
        if len(self.performance_history[source_id][target_id]) > self.reliability_memory:
            self.performance_history[source_id][target_id] = \
                self.performance_history[source_id][target_id][-self.reliability_memory:]
        
        # Invalidate cache
        if source_id in self.reliability_cache and target_id in self.reliability_cache[source_id]:
            del self.reliability_cache[source_id][target_id]
            
        logger.debug(f"Updated reliability for {source_id} → {target_id}: success={success}, "
                   f"confidence={confidence:.2f}" + 
                   (f", latency={latency:.2f}s" if latency is not None else ""))
    
    def get_reliability(self, source_id: str, target_id: str) -> float:
        """
        Get the reliability score for a source-target pair.
        
        Args:
            source_id: ID of the source component
            target_id: ID of the target component
            
        Returns:
            reliability: Calculated reliability score (0.0 to 1.0)
        """
        # Check cache
        if (source_id in self.reliability_cache and 
            target_id in self.reliability_cache[source_id] and
            time.time() - self.last_cache_update < self.cache_validity):
            return self.reliability_cache[source_id][target_id]
        
        # Get performance history
        history = self.performance_history.get(source_id, {}).get(target_id, [])
        
        # If no history, return default reliability
        if not history:
            return self.default_reliability
        
        # Filter by time window
        current_time = time.time()
        window_start = current_time - self.window_size
        recent_history = [record for record in history if record["timestamp"] >= window_start]
        
        # If not enough data points in window, include older data with decay
        if len(recent_history) < self.min_data_points and len(history) >= self.min_data_points:
            # Sort by timestamp (newest first)
            sorted_history = sorted(history, key=lambda x: x["timestamp"], reverse=True)
            
            # Add older entries with decay until we reach min_data_points
            while len(recent_history) < self.min_data_points and len(recent_history) < len(sorted_history):
                idx = len(recent_history)
                record = sorted_history[idx].copy()
                
                # Apply time decay to older records
                age = (current_time - record["timestamp"]) / self.window_size
                time_decay = math.pow(self.decay_factor, age)
                
                # Apply decay to success and confidence
                record["success"] = record["success"] and (time_decay >= 0.5)  # Binary decay for success
                record["confidence"] *= time_decay  # Linear decay for confidence
                
                recent_history.append(record)
        
        # If still not enough data, return default with a slight bias from available data
        if len(recent_history) < self.min_data_points:
            # Calculate bias from available data
            if recent_history:
                success_rate = sum(1 for r in recent_history if r["success"]) / len(recent_history)
                avg_confidence = sum(r["confidence"] for r in recent_history) / len(recent_history)
                
                # Slight adjustment to default based on limited data
                bias = (success_rate * 0.6 + avg_confidence * 0.4 - 0.5) * 0.2
                return max(0.0, min(1.0, self.default_reliability + bias))
            else:
                return self.default_reliability
        
        # Calculate success rate
        success_rate = sum(1 for r in recent_history if r["success"]) / len(recent_history)
        
        # Calculate average confidence
        avg_confidence = sum(r["confidence"] for r in recent_history) / len(recent_history)
        
        # Calculate speed factor if latency data available
        speed_factor = 0.5  # Default neutral value
        latencies = [r["latency"] for r in recent_history if r.get("latency") is not None]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            # Convert average latency to a 0-1 score (lower is better)
            # Using a sigmoid function centered at 1.0 second
            speed_factor = 1.0 / (1.0 + math.exp((avg_latency - 1.0) * 3))
        
        # Combine factors with weights
        reliability = (
            success_rate * self.success_weight +
            avg_confidence * self.confidence_weight +
            speed_factor * self.speed_weight
        ) / (self.success_weight + self.confidence_weight + self.speed_weight)
        
        # Ensure bounds
        reliability = max(0.0, min(1.0, reliability))
        
        # Cache the result
        self.reliability_cache[source_id][target_id] = reliability
        self.last_cache_update = time.time()
        
        logger.debug(f"Calculated reliability for {source_id} → {target_id}: {reliability:.3f} "
                   f"(success={success_rate:.2f}, confidence={avg_confidence:.2f}, speed={speed_factor:.2f})")
        
        return reliability
    
    def get_best_target(self, source_id: str, candidate_targets: List[str]) -> Tuple[str, float]:
        """
        Get the most reliable target from a list of candidates.
        
        Args:
            source_id: ID of the source component
            candidate_targets: List of potential target components
            
        Returns:
            target_id: ID of the most reliable target
            reliability: Reliability score of the selected target
        """
        if not candidate_targets:
            logger.warning(f"No candidate targets provided for source {source_id}")
            return "", 0.0
        
        # Get reliability for each candidate
        reliabilities = [(target, self.get_reliability(source_id, target)) 
                        for target in candidate_targets]
        
        # Sort by reliability (descending)
        reliabilities.sort(key=lambda x: x[1], reverse=True)
        
        best_target, best_reliability = reliabilities[0]
        
        logger.debug(f"Best target for {source_id}: {best_target} (reliability={best_reliability:.3f})")
        
        return best_target, best_reliability
    
    def get_alternatives(self, source_id: str, current_target: str,
                        candidate_targets: Optional[List[str]] = None) -> List[Tuple[str, float]]:
        """
        Get alternative targets that may be more reliable than the current one.
        
        Args:
            source_id: ID of the source component
            current_target: Current target component
            candidate_targets: Optional list of alternative targets to consider
            
        Returns:
            alternatives: List of (target_id, reliability) tuples with higher reliability
        """
        # Get current reliability
        current_reliability = self.get_reliability(source_id, current_target)
        
        # If no candidates provided, use all known targets for this source
        if candidate_targets is None:
            candidate_targets = list(self.performance_history.get(source_id, {}).keys())
            
        # Remove current target from candidates
        if current_target in candidate_targets:
            candidate_targets.remove(current_target)
            
        if not candidate_targets:
            return []
            
        # Get reliability for each candidate
        reliabilities = [(target, self.get_reliability(source_id, target)) 
                        for target in candidate_targets]
        
        # Filter for targets with significantly higher reliability
        better_alternatives = [(target, rel) for target, rel in reliabilities 
                              if rel > current_reliability + self.min_reliability_diff]
        
        # Sort by reliability (descending)
        better_alternatives.sort(key=lambda x: x[1], reverse=True)
        
        if better_alternatives:
            logger.debug(f"Found {len(better_alternatives)} better alternatives for "
                       f"{source_id} → {current_target} (current={current_reliability:.3f})")
            
        return better_alternatives
    
    def get_reliability_matrix(self, sources: Optional[List[str]] = None,
                              targets: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """
        Get a matrix of reliability scores for multiple sources and targets.
        
        Args:
            sources: Optional list of source components to include
            targets: Optional list of target components to include
            
        Returns:
            matrix: Nested dictionary of reliability scores
        """
        # If no sources provided, use all known sources
        if sources is None:
            sources = list(self.performance_history.keys())
            
        # If no targets provided, collect all known targets
        if targets is None:
            targets = set()
            for source_targets in self.performance_history.values():
                targets.update(source_targets.keys())
            targets = list(targets)
            
        # Build matrix
        matrix = {}
        for source in sources:
            matrix[source] = {}
            for target in targets:
                matrix[source][target] = self.get_reliability(source, source_id=source, target_id=target)
                
        return matrix
    
    def get_reliability_stats(self, source_id: Optional[str] = None, 
                            target_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about reliability calculations.
        
        Args:
            source_id: Optional source to filter by
            target_id: Optional target to filter by
            
        Returns:
            stats: Dictionary of reliability statistics
        """
        # Collect all records matching filters
        records = []
        
        # Filter by source and target
        sources = [source_id] if source_id else list(self.performance_history.keys())
        
        for src in sources:
            targets = [target_id] if target_id else list(self.performance_history.get(src, {}).keys())
            for tgt in targets:
                records.extend(self.performance_history.get(src, {}).get(tgt, []))
        
        # If no records, return empty stats
        if not records:
            return {
                "total_records": 0,
                "sources": 0,
                "targets": 0,
                "avg_success_rate": None,
                "avg_confidence": None,
                "avg_latency": None
            }
        
        # Basic stats
        success_count = sum(1 for r in records if r.get("success", False))
        confidence_sum = sum(r.get("confidence", 0.0) for r in records)
        
        # Latency stats
        latencies = [r.get("latency") for r in records if r.get("latency") is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        
        # Source and target counts
        source_count = len(self.performance_history) if not source_id else 1
        target_count = 0
        for src in sources:
            target_count += len(self.performance_history.get(src, {}))
        if target_id:
            target_count = min(target_count, len(sources))
        
        return {
            "total_records": len(records),
            "sources": source_count,
            "targets": target_count,
            "avg_success_rate": success_count / len(records),
            "avg_confidence": confidence_sum / len(records),
            "avg_latency": avg_latency
        }
    
    def clear_history(self, source_id: Optional[str] = None, 
                     target_id: Optional[str] = None) -> int:
        """
        Clear performance history for specific source/target or all.
        
        Args:
            source_id: Optional source to clear
            target_id: Optional target to clear
            
        Returns:
            cleared_count: Number of records cleared
        """
        total_cleared = 0
        
        # Clear specific source-target pair
        if source_id and target_id:
            if source_id in self.performance_history and target_id in self.performance_history[source_id]:
                total_cleared = len(self.performance_history[source_id][target_id])
                self.performance_history[source_id][target_id] = []
                
                if source_id in self.reliability_cache and target_id in self.reliability_cache[source_id]:
                    del self.reliability_cache[source_id][target_id]
                    
        # Clear all targets for a source
        elif source_id:
            for target, history in self.performance_history.get(source_id, {}).items():
                total_cleared += len(history)
                
            self.performance_history[source_id] = defaultdict(list)
            self.reliability_cache[source_id] = {}
                
        # Clear all history
        else:
            for source, targets in self.performance_history.items():
                for target, history in targets.items():
                    total_cleared += len(history)
                    
            self.performance_history = defaultdict(lambda: defaultdict(list))
            self.reliability_cache = defaultdict(dict)
            
        logger.info(f"Cleared {total_cleared} reliability history records")
        return total_cleared
    
    def prune_old_records(self, max_age: Optional[float] = None) -> int:
        """
        Remove records older than the specified age.
        
        Args:
            max_age: Maximum age in seconds (default: 2x window_size)
            
        Returns:
            pruned_count: Number of records pruned
        """
        if max_age is None:
            max_age = self.window_size * 2
            
        cutoff_time = time.time() - max_age
        total_pruned = 0
        
        for source, targets in self.performance_history.items():
            for target in list(targets.keys()):
                history = targets[target]
                new_history = [r for r in history if r["timestamp"] >= cutoff_time]
                
                pruned = len(history) - len(new_history)
                if pruned > 0:
                    total_pruned += pruned
                    self.performance_history[source][target] = new_history
                    
                    # Invalidate cache
                    if source in self.reliability_cache and target in self.reliability_cache[source]:
                        del self.reliability_cache[source][target]
        
        if total_pruned > 0:
            logger.info(f"Pruned {total_pruned} old reliability records (older than {max_age/86400:.1f} days)")
            
        return total_pruned

# Reliability Router Summary
# -------------------------
# The ReliabilityRouter module provides a system for tracking agent performance,
# calculating reliability scores, and making routing decisions based on historical
# performance metrics.
#
# Key features:
#
# 1. Performance Tracking:
#    - Records success/failure of agent interactions
#    - Tracks confidence levels and latency
#    - Maintains historical performance data with time decay
#
# 2. Reliability Calculation:
#    - Computes weighted reliability scores based on success rate, confidence, and speed
#    - Applies temporal decay to prioritize recent performance
#    - Handles cold-start problems with default reliability values
#
# 3. Routing Decisions:
#    - Identifies the most reliable agent for a given task
#    - Suggests alternative routing paths with higher reliability
#    - Requires minimum reliability difference for route changes
#
# 4. Performance Analysis:
#    - Generates reliability matrices across components
#    - Provides statistical analysis of performance data
#    - Supports filtering by source and target components
#
# 5. Resource Management:
#    - Caches reliability calculations for efficiency
#    - Prunes old performance records to save memory
#    - Configurable time windows and decay parameters
#
# This module enables adaptive, trust-based routing within the Neuron architecture,
# allowing the system to learn from experience and route tasks to the most reliable
# agents based on their historical performance.
