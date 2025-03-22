"""
memory.py - Memory Systems for Neuron Framework

This module implements the memory systems used by agents in the Neuron framework.
The memory system is inspired by human memory architecture, with different types
of memory for different purposes and varying retention characteristics.

The memory system provides agents with the ability to store, retrieve, and forget
information, enabling them to maintain state and learn from past experiences.
"""

import asyncio
import heapq
import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar, Union

from .config import config
from .exceptions import MemoryAccessError, MemoryStorageError
from .types import AgentID, MemoryEntry, MemoryID, MemoryType

logger = logging.getLogger(__name__)

# Type for memory query results
T = TypeVar('T')


class MemoryStore(ABC):
    """
    Abstract base class for memory storage backends.
    
    This defines the interface that all memory stores must implement,
    allowing for different storage backends to be used (e.g., in-memory,
    file-based, database).
    """
    
    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """
        Store a memory entry.
        
        Args:
            entry: Memory entry to store
            
        Raises:
            MemoryStorageError: If storage fails
        """
        pass
    
    @abstractmethod
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: MemoryID) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            MemoryAccessError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """
        Clear all memory entries.
        
        Raises:
            MemoryAccessError: If clearing fails
        """
        pass


class InMemoryStore(MemoryStore):
    """
    In-memory implementation of MemoryStore.
    
    This provides a simple, fast memory store that keeps all entries
    in memory. It's suitable for testing and small-scale deployments
    but does not persist across restarts.
    """
    
    def __init__(self):
        """Initialize an in-memory store."""
        self._store = {}  # memory_id -> MemoryEntry
        self._lock = asyncio.Lock()
    
    async def store(self, entry: MemoryEntry) -> None:
        """
        Store a memory entry.
        
        Args:
            entry: Memory entry to store
        """
        async with self._lock:
            self._store[entry.id] = entry
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
        """
        async with self._lock:
            entry = self._store.get(memory_id)
            if entry:
                # Update access metadata
                entry.access()
            return entry
    
    async def delete(self, memory_id: MemoryID) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if memory_id in self._store:
                del self._store[memory_id]
                return True
            return False
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        This implements a simple filtering mechanism based on exact matches
        of query parameters to memory entry attributes and metadata.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
        """
        async with self._lock:
            results = []
            
            for entry in self._store.values():
                match = True
                entry_dict = asdict(entry)
                
                # Check each query parameter
                for key, value in query.items():
                    # Handle nested keys (dot notation)
                    if '.' in key:
                        parts = key.split('.')
                        current = entry_dict
                        for part in parts[:-1]:
                            if not isinstance(current, dict) or part not in current:
                                match = False
                                break
                            current = current[part]
                        
                        if match and (parts[-1] not in current or current[parts[-1]] != value):
                            match = False
                    # Handle direct keys
                    elif key not in entry_dict or entry_dict[key] != value:
                        match = False
                
                if match:
                    # Update access metadata for matched entries
                    entry.access()
                    results.append(entry)
            
            # Apply limit if specified
            if limit is not None and limit > 0:
                results = results[:limit]
            
            return results
    
    async def clear(self) -> None:
        """Clear all memory entries."""
        async with self._lock:
            self._store.clear()


