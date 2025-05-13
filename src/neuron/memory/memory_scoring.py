"""
Memory Scoring Module for Neuron Architecture

Implements confidence-weighted memory retrieval, contextual
scoping, and temporal decay functions for optimizing memory access.

"""

import time
import math
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Set, Callable
import numpy as np

logger = logging.getLogger(__name__)

class MemoryScoring:
    """
    Handles the scoring, ranking, and selection of memories
    based on relevance, confidence, and recency.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the memory scoring system with configuration parameters.
        
        Args:
            config: Configuration for memory scoring algorithms
        """
        # Decay parameters
        self.decay_rate = config.get("decay_rate", 0.05)
        self.min_retention = config.get("min_retention", 0.2)
        
        # Scoring weights
        self.confidence_weight = config.get("confidence_weight", 0.3)
        self.context_weight = config.get("context_weight", 0.4)
        self.recency_weight = config.get("recency_weight", 0.2)
        self.frequency_weight = config.get("frequency_weight", 0.1)
        
        # Thresholds
        self.confidence_threshold = config.get("confidence_threshold", 0.7)
        self.min_score_threshold = config.get("min_score_threshold", 0.4)
        self.high_relevance_threshold = config.get("high_relevance_threshold", 0.8)
        
        # Context similarity methods
        self.similarity_method = config.get("similarity_method", "cosine")
        self.embedding_dim = config.get("embedding_dim", 768)
        
        # Memory access tracking
        self.access_history: Dict[str, List[float]] = {}
        logger.info(f"Initialized MemoryScoring with decay_rate={self.decay_rate}, similarity_method={self.similarity_method}")
    
    def score_memory(self, memory_item: Dict[str, Any], 
                    query_context: Dict[str, Any]) -> float:
        """
        Score a memory item based on its relevance to the current context,
        confidence, and recency.
        
        Args:
            memory_item: Memory item to score
            query_context: Current context for relevance calculation
            
        Returns:
            score: Calculated score for the memory item
        """
        # Extract memory attributes
        memory_id = memory_item.get("id", str(id(memory_item)))
        confidence = memory_item.get("confidence", 0.5)
        memory_context = memory_item.get("context", {})
        creation_time = memory_item.get("creation_time", time.time())
        last_access_time = memory_item.get("last_access_time", creation_time)
        
        # Calculate temporal decay factor
        time_elapsed = (time.time() - creation_time) / 86400  # Convert to days
        recency_factor = self._calculate_recency_factor(time_elapsed)
        
        # Calculate frequency factor based on access history
        frequency_factor = self._calculate_frequency_factor(memory_id)
        
        # Calculate contextual relevance
        context_similarity = self._calculate_context_similarity(memory_context, query_context)
        
        # Combine factors into final score with configured weights
        score = (
            (confidence * self.confidence_weight) +
            (context_similarity * self.context_weight) +
            (recency_factor * self.recency_weight) +
            (frequency_factor * self.frequency_weight)
        ) / (self.confidence_weight + self.context_weight + self.recency_weight + self.frequency_weight)
        
        # Record this access
        self._record_memory_access(memory_id)
        
        logger.debug(f"Scored memory {memory_id}: score={score:.3f}, confidence={confidence:.3f}, "
                    f"context_sim={context_similarity:.3f}, recency={recency_factor:.3f}")
        
        return score
    
    def _calculate_recency_factor(self, time_elapsed: float) -> float:
        """
        Calculate a recency factor based on time elapsed since creation.
        Uses exponential decay with configured decay rate.
        
        Args:
            time_elapsed: Time elapsed in days
            
        Returns:
            recency_factor: Recency factor between min_retention and 1.0
        """
        # Exponential decay with floor
        raw_factor = math.exp(-self.decay_rate * time_elapsed)
        
        # Ensure it doesn't decay below minimum retention
        recency_factor = max(raw_factor, self.min_retention)
        
        return recency_factor
    
    def _calculate_frequency_factor(self, memory_id: str) -> float:
        """
        Calculate a frequency factor based on how often this memory
        has been accessed.
        
        Args:
            memory_id: Identifier for the memory
            
        Returns:
            frequency_factor: Factor between 0.0 and 1.0
        """
        if memory_id not in self.access_history:
            return 0.0
        
        # Calculate access frequency based on number of accesses in last 30 days
        accesses = self.access_history[memory_id]
        current_time = time.time()
        recent_accesses = [t for t in accesses if (current_time - t) < 30 * 86400]
        
        # Simple scaling function - can be made more sophisticated
        access_count = len(recent_accesses)
        if access_count == 0:
            return 0.0
        elif access_count == 1:
            return 0.3
        elif access_count == 2:
            return 0.6
        else:
            return min(1.0, 0.7 + (access_count - 3) * 0.1)
    
    def _record_memory_access(self, memory_id: str) -> None:
        """
        Record an access to a memory item for frequency tracking.
        
        Args:
            memory_id: Identifier for the memory
        """
        if memory_id not in self.access_history:
            self.access_history[memory_id] = []
            
        self.access_history[memory_id].append(time.time())
        
        # Limit history size
        max_history_per_memory = 100
        if len(self.access_history[memory_id]) > max_history_per_memory:
            self.access_history[memory_id] = self.access_history[memory_id][-max_history_per_memory:]
    
    def _calculate_context_similarity(self, memory_context: Dict[str, Any],
                                    query_context: Dict[str, Any]) -> float:
        """
        Calculate the similarity between memory context and query context.
        
        Args:
            memory_context: Context stored with the memory
            query_context: Current query context
            
        Returns:
            similarity: Calculated similarity score
        """
        # Handle empty contexts
        if not memory_context or not query_context:
            return 0.0
            
        # If context contains embeddings, use them for similarity
        if "embedding" in memory_context and "embedding" in query_context:
            return self._vector_similarity(
                memory_context["embedding"], 
                query_context["embedding"]
            )
            
        # Otherwise, fall back to attribute-based similarity
        return self._attribute_similarity(memory_context, query_context)
    
    def _vector_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate similarity between two vectors using the configured method.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            similarity: Similarity score between 0.0 and 1.0
        """
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            # Pad the shorter vector with zeros
            if len(vec1) < len(vec2):
                vec1 = vec1 + [0.0] * (len(vec2) - len(vec1))
            else:
                vec2 = vec2 + [0.0] * (len(vec1) - len(vec2))
        
        # Convert to numpy arrays for efficient computation
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        if self.similarity_method == "cosine":
            # Cosine similarity
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return float(np.dot(v1, v2) / (norm1 * norm2))
            
        elif self.similarity_method == "euclidean":
            # Euclidean distance converted to similarity
            dist = np.linalg.norm(v1 - v2)
            # Convert distance to similarity, with a maximum distance threshold
            max_dist = math.sqrt(2)  # Maximum distance for normalized vectors
            similarity = max(0.0, 1.0 - (dist / max_dist))
            return float(similarity)
            
        elif self.similarity_method == "dot":
            # Simple dot product for normalized vectors
            return float(np.dot(v1, v2))
            
        else:
            logger.warning(f"Unknown similarity method: {self.similarity_method}, falling back to cosine")
            # Fall back to cosine similarity
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def _attribute_similarity(self, context1: Dict[str, Any], 
                             context2: Dict[str, Any]) -> float:
        """
        Calculate similarity between contexts based on attribute matches.
        
        Args:
            context1: First context dictionary
            context2: Second context dictionary
            
        Returns:
            similarity: Similarity score between 0.0 and 1.0
        """
        # Get all keys
        all_keys = set(context1.keys()) | set(context2.keys())
        
        if not all_keys:
            return 0.0
            
        # Count matching keys and values
        matching_keys = 0
        matching_values = 0
        
        for key in all_keys:
            if key in context1 and key in context2:
                matching_keys += 1
                if context1[key] == context2[key]:
                    matching_values += 1
        
        # Calculate key similarity and value similarity
        key_similarity = matching_keys / len(all_keys) if all_keys else 0.0
        value_similarity = matching_values / len(all_keys) if all_keys else 0.0
        
        # Combine with more weight on value matches
        return 0.4 * key_similarity + 0.6 * value_similarity
    
    def rank_memories(self, memory_items: List[Dict[str, Any]], 
                     query_context: Dict[str, Any],
                     top_k: Optional[int] = None) -> List[Tuple[Dict[str, Any], float]]:
        """
        Rank a list of memory items by their scores.
        
        Args:
            memory_items: List of memory items to rank
            query_context: Current context for scoring
            top_k: Optional limit on number of results
            
        Returns:
            ranked_memories: List of (memory, score) tuples, sorted by score
        """
        # Score all memories
        scored_memories = [(memory, self.score_memory(memory, query_context)) 
                          for memory in memory_items]
        
        # Filter out memories below threshold
        filtered_memories = [(memory, score) for memory, score in scored_memories 
                            if score >= self.min_score_threshold]
        
        # Sort by score (descending)
        sorted_memories = sorted(filtered_memories, key=lambda x: x[1], reverse=True)
        
        # Limit to top_k if specified
        if top_k is not None and top_k > 0:
            sorted_memories = sorted_memories[:top_k]
            
        return sorted_memories
    
    def filter_by_criteria(self, memory_items: List[Dict[str, Any]], 
                          criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter memory items by specific criteria.
        
        Args:
            memory_items: List of memory items to filter
            criteria: Dictionary of criteria to match
            
        Returns:
            filtered_memories: List of memories that match criteria
        """
        filtered = []
        
        for memory in memory_items:
            matches_all = True
            
            for key, value in criteria.items():
                # Handle special keys with custom logic
                if key == "min_confidence":
                    if memory.get("confidence", 0) < value:
                        matches_all = False
                        break
                elif key == "max_age_days":
                    creation_time = memory.get("creation_time", 0)
                    age_days = (time.time() - creation_time) / 86400
                    if age_days > value:
                        matches_all = False
                        break
                elif key == "context_contains":
                    memory_context = memory.get("context", {})
                    if not all(memory_context.get(k) == v for k, v in value.items()):
                        matches_all = False
                        break
                # Default: direct attribute comparison
                elif memory.get(key) != value:
                    matches_all = False
                    break
                    
            if matches_all:
                filtered.append(memory)
                
        return filtered
    
    def calculate_decay(self, memory_item: Dict[str, Any], 
                       current_time: Optional[float] = None) -> float:
        """
        Calculate the current decay factor for a memory item.
        
        Args:
            memory_item: Memory item to calculate decay for
            current_time: Current time (default: time.time())
            
        Returns:
            decay_factor: Current decay factor (1.0 = no decay, 0.0 = full decay)
        """
        if current_time is None:
            current_time = time.time()
            
        creation_time = memory_item.get("creation_time", current_time)
        time_elapsed = (current_time - creation_time) / 86400  # Convert to days
        
        return self._calculate_recency_factor(time_elapsed)
    
    def should_retain_memory(self, memory_item: Dict[str, Any], 
                            current_time: Optional[float] = None) -> bool:
        """
        Determine if a memory item should be retained or pruned.
        
        Args:
            memory_item: Memory item to evaluate
            current_time: Current time (default: time.time())
            
        Returns:
            retain: Whether the memory should be retained
        """
        # High confidence memories are always retained
        if memory_item.get("confidence", 0) >= self.confidence_threshold:
            return True
            
        # Calculate current decay factor
        decay_factor = self.calculate_decay(memory_item, current_time)
        
        # Check against minimum retention threshold
        retention_threshold = memory_item.get("retention_threshold", self.min_retention)
        
        return decay_factor >= retention_threshold
    
    def update_memory_score(self, memory_item: Dict[str, Any], 
                           new_score: float,
                           update_confidence: bool = False) -> Dict[str, Any]:
        """
        Update a memory item with a new score and optionally adjust confidence.
        
        Args:
            memory_item: Memory item to update
            new_score: New score from recent retrieval
            update_confidence: Whether to update confidence based on score
            
        Returns:
            updated_memory: Updated memory item
        """
        # Create a copy to avoid modifying the original
        updated_memory = memory_item.copy()
        
        # Update score
        updated_memory["last_score"] = new_score
        
        # Record access time
        updated_memory["last_access_time"] = time.time()
        
        # Update access count
        updated_memory["access_count"] = updated_memory.get("access_count", 0) + 1
        
        # Optionally update confidence based on score
        if update_confidence:
            # Slow confidence adjustment (1:5 ratio of new to old)
            old_confidence = updated_memory.get("confidence", 0.5)
            updated_memory["confidence"] = (old_confidence * 5 + new_score) / 6
            
        return updated_memory
    
    def merge_similar_memories(self, memory_items: List[Dict[str, Any]], 
                              similarity_threshold: float = 0.9) -> List[Dict[str, Any]]:
        """
        Merge memories that are highly similar to reduce redundancy.
        
        Args:
            memory_items: List of memory items to process
            similarity_threshold: Threshold for considering memories similar
            
        Returns:
            merged_memories: List with similar memories merged
        """
        if not memory_items:
            return []
            
        # Make a copy to avoid modifying originals
        processed_memories = memory_items.copy()
        
        # Sort by confidence so we merge into higher confidence items
        processed_memories.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        merged_results = []
        skip_indices = set()
        
        for i, memory_i in enumerate(processed_memories):
            if i in skip_indices:
                continue
                
            # This memory becomes the base for potential merges
            merged_memory = memory_i.copy()
            merged_with = []
            
            for j, memory_j in enumerate(processed_memories[i+1:], i+1):
                if j in skip_indices:
                    continue
                    
                # Check if contexts are similar
                similarity = self._calculate_context_similarity(
                    memory_i.get("context", {}),
                    memory_j.get("context", {})
                )
                
                if similarity >= similarity_threshold:
                    # Merge memories
                    merged_memory = self._merge_memory_pair(merged_memory, memory_j)
                    merged_with.append(j)
                    skip_indices.add(j)
            
            # Add metadata about merge if it happened
            if merged_with:
                if "metadata" not in merged_memory:
                    merged_memory["metadata"] = {}
                merged_memory["metadata"]["merged_count"] = len(merged_with) + 1
                merged_memory["metadata"]["merged_at"] = time.time()
                
            merged_results.append(merged_memory)
            
        return merged_results
    
    def _merge_memory_pair(self, primary: Dict[str, Any], 
                          secondary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two memory items together, with primary taking precedence.
        
        Args:
            primary: Primary memory item
            secondary: Secondary memory item to merge in
            
        Returns:
            merged: Merged memory item
        """
        merged = primary.copy()
        
        # Merge metadata
        if "metadata" not in merged:
            merged["metadata"] = {}
            
        if "metadata" in secondary:
            for key, value in secondary["metadata"].items():
                if key not in merged["metadata"]:
                    merged["metadata"][key] = value
        
        # Take higher confidence
        merged["confidence"] = max(
            merged.get("confidence", 0.5),
            secondary.get("confidence", 0.5)
        )
        
        # Take more recent timestamp for last_access_time
        merged["last_access_time"] = max(
            merged.get("last_access_time", 0),
            secondary.get("last_access_time", 0)
        )
        
        # Combine access counts
        merged["access_count"] = (merged.get("access_count", 0) + 
                                 secondary.get("access_count", 0))
        
        # Keep older creation time
        merged["creation_time"] = min(
            merged.get("creation_time", time.time()),
            secondary.get("creation_time", time.time())
        )
        
        # Store original memory IDs if present
        original_ids = []
        if "id" in merged:
            original_ids.append(merged["id"])
        if "id" in secondary:
            original_ids.append(secondary["id"])
            
        if original_ids:
            merged["metadata"]["original_ids"] = original_ids
            
        return merged

# Memory Scoring Summary
# ---------------------
# The MemoryScoring module implements algorithms for ranking, filtering, and
# managing memory items based on their relevance, confidence, recency, and usage patterns.
#
# Key features:
#
# 1. Context-Sensitive Scoring:
#    - Calculates similarity between memory contexts and query contexts
#    - Supports both vector-based and attribute-based similarity metrics
#    - Weights relevance based on configurable parameters
#
# 2. Temporal Dynamics:
#    - Implements exponential decay based on memory age
#    - Tracks access frequency to boost commonly used memories
#    - Balances recency with persistence for important memories
#
# 3. Memory Management:
#    - Ranks memories by relevance for efficient retrieval
#    - Filters memories based on complex criteria
#    - Merges similar memories to reduce redundancy
#    - Provides retention policies for memory pruning
#
# 4. Confidence Integration:
#    - Factors memory confidence into scoring
#    - Updates confidence based on usage patterns
#    - Protects high-confidence memories from decay
#
# 5. Flexible Configuration:
#    - Customizable decay rates and thresholds
#    - Configurable similarity methods
#    - Adjustable weighting between factors
#
# This module enhances memory retrieval quality by prioritizing memories that are
# most relevant to the current context, while efficiently managing memory resources
# through intelligent pruning and merging of similar content.
