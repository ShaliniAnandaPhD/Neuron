
"""
Neuron Framework: Working Memory System 


Working memory implementation for short-term information storage and active processing.
Provides LRU caching, automatic expiration, and priority-based retention.
"""

import time
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import pickle
import os

from neuron.core.base import MemoryInterface

logger = logging.getLogger(__name__)

# =====================================
# Memory Data Structures
# =====================================

@dataclass
class MemoryItem:
    """Individual memory item with metadata"""
    key: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    priority: float = 1.0  # Higher = more important
    ttl: Optional[float] = None  # Time to live in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0
    
    def __post_init__(self):
        """Calculate size after initialization"""
        self.size_bytes = self._calculate_size()
    
    def _calculate_size(self) -> int:
        """Estimate memory size of the item"""
        try:
            return len(pickle.dumps(self.value))
        except Exception:
            # Fallback estimation
            if isinstance(self.value, str):
                return len(self.value.encode('utf-8'))
            elif isinstance(self.value, (int, float)):
                return 8
            elif isinstance(self.value, dict):
                return len(str(self.value)) * 2
            elif isinstance(self.value, list):
                return len(str(self.value)) * 2
            else:
                return 100  # Default estimate
    
    def is_expired(self) -> bool:
        """Check if item has expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def access(self):
        """Mark item as accessed"""
        self.access_count += 1
        self.last_access = time.time()
    
    def get_age(self) -> float:
        """Get age in seconds"""
        return time.time() - self.timestamp
    
    def get_idle_time(self) -> float:
        """Get time since last access"""
        return time.time() - self.last_access
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'key': self.key,
            'value': self.value,
            'timestamp': self.timestamp,
            'access_count': self.access_count,
            'last_access': self.last_access,
            'priority': self.priority,
            'ttl': self.ttl,
            'metadata': self.metadata,
            'size_bytes': self.size_bytes
        }

@dataclass
class MemoryStats:
    """Statistics for memory system"""
    total_items: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    expired_count: int = 0
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hit_count + self.miss_count
        return (self.hit_count / total * 100) if total > 0 else 0.0
    
    def get_average_size(self) -> float:
        """Calculate average item size"""
        return (self.total_size_bytes / self.total_items) if self.total_items > 0 else 0.0

# =====================================
# Working Memory Implementation
# =====================================

class WorkingMemory(MemoryInterface):
    """
    Working memory implementation for short-term information storage
    
    Features:
    - LRU eviction with priority boost
    - Automatic expiration based on TTL
    - Size-based capacity management
    - Access pattern tracking
    - Persistence to disk
    - Thread-safe operations
    """
    
    def __init__(self, 
                 max_items: int = 1000,
                 max_size_bytes: int = 10 * 1024 * 1024,  # 10MB
                 default_ttl: Optional[float] = None,
                 persistence_file: Optional[str] = None,
                 cleanup_interval: float = 60.0):  # 1 minute
        """
        Initialize working memory
        
        Args:
            max_items: Maximum number of items to store
            max_size_bytes: Maximum total size in bytes
            default_ttl: Default time-to-live for items (None = no expiration)
            persistence_file: File to persist memory to disk
            cleanup_interval: How often to run cleanup (seconds)
        """
        self.max_items = max_items
        self.max_size_bytes = max_size_bytes
        self.default_ttl = default_ttl
        self.persistence_file = persistence_file
        self.cleanup_interval = cleanup_interval
        
        # Storage
        self._memory: OrderedDict[str, MemoryItem] = OrderedDict()
        self._lock = threading.RLock()
        
        # Statistics
        self.stats = MemoryStats()
        
        # Cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Load from persistence if available
        if self.persistence_file and os.path.exists(self.persistence_file):
            self._load_from_disk()
        
        logger.info(f"WorkingMemory initialized: max_items={max_items}, max_size={max_size_bytes}")
    
    # =====================================
    # Core Memory Interface
    # =====================================
    
    async def store(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> bool:
        """Store information in working memory"""
        try:
            with self._lock:
                # Create memory item
                item = MemoryItem(
                    key=key,
                    value=value,
                    ttl=metadata.get('ttl', self.default_ttl) if metadata else self.default_ttl,
                    priority=metadata.get('priority', 1.0) if metadata else 1.0,
                    metadata=metadata or {}
                )
                
                # Check if we need to make space
                await self._ensure_capacity(item.size_bytes)
                
                # Store item (move to end for LRU)
                if key in self._memory:
                    # Update existing item
                    old_item = self._memory[key]
                    self.stats.total_size_bytes -= old_item.size_bytes
                else:
                    self.stats.total_items += 1
                
                self._memory[key] = item
                self._memory.move_to_end(key)  # Mark as most recently used
                self.stats.total_size_bytes += item.size_bytes
                
                logger.debug(f"Stored item '{key}' in working memory (size: {item.size_bytes} bytes)")
                return True
                
        except Exception as e:
            logger.error(f"Error storing item '{key}': {e}")
            return False
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve information from working memory"""
        try:
            with self._lock:
                if key not in self._memory:
                    self.stats.miss_count += 1
                    return None
                
                item = self._memory[key]
                
                # Check if expired
                if item.is_expired():
                    await self._remove_item(key)
                    self.stats.miss_count += 1
                    self.stats.expired_count += 1
                    return None
                
                # Mark as accessed and move to end (most recent)
                item.access()
                self._memory.move_to_end(key)
                self.stats.hit_count += 1
                
                logger.debug(f"Retrieved item '{key}' from working memory")
                return item.value
                
        except Exception as e:
            logger.error(f"Error retrieving item '{key}': {e}")
            self.stats.miss_count += 1
            return None
    
    async def search(self, query: Dict[str, Any]) -> List[Any]:
        """Search memory with query"""
        results = []
        
        try:
            with self._lock:
                for key, item in self._memory.items():
                    if item.is_expired():
                        continue
                    
                    # Check if item matches query
                    if self._matches_query(item, query):
                        item.access()
                        results.append({
                            'key': key,
                            'value': item.value,
                            'metadata': item.metadata,
                            'timestamp': item.timestamp,
                            'access_count': item.access_count
                        })
                
                logger.debug(f"Search found {len(results)} items matching query")
                return results
                
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    async def forget(self, key: str) -> bool:
        """Remove information from memory"""
        try:
            with self._lock:
                if key in self._memory:
                    await self._remove_item(key)
                    logger.debug(f"Forgot item '{key}' from working memory")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Error forgetting item '{key}': {e}")
            return False
    
    async def clear(self) -> bool:
        """Clear all memory"""
        try:
            with self._lock:
                self._memory.clear()
                self.stats = MemoryStats()
                logger.info("Working memory cleared")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return False
    
    # =====================================
    # Memory Management
    # =====================================
    
    async def _ensure_capacity(self, new_item_size: int):
        """Ensure there's enough capacity for a new item"""
        # Remove expired items first
        await self._cleanup_expired()
        
        # Check if we need to evict items
        while (len(self._memory) >= self.max_items or 
               self.stats.total_size_bytes + new_item_size > self.max_size_bytes):
            
            if not self._memory:
                break
            
            # Find item to evict (LRU with priority consideration)
            victim_key = self._find_eviction_victim()
            if victim_key:
                await self._remove_item(victim_key)
                self.stats.eviction_count += 1
            else:
                break
    
    def _find_eviction_victim(self) -> Optional[str]:
        """Find the best item to evict (LRU with priority boost)"""
        if not self._memory:
            return None
        
        # Calculate eviction score for each item (lower = more likely to evict)
        candidates = []
        
        for key, item in self._memory.items():
            # Base score is recency (older = higher score)
            recency_score = item.get_idle_time()
            
            # Priority boost (higher priority = lower eviction score)
            priority_factor = 1.0 / max(0.1, item.priority)
            
            # Access frequency factor (more accessed = lower eviction score)
            access_factor = 1.0 / max(1, item.access_count)
            
            # Combined eviction score
            eviction_score = recency_score * priority_factor * access_factor
            
            candidates.append((eviction_score, key))
        
        # Sort by eviction score (highest first = most likely to evict)
        candidates.sort(reverse=True)
        
        return candidates[0][1] if candidates else None
    
    async def _remove_item(self, key: str):
        """Remove an item from memory"""
        if key in self._memory:
            item = self._memory.pop(key)
            self.stats.total_items -= 1
            self.stats.total_size_bytes -= item.size_bytes
    
    async def _cleanup_expired(self):
        """Remove expired items"""
        expired_keys = []
        
        for key, item in self._memory.items():
            if item.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            await self._remove_item(key)
            self.stats.expired_count += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired items")
    
    def _matches_query(self, item: MemoryItem, query: Dict[str, Any]) -> bool:
        """Check if memory item matches search query"""
        for key, expected_value in query.items():
            if key == 'key_pattern':
                if expected_value not in item.key:
                    return False
            elif key == 'metadata_key':
                if expected_value not in item.metadata:
                    return False
            elif key == 'min_priority':
                if item.priority < expected_value:
                    return False
            elif key == 'max_age':
                if item.get_age() > expected_value:
                    return False
            elif key == 'value_type':
                if not isinstance(item.value, expected_value):
                    return False
            elif key in item.metadata:
                if item.metadata[key] != expected_value:
                    return False
        
        return True
    
    # =====================================
    # Persistence
    # =====================================
    
    async def save_to_disk(self) -> bool:
        """Save memory contents to disk"""
        if not self.persistence_file:
            return False
        
        try:
            with self._lock:
                # Convert to serializable format
                data = {
                    'items': [item.to_dict() for item in self._memory.values()],
                    'stats': asdict(self.stats),
                    'timestamp': time.time()
                }
                
                # Write to temporary file first, then rename (atomic operation)
                temp_file = f"{self.persistence_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                os.rename(temp_file, self.persistence_file)
                logger.debug(f"Saved working memory to {self.persistence_file}")
                return True
                
        except Exception as e:
            logger.error(f"Error saving memory to disk: {e}")
            return False
    
    def _load_from_disk(self) -> bool:
        """Load memory contents from disk"""
        try:
            with open(self.persistence_file, 'r') as f:
                data = json.load(f)
            
            # Restore items
            self._memory.clear()
            for item_data in data.get('items', []):
                item = MemoryItem(**item_data)
                # Skip expired items
                if not item.is_expired():
                    self._memory[item.key] = item
            
            # Restore stats
            if 'stats' in data:
                self.stats = MemoryStats(**data['stats'])
            
            logger.info(f"Loaded {len(self._memory)} items from {self.persistence_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading memory from disk: {e}")
            return False
    
    # =====================================
    # Lifecycle and Monitoring
    # =====================================
    
    async def start_cleanup_task(self):
        """Start automatic cleanup task"""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Working memory cleanup task started")
    
    async def stop_cleanup_task(self):
        """Stop automatic cleanup task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Working memory cleanup task stopped")
    
    async def _cleanup_loop(self):
        """Background task for periodic cleanup"""
        while self._running:
            try:
                await self._cleanup_expired()
                
                # Save to disk if persistence is enabled
                if self.persistence_file:
                    await self.save_to_disk()
                
                await asyncio.sleep(self.cleanup_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(self.cleanup_interval)
    
    # =====================================
    # Information and Statistics
    # =====================================
    
    def get_info(self) -> Dict[str, Any]:
        """Get memory system information"""
        with self._lock:
            return {
                'type': 'WorkingMemory',
                'capacity': {
                    'max_items': self.max_items,
                    'max_size_bytes': self.max_size_bytes,
                    'current_items': len(self._memory),
                    'current_size_bytes': self.stats.total_size_bytes,
                    'utilization_items': (len(self._memory) / self.max_items) * 100,
                    'utilization_size': (self.stats.total_size_bytes / self.max_size_bytes) * 100
                },
                'statistics': {
                    'hit_rate': self.stats.get_hit_rate(),
                    'total_hits': self.stats.hit_count,
                    'total_misses': self.stats.miss_count,
                    'evictions': self.stats.eviction_count,
                    'expired_items': self.stats.expired_count,
                    'average_item_size': self.stats.get_average_size()
                },
                'config': {
                    'default_ttl': self.default_ttl,
                    'cleanup_interval': self.cleanup_interval,
                    'persistence_enabled': self.persistence_file is not None
                }
            }
    
    def get_items_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all items in memory"""
        with self._lock:
            summary = []
            for key, item in self._memory.items():
                summary.append({
                    'key': key,
                    'size_bytes': item.size_bytes,
                    'age': item.get_age(),
                    'idle_time': item.get_idle_time(),
                    'access_count': item.access_count,
                    'priority': item.priority,
                    'expires_in': (item.ttl - item.get_age()) if item.ttl else None,
                    'expired': item.is_expired(),
                    'value_type': type(item.value).__name__
                })
            return summary
    
    def get_top_items(self, limit: int = 10, sort_by: str = 'access_count') -> List[Dict[str, Any]]:
        """Get top items by specified criteria"""
        summary = self.get_items_summary()
        
        # Sort by specified criteria
        if sort_by in ['access_count', 'priority', 'size_bytes', 'age']:
            summary.sort(key=lambda x: x[sort_by], reverse=True)
        elif sort_by == 'idle_time':
            summary.sort(key=lambda x: x[sort_by])
        
        return summary[:limit]
    
    def get_memory_usage_breakdown(self) -> Dict[str, Any]:
        """Get detailed memory usage breakdown"""
        with self._lock:
            breakdown = {
                'total_items': len(self._memory),
                'total_size_bytes': self.stats.total_size_bytes,
                'by_type': {},
                'by_priority': {},
                'by_age_group': {'<1h': 0, '1h-1d': 0, '1d-1w': 0, '>1w': 0}
            }
            
            for item in self._memory.values():
                # By value type
                value_type = type(item.value).__name__
                if value_type not in breakdown['by_type']:
                    breakdown['by_type'][value_type] = {'count': 0, 'size_bytes': 0}
                breakdown['by_type'][value_type]['count'] += 1
                breakdown['by_type'][value_type]['size_bytes'] += item.size_bytes
                
                # By priority
                priority_group = f"{int(item.priority)}.x"
                if priority_group not in breakdown['by_priority']:
                    breakdown['by_priority'][priority_group] = {'count': 0, 'size_bytes': 0}
                breakdown['by_priority'][priority_group]['count'] += 1
                breakdown['by_priority'][priority_group]['size_bytes'] += item.size_bytes
                
                # By age
                age = item.get_age()
                if age < 3600:  # < 1 hour
                    breakdown['by_age_group']['<1h'] += 1
                elif age < 86400:  # < 1 day
                    breakdown['by_age_group']['1h-1d'] += 1
                elif age < 604800:  # < 1 week
                    breakdown['by_age_group']['1d-1w'] += 1
                else:
                    breakdown['by_age_group']['>1w'] += 1
            
            return breakdown
    
    def __repr__(self) -> str:
        return f"<WorkingMemory(items={len(self._memory)}, size={self.stats.total_size_bytes}B, hit_rate={self.stats.get_hit_rate():.1f}%)>"