class FileStore(MemoryStore):
    """
    File-based implementation of MemoryStore.
    
    This provides a persistent memory store that saves entries to files.
    It's slower than InMemoryStore but persists across restarts.
    """
    
    def __init__(self, directory: Union[str, Path]):
        """
        Initialize a file-based store.
        
        Args:
            directory: Directory to store memory files in
        """
        self._directory = Path(directory)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._cache = {}  # memory_id -> MemoryEntry (small cache for frequent accesses)
        self._max_cache_size = 1000
    
    def _get_file_path(self, memory_id: MemoryID) -> Path:
        """
        Get the file path for a memory ID.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Path to the memory file
        """
        # Use a simple sharded structure to avoid too many files in one directory
        shard = memory_id[:2]
        shard_dir = self._directory / shard
        shard_dir.mkdir(exist_ok=True)
        return shard_dir / f"{memory_id}.json"
    
    async def store(self, entry: MemoryEntry) -> None:
        """
        Store a memory entry.
        
        Args:
            entry: Memory entry to store
            
        Raises:
            MemoryStorageError: If storage fails
        """
        async with self._lock:
            try:
                # Add to cache
                self._cache[entry.id] = entry
                
                # Trim cache if needed
                if len(self._cache) > self._max_cache_size:
                    # Remove oldest entries (approximation)
                    remove_count = len(self._cache) - self._max_cache_size
                    for _ in range(remove_count):
                        self._cache.pop(next(iter(self._cache)))
                
                # Write to file
                file_path = self._get_file_path(entry.id)
                entry_dict = entry.to_dict()
                
                # Write to a temporary file, then atomically rename
                temp_path = file_path.with_suffix('.tmp')
                with open(temp_path, 'w') as f:
                    json.dump(entry_dict, f)
                temp_path.rename(file_path)
            except Exception as e:
                raise MemoryStorageError(f"Failed to store memory entry: {e}") from e
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        async with self._lock:
            # Check cache first
            if memory_id in self._cache:
                entry = self._cache[memory_id]
                entry.access()
                return entry
            
            # Try to load from file
            file_path = self._get_file_path(memory_id)
            if not file_path.exists():
                return None
            
            try:
                with open(file_path, 'r') as f:
                    entry_dict = json.load(f)
                
                entry = MemoryEntry.from_dict(entry_dict)
                
                # Update access metadata
                entry.access()
                
                # Add to cache
                self._cache[memory_id] = entry
                
                return entry
            except Exception as e:
                raise MemoryAccessError(f"Failed to retrieve memory entry: {e}") from e
    
    async def delete(self, memory_id: MemoryID) -> bool:
        """
        Delete a memory entry.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            MemoryAccessError: If deletion fails
        """
        async with self._lock:
            try:
                # Remove from cache
                if memory_id in self._cache:
                    del self._cache[memory_id]
                
                # Remove file
                file_path = self._get_file_path(memory_id)
                if file_path.exists():
                    file_path.unlink()
                    return True
                return False
            except Exception as e:
                raise MemoryAccessError(f"Failed to delete memory entry: {e}") from e
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        This implementation is not efficient for file-based storage as it 
        needs to load all entries to perform the query. In a real-world
        implementation, you would want to use an indexed database.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        async with self._lock:
            try:
                results = []
                
                # Iterate through all files in the directory (inefficient, but simple)
                for shard_dir in self._directory.iterdir():
                    if not shard_dir.is_dir():
                        continue
                    
                    for file_path in shard_dir.glob("*.json"):
                        try:
                            # Load the entry
                            with open(file_path, 'r') as f:
                                entry_dict = json.load(f)
                            
                            # Check if it matches the query
                            match = True
                            for key, value in query.items():
                                # Handle nested keys (dot notation)
                                if '.' in key:
                                    parts = key.split('.')
                                    current = entry_dict
                                    for part in parts[:-1]:
                                        if not isinstance(current, dict) or part not in current:
                                            match = False
                                            break
                                        current = current[part]
                                    
                                    if match and (parts[-1] not in current or current[parts[-1]] != value):
                                        match = False
                                # Handle direct keys
                                elif key not in entry_dict or entry_dict[key] != value:
                                    match = False
                            
                            if match:
                                entry = MemoryEntry.from_dict(entry_dict)
                                entry.access()
                                results.append(entry)
                                
                                # Update the file with new access time
                                await self.store(entry)
                                
                                # Stop if we've reached the limit
                                if limit is not None and len(results) >= limit:
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading memory file {file_path}: {e}")
                    
                    # Stop if we've reached the limit
                    if limit is not None and len(results) >= limit:
                        break
                
                return results
            except Exception as e:
                raise MemoryAccessError(f"Failed to query memory entries: {e}") from e
    
    async def clear(self) -> None:
        """
        Clear all memory entries.
        
        Raises:
            MemoryAccessError: If clearing fails
        """
        async with self._lock:
            try:
                # Clear cache
                self._cache.clear()
                
                # Remove all files
                for shard_dir in self._directory.iterdir():
                    if not shard_dir.is_dir():
                        continue
                    
                    for file_path in shard_dir.glob("*.json"):
                        file_path.unlink()
                    
                    # Remove empty shard directories
                    if not any(shard_dir.iterdir()):
                        shard_dir.rmdir()
            except Exception as e:
                raise MemoryAccessError(f"Failed to clear memory store: {e}") from e


class MemoryManagerBase(ABC):
    """
    Abstract base class for memory systems.
    
    This defines the interface for memory systems, which allow agents
    to store, retrieve, and manage information. Different memory system
    implementations can provide different types of memory (working, episodic,
    semantic, etc.) with different characteristics.
    """
    
    def __init__(self):
        """Initialize the memory system."""
        self._agent_id = None
    
    def set_agent_id(self, agent_id: AgentID) -> None:
        """
        Set the agent ID for this memory system.
        
        Args:
            agent_id: ID of the agent this memory belongs to
        """
        self._agent_id = agent_id
    
    @abstractmethod
    async def store(self, content: Any, memory_type: MemoryType,
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in memory.
        
        Args:
            content: Content to store
            memory_type: Type of memory to store in
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
        """
        pass
    
    @abstractmethod
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve an item from memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        pass
    
    @abstractmethod
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        pass
    
    @abstractmethod
    async def forget(self, memory_id: MemoryID) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        pass
    
    @abstractmethod
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        pass
    
    @abstractmethod
    async def consolidate(self) -> None:
        """
        Consolidate memories based on memory management policies.
        
        This process might involve forgetting less important memories,
        summarizing related memories, or transferring between memory types.
        
        Raises:
            MemoryAccessError: If consolidation fails
        """
        pass
    
    @abstractmethod
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear all memories of a specific type or all types.
        
        Args:
            memory_type: Type of memory to clear, or None for all types
            
        Raises:
            MemoryAccessError: If clearing fails
        """
        pass


class WorkingMemory(MemoryManagerBase):
    """
    Working (short-term) memory implementation.
    
    Working memory has limited capacity and is used for temporary storage
    of information needed for current processing. It follows a least-recently-used
    eviction policy when capacity is exceeded.
    """
    
    def __init__(self, capacity: int = 100, store: Optional[MemoryStore] = None):
        """
        Initialize working memory.
        
        Args:
            capacity: Maximum number of items in working memory
            store: Memory store to use (creates InMemoryStore if None)
        """
        super().__init__()
        self._capacity = capacity
        self._store = store or InMemoryStore()
        self._lru_tracker = OrderedDict()  # memory_id -> access timestamp
    
    async def store(self, content: Any, memory_type: MemoryType = MemoryType.WORKING,
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in working memory.
        
        If capacity is exceeded, the least recently used item is evicted.
        
        Args:
            content: Content to store
            memory_type: Type of memory (ignored, always WORKING)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Always use WORKING memory type
        memory_type = MemoryType.WORKING
        
        # Create memory entry
        entry = MemoryEntry.create(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata or {}
        )
        
        # Store the entry
        await self._store.store(entry)
        
        # Update LRU tracker
        self._lru_tracker[entry.id] = entry.last_accessed
        
        # Check capacity and evict if needed
        await self._check_capacity()
        
        return entry.id
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve an item from working memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        entry = await self._store.retrieve(memory_id)
        
        if entry:
            # Update LRU tracker
            self._lru_tracker[entry.id] = entry.last_accessed
        
        return entry
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        # Ensure we only query for WORKING memory type
        query = {**query, "memory_type": MemoryType.WORKING.name}
        
        results = await self._store.query(query, limit)
        
        # Update LRU tracker for all retrieved entries
        for entry in results:
            self._lru_tracker[entry.id] = entry.last_accessed
        
        return results
    
    async def forget(self, memory_id: MemoryID) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        result = await self._store.delete(memory_id)
        
        if result and memory_id in self._lru_tracker:
            del self._lru_tracker[memory_id]
        
        return result
    
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Retrieve the entry
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        # Update importance
        entry.update_importance(importance)
        
        # Store the updated entry
        await self._store.store(entry)
        
        return True
    
    async def consolidate(self) -> None:
        """
        Consolidate working memory.
        
        For working memory, this just checks capacity and evicts
        if needed.
        """
        await self._check_capacity()
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear all memories.
        
        Args:
            memory_type: Ignored for working memory
        """
        await self._store.clear()
        self._lru_tracker.clear()
    
    async def _check_capacity(self) -> None:
        """
        Check if capacity is exceeded and evict if needed.
        
        This implements a least-recently-used eviction policy.
        """
        while len(self._lru_tracker) > self._capacity:
            # Get the least recently used item
            oldest_id, _ = next(iter(self._lru_tracker.items()))
            
            # Forget it
            await self.forget(oldest_id)


class EpisodicMemory(MemoryManagerBase):
    """
    Episodic (event-based) memory implementation.
    
    Episodic memory stores records of experiences and events, with
    temporal context. It has a larger capacity than working memory
    but may forget less important memories over time.
    """
    
    def __init__(self, store: Optional[MemoryStore] = None,
                forget_threshold: float = 0.3,
                time_decay_factor: float = 0.1):
        """
        Initialize episodic memory.
        
        Args:
            store: Memory store to use (creates InMemoryStore if None)
            forget_threshold: Importance threshold below which memories may be forgotten
            time_decay_factor: Factor for time-based importance decay
        """
        super().__init__()
        self._store = store or InMemoryStore()
        self._forget_threshold = forget_threshold
        self._time_decay_factor = time_decay_factor
        self._last_consolidation = time.time()
    
    async def store(self, content: Any, memory_type: MemoryType = MemoryType.EPISODIC,
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in episodic memory.
        
        Args:
            content: Content to store
            memory_type: Type of memory (ignored, always EPISODIC)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Always use EPISODIC memory type
        memory_type = MemoryType.EPISODIC
        
        # Ensure metadata includes temporal context
        metadata = metadata or {}
        if "timestamp" not in metadata:
            metadata["timestamp"] = time.time()
        
        # Create memory entry
        entry = MemoryEntry.create(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        # Store the entry
        await self._store.store(entry)
        
        return entry.id
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve an item from episodic memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        entry = await self._store.retrieve(memory_id)
        
        if entry and entry.memory_type == MemoryType.EPISODIC:
            # Boost importance slightly when accessed (memory strengthening)
            if entry.importance < 0.95:
                entry.update_importance(entry.importance + 0.05)
                await self._store.store(entry)
        
        return entry
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        # Ensure we only query for EPISODIC memory type
        query = {**query, "memory_type": MemoryType.EPISODIC.name}
        
        results = await self._store.query(query, limit)
        
        # Boost importance slightly for all retrieved entries
        for entry in results:
            if entry.importance < 0.95:
                entry.update_importance(entry.importance + 0.05)
                await self._store.store(entry)
        
        return results
    
    async def forget(self, memory_id: MemoryID) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        return await self._store.delete(memory_id)
    
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Retrieve the entry
        entry = await self.retrieve(memory_id)
        if not entry or entry.memory_type != MemoryType.EPISODIC:
            return False
        
        # Update importance
        entry.update_importance(importance)
        
        # Store the updated entry
        await self._store.store(entry)
        
        return True
    
    async def consolidate(self) -> None:
        """
        Consolidate episodic memory.
        
        This process involves:
        1. Decaying importance of memories over time
        2. Forgetting memories below the importance threshold
        """
        current_time = time.time()
        time_since_last = current_time - self._last_consolidation
        
        # Don't consolidate too frequently
        if time_since_last < 3600:  # 1 hour
            return
        
        self._last_consolidation = current_time
        
        # Query all episodic memories
        all_memories = await self.query({}, None)
        
        for entry in all_memories:
            # Calculate time decay
            age = current_time - entry.created_at
            decay = min(0.9, self._time_decay_factor * (age / 86400))  # 86400 seconds in a day
            
            # Apply decay to importance
            new_importance = max(0.0, entry.importance - decay)
            entry.update_importance(new_importance)
            
            if new_importance < self._forget_threshold:
                # Forget memories below threshold
                await self.forget(entry.id)
            else:
                # Store updated importance
                await self._store.store(entry)
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear all episodic memories.
        
        Args:
            memory_type: Ignored for episodic memory
        """
        # Query all episodic memories
        all_memories = await self.query({}, None)
        
        # Delete each one
        for entry in all_memories:
            await self.forget(entry.id)


class SemanticMemory(MemoryManagerBase):
    """
    Semantic (knowledge-based) memory implementation.
    
    Semantic memory stores factual, conceptual knowledge independent of
    specific experiences. It has a hierarchical organization and focuses
    on relationships between concepts.
    """
    
    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize semantic memory.
        
        Args:
            store: Memory store to use (creates InMemoryStore if None)
        """
        super().__init__()
        self._store = store or InMemoryStore()
    
    async def store(self, content: Any, memory_type: MemoryType = MemoryType.SEMANTIC,
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in semantic memory.
        
        Args:
            content: Content to store
            memory_type: Type of memory (ignored, always SEMANTIC)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Always use SEMANTIC memory type
        memory_type = MemoryType.SEMANTIC
        
        # Ensure metadata includes concept categorization
        metadata = metadata or {}
        if "concept" not in metadata:
            metadata["concept"] = "general"
        
        # Create memory entry
        entry = MemoryEntry.create(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        # Store the entry
        await self._store.store(entry)
        
        return entry.id
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve an item from semantic memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        entry = await self._store.retrieve(memory_id)
        
        # Only return if it's a semantic memory
        if entry and entry.memory_type == MemoryType.SEMANTIC:
            return entry
        return None
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        # Ensure we only query for SEMANTIC memory type
        query = {**query, "memory_type": MemoryType.SEMANTIC.name}
        
        return await self._store.query(query, limit)
    
    async def query_by_concept(self, concept: str, limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for semantic memories by concept.
        
        Args:
            concept: Concept to query for
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        return await self.query({"metadata.concept": concept}, limit)
    
    async def forget(self, memory_id: MemoryID) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        # First check if it's a semantic memory
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        return await self._store.delete(memory_id)
    
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Retrieve the entry
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        # Update importance
        entry.update_importance(importance)
        
        # Store the updated entry
        await self._store.store(entry)
        
        return True
    
    async def consolidate(self) -> None:
        """
        Consolidate semantic memory.
        
        For semantic memory, consolidation involves identifying related
        concepts and organizing them hierarchically. This is a complex
        process that would typically involve machine learning or predefined
        taxonomies.
        
        This implementation is simplified and focuses on merging duplicate
        or highly similar concepts.
        """
        # Query all concepts
        all_memories = await self.query({}, None)
        
        # Group by concept
        concepts = {}
        for entry in all_memories:
            concept = entry.metadata.get("concept", "general")
            if concept not in concepts:
                concepts[concept] = []
            concepts[concept].append(entry)
        
        # For each concept with multiple entries, consider consolidation
        for concept, entries in concepts.items():
            if len(entries) <= 1:
                continue
            
            # Sort by importance (highest first)
            entries.sort(key=lambda x: x.importance, reverse=True)
            
            # For simplicity, we'll just keep the most important entry
            # and merge metadata from others
            primary = entries[0]
            
            # Initialize merged metadata
            if "related" not in primary.metadata:
                primary.metadata["related"] = []
            
            # Merge from other entries
            for other in entries[1:]:
                # Add other's ID to related list
                primary.metadata["related"].append(other.id)
                
                # Boost primary's importance slightly
                new_importance = min(1.0, primary.importance + 0.05)
                primary.update_importance(new_importance)
            
            # Store updated primary entry
            await self._store.store(primary)
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear all semantic memories.
        
        Args:
            memory_type: Ignored for semantic memory
        """
        # Query all semantic memories
        all_memories = await self.query({}, None)
        
        # Delete each one
        for entry in all_memories:
            await self.forget(entry.id)


class ProceduralMemory(MemoryManagerBase):
    """
    Procedural (skill-based) memory implementation.
    
    Procedural memory stores knowledge about how to perform specific tasks
    or skills. It focuses on action sequences and procedures.
    """
    
    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize procedural memory.
        
        Args:
            store: Memory store to use (creates InMemoryStore if None)
        """
        super().__init__()
        self._store = store or InMemoryStore()
    
    async def store(self, content: Any, memory_type: MemoryType = MemoryType.PROCEDURAL,
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in procedural memory.
        
        Args:
            content: Content to store (typically a procedure or skill)
            memory_type: Type of memory (ignored, always PROCEDURAL)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Always use PROCEDURAL memory type
        memory_type = MemoryType.PROCEDURAL
        
        # Ensure metadata includes skill categorization
        metadata = metadata or {}
        if "skill" not in metadata:
            metadata["skill"] = "general"
        
        # Create memory entry
        entry = MemoryEntry.create(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        # Store the entry
        await self._store.store(entry)
        
        return entry.id
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve an item from procedural memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        entry = await self._store.retrieve(memory_id)
        
        # Only return if it's a procedural memory
        if entry and entry.memory_type == MemoryType.PROCEDURAL:
            return entry
        return None
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        # Ensure we only query for PROCEDURAL memory type
        query = {**query, "memory_type": MemoryType.PROCEDURAL.name}
        
        return await self._store.query(query, limit)
    
    async def query_by_skill(self, skill: str, limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for procedural memories by skill.
        
        Args:
            skill: Skill to query for
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        return await self.query({"metadata.skill": skill}, limit)
    
    async def forget(self, memory_id: MemoryID) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        # First check if it's a procedural memory
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        return await self._store.delete(memory_id)
    
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Retrieve the entry
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        # Update importance
        entry.update_importance(importance)
        
        # Store the updated entry
        await self._store.store(entry)
        
        return True
    
    async def consolidate(self) -> None:
        """
        Consolidate procedural memory.
        
        For procedural memory, consolidation involves identifying related
        skills and potentially combining them into more complex procedures.
        
        This implementation is simplified and focuses on organizing skills
        into hierarchies.
        """
        # Query all skills
        all_memories = await self.query({}, None)
        
        # Group by skill
        skills = {}
        for entry in all_memories:
            skill = entry.metadata.get("skill", "general")
            if skill not in skills:
                skills[skill] = []
            skills[skill].append(entry)
        
        # For each skill with multiple entries, consider organizing into a hierarchy
        for skill, entries in skills.items():
            if len(entries) <= 1:
                continue
            
            # Sort by complexity (if available) or importance
            if all("complexity" in entry.metadata for entry in entries):
                entries.sort(key=lambda x: x.metadata["complexity"])
            else:
                entries.sort(key=lambda x: x.importance, reverse=True)
            
            # Update entries with hierarchy information
            for i, entry in enumerate(entries):
                if "hierarchy" not in entry.metadata:
                    entry.metadata["hierarchy"] = {}
                
                # Add next and previous in sequence
                if i > 0:
                    entry.metadata["hierarchy"]["previous"] = entries[i-1].id
                if i < len(entries) - 1:
                    entry.metadata["hierarchy"]["next"] = entries[i+1].id
                
                # Store updated entry
                await self._store.store(entry)
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear all procedural memories.
        
        Args:
            memory_type: Ignored for procedural memory
        """
        # Query all procedural memories
        all_memories = await self.query({}, None)
        
        # Delete each one
        for entry in all_memories:
            await self.forget(entry.id)


class EmotionalMemory(MemoryManagerBase):
    """
    Emotional memory implementation.
    
    Emotional memory stores affective associations with concepts, experiences,
    and entities. It allows agents to develop emotional responses and preferences.
    """
    
    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize emotional memory.
        
        Args:
            store: Memory store to use (creates InMemoryStore if None)
        """
        super().__init__()
        self._store = store or InMemoryStore()
    
    async def store(self, content: Any, memory_type: MemoryType = MemoryType.EMOTIONAL,
                  importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in emotional memory.
        
        Args:
            content: Content to store (typically an emotional association)
            memory_type: Type of memory (ignored, always EMOTIONAL)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Always use EMOTIONAL memory type
        memory_type = MemoryType.EMOTIONAL
        
        # Ensure metadata includes emotion information
        metadata = metadata or {}
        if "emotion" not in metadata:
            metadata["emotion"] = "neutral"
        if "intensity" not in metadata:
            metadata["intensity"] = 0.5
        
        # Create memory entry
        entry = MemoryEntry.create(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata
        )
        
        # Store the entry
        await self._store.store(entry)
        
        return entry.id
    
    async def retrieve(self, memory_id: MemoryID) -> Optional[MemoryEntry]:
        """
        Retrieve an item from emotional memory by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        entry = await self._store.retrieve(memory_id)
        
        # Only return if it's an emotional memory
        if entry and entry.memory_type == MemoryType.EMOTIONAL:
            return entry
        return None
    
    async def query(self, query: Dict[str, Any], limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        # Ensure we only query for EMOTIONAL memory type
        query = {**query, "memory_type": MemoryType.EMOTIONAL.name}
        
        return await self._store.query(query, limit)
    
    async def query_by_emotion(self, emotion: str, min_intensity: float = 0.0,
                            limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for emotional memories by emotion.
        
        Args:
            emotion: Emotion to query for
            min_intensity: Minimum intensity threshold
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
            ValueError: If min_intensity is outside valid range
        """
        if not 0.0 <= min_intensity <= 1.0:
            raise ValueError("Minimum intensity must be between 0.0 and 1.0")
        
        # Query for entries with matching emotion
        entries = await self.query({"metadata.emotion": emotion}, limit)
        
        # Filter by intensity
        if min_intensity > 0.0:
            entries = [entry for entry in entries 
                      if entry.metadata.get("intensity", 0.0) >= min_intensity]
        
        return entries
    
    async def forget(self, memory_id: MemoryID) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        # First check if it's an emotional memory
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        return await self._store.delete(memory_id)
    
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        if not 0.0 <= importance <= 1.0:
            raise ValueError("Importance must be between 0.0 and 1.0")
        
        # Retrieve the entry
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        # Update importance
        entry.update_importance(importance)
        
        # Store the updated entry
        await self._store.store(entry)
        
        return True
    
    async def update_emotion(self, memory_id: MemoryID, emotion: str, intensity: float) -> bool:
        """
        Update the emotion and intensity of a memory.
        
        Args:
            memory_id: ID of the memory to update
            emotion: New emotion
            intensity: New intensity (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If intensity is outside valid range
        """
        if not 0.0 <= intensity <= 1.0:
            raise ValueError("Intensity must be between 0.0 and 1.0")
        
        # Retrieve the entry
        entry = await self.retrieve(memory_id)
        if not entry:
            return False
        
        # Update emotion and intensity
        entry.metadata["emotion"] = emotion
        entry.metadata["intensity"] = intensity
        
        # Store the updated entry
        await self._store.store(entry)
        
        return True
    
    async def consolidate(self) -> None:
        """
        Consolidate emotional memory.
        
        For emotional memory, consolidation involves aggregating emotional
        responses to similar stimuli and potentially developing more complex
        emotional associations.
        """
        # Query all emotional memories
        all_memories = await self.query({}, None)
        
        # Group by stimulus (if available) or target
        stimuli = {}
        for entry in all_memories:
            stimulus = entry.metadata.get("stimulus") or entry.metadata.get("target", "general")
            if stimulus not in stimuli:
                stimuli[stimulus] = []
            stimuli[stimulus].append(entry)
        
        # For each stimulus with multiple entries, consider aggregating
        for stimulus, entries in stimuli.items():
            if len(entries) <= 1:
                continue
            
            # Group by emotion
            emotions = {}
            for entry in entries:
                emotion = entry.metadata.get("emotion", "neutral")
                if emotion not in emotions:
                    emotions[emotion] = []
                emotions[emotion].append(entry)
            
            # For each emotion, create or update an aggregate entry
            for emotion, emotion_entries in emotions.items():
                # Calculate average intensity
                total_intensity = sum(entry.metadata.get("intensity", 0.5) for entry in emotion_entries)
                avg_intensity = total_intensity / len(emotion_entries)
                
                # Find or create an aggregate entry
                aggregate_query = {
                    "metadata.aggregate": True,
                    "metadata.stimulus": stimulus,
                    "metadata.emotion": emotion
                }
                aggregate_entries = await self.query(aggregate_query, 1)
                
                if aggregate_entries:
                    # Update existing aggregate
                    aggregate = aggregate_entries[0]
                    aggregate.metadata["intensity"] = avg_intensity
                    aggregate.metadata["count"] = len(emotion_entries)
                    aggregate.metadata["last_updated"] = time.time()
                    
                    # Store updated aggregate
                    await self._store.store(aggregate)
                else:
                    # Create new aggregate
                    await self.store(
                        content=f"Aggregate emotional response to {stimulus}",
                        importance=0.7,  # Aggregates are more important
                        metadata={
                            "aggregate": True,
                            "stimulus": stimulus,
                            "emotion": emotion,
                            "intensity": avg_intensity,
                            "count": len(emotion_entries),
                            "last_updated": time.time()
                        }
                    )
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear all emotional memories.
        
        Args:
            memory_type: Ignored for emotional memory
        """
        # Query all emotional memories
        all_memories = await self.query({}, None)
        
        # Delete each one
        for entry in all_memories:
            await self.forget(entry.id)


class MemoryManager:
    """
    Coordinates different types of memory for the Neuron framework.
    
    The MemoryManager provides a unified interface to access different memory
    systems (working, episodic, semantic, etc.) and manages the flow of information
    between them.
    
    Conceptually, this is similar to how the brain integrates different memory
    systems to provide a cohesive experience of remembering.
    """
    
    def __init__(self):
        """Initialize the memory manager."""
        self._memory_systems = {}
        self._lock = threading.RLock()
        self._consolidation_interval = 3600  # 1 hour
        self._last_consolidation = time.time()
        self._consolidation_task = None
        
        logger.info("Initialized MemoryManager")
    
    def initialize(self) -> None:
        """
        Initialize memory systems.
        
        This creates the default memory systems and sets up any
        required infrastructure.
        """
        with self._lock:
            # Create default memory systems
            self._memory_systems[MemoryType.WORKING] = WorkingMemory(
                capacity=config.get("memory", "working_memory_capacity", 100)
            )
            
            self._memory_systems[MemoryType.EPISODIC] = EpisodicMemory(
                forget_threshold=config.get("memory", "importance_threshold", 0.3),
                time_decay_factor=0.1
            )
            
            self._memory_systems[MemoryType.SEMANTIC] = SemanticMemory()
            self._memory_systems[MemoryType.PROCEDURAL] = ProceduralMemory()
            self._memory_systems[MemoryType.EMOTIONAL] = EmotionalMemory()
        
        logger.info("MemoryManager initialized memory systems")
    
    def start(self) -> None:
        """
        Start memory management processes.
        
        This initiates background tasks like memory consolidation.
        """
        # Start consolidation task
        self._consolidation_task = asyncio.create_task(self._consolidation_loop())
        
        logger.info("MemoryManager started")
    
    def stop(self) -> None:
        """
        Stop memory management processes.
        
        This terminates background tasks and performs any necessary cleanup.
        """
        # Stop consolidation task
        if self._consolidation_task:
            self._consolidation_task.cancel()
        
        logger.info("MemoryManager stopped")
    
    async def store(self, content: Any, memory_type: MemoryType,
                   agent_id: Optional[AgentID] = None,
                   importance: float = 0.5,
                   metadata: Optional[Dict[str, Any]] = None) -> MemoryID:
        """
        Store an item in the specified memory system.
        
        Args:
            content: Content to store
            memory_type: Type of memory to store in
            agent_id: Optional ID of the agent this memory belongs to
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata
            
        Returns:
            ID of the stored memory
            
        Raises:
            MemoryStorageError: If storage fails
            ValueError: If the memory type is not supported
        """
        memory_system = self._get_memory_system(memory_type)
        
        # Add agent ID to metadata if provided
        metadata = metadata or {}
        if agent_id:
            metadata["agent_id"] = agent_id
        
        # Store in the appropriate memory system
        return await memory_system.store(content, memory_type, importance, metadata)
    
    async def retrieve(self, memory_id: MemoryID, memory_type: Optional[MemoryType] = None) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry by ID.
        
        Args:
            memory_id: ID of the memory to retrieve
            memory_type: Optional type hint to speed up retrieval
            
        Returns:
            Memory entry if found, None otherwise
            
        Raises:
            MemoryAccessError: If retrieval fails
        """
        if memory_type:
            # If type is provided, try that system first
            memory_system = self._get_memory_system(memory_type)
            entry = await memory_system.retrieve(memory_id)
            if entry:
                return entry
        
        # If type is not provided or entry not found, try all systems
        for system_type, system in self._memory_systems.items():
            if memory_type and system_type == memory_type:
                # Already checked this one
                continue
            
            entry = await system.retrieve(memory_id)
            if entry:
                return entry
        
        return None
    
    async def query(self, query: Dict[str, Any], memory_type: Optional[MemoryType] = None,
                   limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Query for memory entries matching criteria.
        
        Args:
            query: Query criteria
            memory_type: Optional type to query in specific memory system
            limit: Maximum number of results to return
            
        Returns:
            List of matching memory entries
            
        Raises:
            MemoryAccessError: If query fails
        """
        if memory_type:
            # If type is provided, query only that system
            memory_system = self._get_memory_system(memory_type)
            return await memory_system.query(query, limit)
        
        # If type is not provided, query all systems
        results = []
        remaining_limit = limit
        
        for system in self._memory_systems.values():
            system_limit = remaining_limit
            system_results = await system.query(query, system_limit)
            results.extend(system_results)
            
            # Update remaining limit
            if limit is not None:
                remaining_limit = limit - len(results)
                if remaining_limit <= 0:
                    break
        
        return results
    
    async def forget(self, memory_id: MemoryID, memory_type: Optional[MemoryType] = None) -> bool:
        """
        Forget (delete) a memory.
        
        Args:
            memory_id: ID of the memory to forget
            memory_type: Optional type hint to speed up forgetting
            
        Returns:
            True if forgotten, False if not found
            
        Raises:
            MemoryAccessError: If forgetting fails
        """
        if memory_type:
            # If type is provided, try that system first
            memory_system = self._get_memory_system(memory_type)
            result = await memory_system.forget(memory_id)
            if result:
                return True
        
        # If type is not provided or entry not found, try all systems
        for system_type, system in self._memory_systems.items():
            if memory_type and system_type == memory_type:
                # Already checked this one
                continue
            
            result = await system.forget(memory_id)
            if result:
                return True
        
        return False
    
    async def update_importance(self, memory_id: MemoryID, importance: float) -> bool:
        """
        Update the importance of a memory.
        
        Args:
            memory_id: ID of the memory to update
            importance: New importance score (0.0 to 1.0)
            
        Returns:
            True if updated, False if not found
            
        Raises:
            MemoryAccessError: If update fails
            ValueError: If importance is outside valid range
        """
        # Find the memory to update
        memory = await self.retrieve(memory_id)
        if not memory:
            return False
        
        # Update in the appropriate memory system
        memory_system = self._get_memory_system(memory.memory_type)
        return await memory_system.update_importance(memory_id, importance)
    
    async def consolidate(self) -> None:
        """
        Consolidate all memory systems.
        
        This triggers the consolidation process for each memory system
        and also manages the transfer of information between systems.
        
        Raises:
            MemoryAccessError: If consolidation fails
        """
        logger.info("Starting memory consolidation")
        
        # Consolidate each memory system
        for memory_type, system in self._memory_systems.items():
            try:
                await system.consolidate()
            except Exception as e:
                logger.error(f"Error consolidating {memory_type.name} memory: {e}")
        
        # Transfer memories between systems as needed
        await self._transfer_memories()
        
        self._last_consolidation = time.time()
        logger.info("Memory consolidation completed")
    
    async def _transfer_memories(self) -> None:
        """
        Transfer memories between memory systems based on importance and access patterns.
        
        This implements a simplified version of memory consolidation in the brain,
        where information moves between short-term and long-term memory systems.
        """
        try:
            # Transfer from working to episodic memory
            working_memory = self._get_memory_system(MemoryType.WORKING)
            episodic_memory = self._get_memory_system(MemoryType.EPISODIC)
            
            # Get working memories that are important and frequently accessed
            important_working_memories = await working_memory.query(
                {"importance": lambda x: x >= 0.7},  # This is a simplification
                None
            )
            
            for memory in important_working_memories:
                # Check if it's been accessed multiple times
                if memory.access_count >= 3:
                    # Transfer to episodic memory
                    await episodic_memory.store(
                        content=memory.content,
                        memory_type=MemoryType.EPISODIC,
                        importance=memory.importance,
                        metadata={
                            **memory.metadata,
                            "transferred_from": "working",
                            "original_id": memory.id,
                            "transfer_time": time.time()
                        }
                    )
            
            # Transfer from episodic to semantic memory (for conceptual knowledge)
            semantic_memory = self._get_memory_system(MemoryType.SEMANTIC)
            
            # Get episodic memories that might contain semantic knowledge
            potential_semantic_memories = await episodic_memory.query(
                {"metadata.content_type": "knowledge"},  # This is a simplification
                None
            )
            
            for memory in potential_semantic_memories:
                # Transfer to semantic memory
                await semantic_memory.store(
                    content=memory.content,
                    memory_type=MemoryType.SEMANTIC,
                    importance=memory.importance,
                    metadata={
                        **memory.metadata,
                        "transferred_from": "episodic",
                        "original_id": memory.id,
                        "transfer_time": time.time()
                    }
                )
        except Exception as e:
            logger.error(f"Error transferring memories: {e}")
    
    async def _consolidation_loop(self) -> None:
        """
        Background task for periodic memory consolidation.
        
        This runs at regular intervals to consolidate memories and
        ensure efficient memory management.
        """
        try:
            while True:
                # Sleep until next consolidation
                current_time = time.time()
                time_since_last = current_time - self._last_consolidation
                
                if time_since_last < self._consolidation_interval:
                    sleep_time = self._consolidation_interval - time_since_last
                    await asyncio.sleep(sleep_time)
                
                # Consolidate memories
                await self.consolidate()
        except asyncio.CancelledError:
            logger.debug("Memory consolidation task cancelled")
        except Exception as e:
            logger.error(f"Error in memory consolidation loop: {e}")
    
    async def clear(self, memory_type: Optional[MemoryType] = None) -> None:
        """
        Clear memories of a specific type or all types.
        
        Args:
            memory_type: Type of memory to clear, or None for all types
            
        Raises:
            MemoryAccessError: If clearing fails
        """
        if memory_type:
            # Clear specific memory type
            memory_system = self._get_memory_system(memory_type)
            await memory_system.clear()
        else:
            # Clear all memory types
            for system in self._memory_systems.values():
                await system.clear()
    
    def get_memory_system(self, memory_type: MemoryType) -> MemoryManagerBase:
        """
        Get a specific memory system.
        
        Args:
            memory_type: Type of memory system to get
            
        Returns:
            The requested memory system
            
        Raises:
            ValueError: If the memory type is not supported
        """
        return self._get_memory_system(memory_type)
    
    def _get_memory_system(self, memory_type: MemoryType) -> MemoryManagerBase:
        """
        Get a specific memory system (internal implementation).
        
        Args:
            memory_type: Type of memory system to get
            
        Returns:
            The requested memory system
            
        Raises:
            ValueError: If the memory type is not supported
        """
        if memory_type not in self._memory_systems:
            raise ValueError(f"Unsupported memory type: {memory_type}")
        
        return self._memory_systems[memory_type]
"""