# =====================================
# Utility Functions
# =====================================

async def create_working_memory(config: Dict[str, Any] = None) -> WorkingMemory:
    """Factory function to create and start working memory"""
    config = config or {}
    
    memory = WorkingMemory(
        max_items=config.get('max_items', 1000),
        max_size_bytes=config.get('max_size_bytes', 10 * 1024 * 1024),
        default_ttl=config.get('default_ttl', None),
        persistence_file=config.get('persistence_file', None),
        cleanup_interval=config.get('cleanup_interval', 60.0)
    )
    
    # Start cleanup task if requested
    if config.get('auto_cleanup', True):
        await memory.start_cleanup_task()
    
    return memory

def estimate_memory_usage(value: Any) -> int:
    """Estimate memory usage of a value"""
    try:
        return len(pickle.dumps(value))
    except Exception:
        # Fallback estimation
        if isinstance(value, str):
            return len(value.encode('utf-8'))
        elif isinstance(value, (int, float)):
            return 8
        elif isinstance(value, dict):
            return sum(estimate_memory_usage(k) + estimate_memory_usage(v) for k, v in value.items())
        elif isinstance(value, (list, tuple)):
            return sum(estimate_memory_usage(item) for item in value)
        else:
            return 100  # Default estimate

def create_memory_item(key: str, value: Any, **kwargs) -> MemoryItem:
    """Utility function to create memory items"""
    return MemoryItem(
        key=key,
        value=value,
        priority=kwargs.get('priority', 1.0),
        ttl=kwargs.get('ttl', None),
        metadata=kwargs.get('metadata', {})
    )
