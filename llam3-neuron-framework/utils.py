#!/usr/bin/env python3
"""
Utility Functions and Classes for LLaMA3 Neuron Framework
Common utilities used throughout the system
"""

import asyncio
import time
import json
import hashlib
import re
import logging
import threading
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from functools import wraps
from contextlib import asynccontextmanager
from enum import Enum

# ============================================================================
# MOCK CONFIG (to make the script self-contained)
# ============================================================================

# In a real application, these would be in a separate 'config.py' file.
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30  # seconds

def get_logger(name: str) -> logging.Logger:
    """Creates and configures a logger."""
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# TYPE VARIABLES
# ============================================================================

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# ============================================================================
# CIRCUIT BREAKER
# ============================================================================

class CircuitBreakerError(Exception):
    """Raised when the circuit breaker is open and preventing calls."""
    pass

class CircuitBreakerState(Enum):
    """Enumeration for circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """
    Implements the circuit breaker pattern for fault tolerance in services.
    It prevents an application from repeatedly trying to execute an operation
    that is likely to fail.
    """

    def __init__(self,
                 failure_threshold: int = CIRCUIT_BREAKER_THRESHOLD,
                 recovery_timeout: int = CIRCUIT_BREAKER_TIMEOUT,
                 expected_exception: type = Exception):
        """
        Initializes the CircuitBreaker.

        Args:
            failure_threshold: The number of failures required to open the circuit.
            recovery_timeout: The time in seconds to wait before moving to HALF_OPEN.
            expected_exception: The type of exception to count as a failure.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = CircuitBreakerState.CLOSED
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """
        Executes the given function, wrapped by the circuit breaker logic.

        Args:
            func: The asynchronous or synchronous function to call.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.

        Returns:
            The result of the function call.

        Raises:
            CircuitBreakerError: If the circuit is currently open.
            Exception: The original exception from the failed function call.
        """
        async with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker is now HALF_OPEN. Attempting a trial call.")
                else:
                    raise CircuitBreakerError("Circuit breaker is open")

        # The function call itself is outside the lock to avoid blocking
        # other calls during a potentially long-running operation.
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # If the call was successful, reset the breaker.
            await self._on_success()
            return result
            
        except self.expected_exception as e:
            # If the call failed, record the failure.
            await self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Checks if the recovery timeout has passed, allowing a reset attempt."""
        return (
            self._last_failure_time is not None and
            time.time() - self._last_failure_time >= self.recovery_timeout
        )

    async def _on_success(self):
        """Handles a successful call, closing the circuit."""
        async with self._lock:
            if self._state == CircuitBreakerState.HALF_OPEN:
                logger.info("Trial call successful. Circuit breaker is now CLOSED.")
            self._failure_count = 0
            self._state = CircuitBreakerState.CLOSED
            self._last_failure_time = None

    async def _on_failure(self):
        """Handles a failed call, incrementing failure count and potentially opening the circuit."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitBreakerState.HALF_OPEN or self._failure_count >= self.failure_threshold:
                self._state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker opened after {self._failure_count} failures.")

    @property
    def state(self) -> str:
        """Gets the current state of the circuit breaker."""
        return self._state.value
    
    @property
    def is_open(self) -> bool:
        """Checks if the circuit is open."""
        return self._state == CircuitBreakerState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Checks if the circuit is closed."""
        return self._state == CircuitBreakerState.CLOSED

# ============================================================================
# CACHE
# ============================================================================

class Cache(Generic[T]):
    """
    A simple asynchronous in-memory cache with LRU (Least Recently Used) eviction
    policy and TTL (Time-To-Live) support.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initializes the cache.
        
        Args:
            max_size: The maximum number of items to store in the cache.
            ttl_seconds: The default time-to-live for cache entries in seconds.
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[T]:
        """
        Retrieves an item from the cache. Returns None if the item is not found
        or has expired.
        
        Args:
            key: The key of the item to retrieve.
            
        Returns:
            The cached value, or None if not found or expired.
        """
        async with self._lock:
            if key not in self._cache:
                return None
            
            value, expiry_time = self._cache[key]
            
            # Check for expiration
            if time.time() > expiry_time:
                del self._cache[key]
                return None
            
            # Move to end to mark as recently used
            self._cache.move_to_end(key)
            return value
    
    async def set(self, key: str, value: T, ttl: Optional[int] = None):
        """
        Adds or updates an item in the cache.
        
        Args:
            key: The key of the item to set.
            value: The value to cache.
            ttl: An optional override for the default TTL for this specific item.
        """
        async with self._lock:
            # Evict the oldest item if the cache is full
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
            
            expiry_time = time.time() + (ttl or self.ttl_seconds)
            self._cache[key] = (value, expiry_time)
            self._cache.move_to_end(key)
    
    async def delete(self, key: str) -> bool:
        """
        Deletes an item from the cache.
        
        Args:
            key: The key of the item to delete.
            
        Returns:
            True if the item was deleted, False if it was not found.
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self):
        """Clears all items from the cache."""
        async with self._lock:
            self._cache.clear()
    
    async def size(self) -> int:
        """Returns the current number of items in the cache."""
        async with self._lock:
            return len(self._cache)

# ============================================================================
# METRICS
# ============================================================================

class Metrics:
    """A simple thread-safe and async-safe metrics collector."""
    
    def __init__(self, namespace: str):
        """
        Initializes the metrics collector.
        
        Args:
            namespace: A prefix for all metric names.
        """
        self.namespace = namespace
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.Lock() # For thread-safety in sync methods
    
    async def increment(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increments a counter asynchronously."""
        key = self._make_key(name, labels)
        async with self._async_lock:
            self._counters[key] += value
    
    async def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Sets a gauge value asynchronously."""
        key = self._make_key(name, labels)
        async with self._async_lock:
            self._gauges[key] = value
    
    async def record(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Records a value in a histogram asynchronously."""
        key = self._make_key(name, labels)
        async with self._async_lock:
            self._histograms[key].append(value)
            # Optional: cap the histogram size
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def increment_sync(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """Increments a counter synchronously and thread-safely."""
        key = self._make_key(name, labels)
        with self._sync_lock:
            self._counters[key] += value
    
    def record_sync(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Records a value in a histogram synchronously and thread-safely."""
        key = self._make_key(name, labels)
        with self._sync_lock:
            self._histograms[key].append(value)
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Creates a unique metric key from a name and labels."""
        if not labels:
            return f"{self.namespace}.{name}"
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{self.namespace}.{name}{{{label_str}}}"
    
    async def get_all(self) -> Dict[str, Any]:
        """Retrieves a snapshot of all current metrics."""
        async with self._async_lock:
            # Create a deep copy to avoid race conditions during iteration
            histograms_copy = self._histograms.copy()
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: {
                        "count": len(v),
                        "sum": sum(v),
                        "min": min(v) if v else 0,
                        "max": max(v) if v else 0,
                        "avg": sum(v) / len(v) if v else 0
                    }
                    for k, v in histograms_copy.items()
                }
            }

# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """
    An asynchronous token bucket rate limiter.
    """
    
    def __init__(self, rate: int, capacity: int):
        """
        Initializes the rate limiter.
        
        Args:
            rate: The number of tokens to add to the bucket per second.
            capacity: The maximum number of tokens the bucket can hold.
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Tries to acquire a number of tokens from the bucket.
        
        Args:
            tokens: The number of tokens to acquire.
            
        Returns:
            True if tokens were acquired, False otherwise.
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_and_acquire(self, tokens: int = 1):
        """
        Waits until the required number of tokens are available, then acquires them.
        
        Args:
            tokens: The number of tokens to acquire.
        """
        while not await self.acquire(tokens):
            async with self._lock:
                tokens_needed = tokens - self.tokens
                wait_time = max(0, tokens_needed / self.rate)
            await asyncio.sleep(wait_time)

# ============================================================================
# RETRY DECORATOR
# ============================================================================

def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    A decorator for retrying an async function with exponential backoff.
    
    Args:
        max_attempts: The maximum number of attempts.
        delay: The initial delay between retries in seconds.
        backoff: The multiplier for the delay after each retry.
        exceptions: A tuple of exception types to catch and trigger a retry.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.2f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}.")
            
            raise last_exception
        
        return wrapper
    return decorator

# ============================================================================
# TIMING UTILITIES
# ============================================================================

class Timer:
    """A context manager for timing synchronous operations."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if self.start_time:
            self.elapsed = self.end_time - self.start_time
            logger.debug(f"{self.name} took {self.elapsed:.3f} seconds")
    
    @property
    def elapsed_ms(self) -> float:
        """Returns the elapsed time in milliseconds."""
        return (self.elapsed * 1000) if self.elapsed is not None else 0.0

@asynccontextmanager
async def async_timer(name: str = "Operation"):
    """An async context manager for timing asynchronous operations."""
    start_time = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start_time
        logger.debug(f"{name} took {elapsed:.3f} seconds")

# ============================================================================
# JSON UTILITIES
# ============================================================================

class JSONEncoder(json.JSONEncoder):
    """
    Enhanced JSON encoder that handles additional types like datetime,
    timedelta, and objects with a to_dict() method.
    """
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        if hasattr(obj, 'to_dict') and callable(obj.to_dict):
            return obj.to_dict()
        return super().default(obj)

def json_dumps(obj: Any, **kwargs) -> str:
    """Serializes an object to a JSON string using the custom encoder."""
    return json.dumps(obj, cls=JSONEncoder, **kwargs)

def json_loads(s: str, **kwargs) -> Any:
    """Deserializes a JSON string, with standardized error handling."""
    try:
        return json.loads(s, **kwargs)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise

# ============================================================================
# HASHING UTILITIES
# ============================================================================

def generate_hash(data: Any, algorithm: str = 'sha256') -> str:
    """
    Generates a hash for the given data.
    
    Args:
        data: The data to hash (can be string, bytes, or JSON-serializable).
        algorithm: The hash algorithm to use (e.g., 'sha256', 'md5').
        
    Returns:
        The hex digest of the hash.
    """
    if not isinstance(data, bytes):
        data_str = json_dumps(data, sort_keys=True) if not isinstance(data, str) else data
        data = data_str.encode('utf-8')
    
    hasher = hashlib.new(algorithm)
    hasher.update(data)
    return hasher.hexdigest()

def generate_cache_key(*args, **kwargs) -> str:
    """
    Generates a consistent cache key from function arguments.
    
    Args:
        *args: Positional arguments.
        **kwargs: Keyword arguments.
        
    Returns:
        A stable SHA256 hash to be used as a cache key.
    """
    key_data = {'args': args, 'kwargs': sorted(kwargs.items())}
    return generate_hash(key_data)

# ============================================================================
# BATCHING UTILITIES
# ============================================================================

class BatchProcessor(Generic[T]):
    """
    Collects items into batches and processes them together, either when the
    batch is full or a timeout is reached.
    """
    
    def __init__(self,
                 process_func: Callable[[List[T]], Any],
                 batch_size: int = 10,
                 timeout: float = 1.0):
        """
        Initializes the batch processor.
        
        Args:
            process_func: The async function to call with a batch of items.
            batch_size: The maximum number of items in a batch.
            timeout: The max time in seconds to wait before processing a partial batch.
        """
        self.process_func = process_func
        self.batch_size = batch_size
        self.timeout = timeout
        
        self._batch: List[T] = []
        self._futures: List[asyncio.Future] = []
        self._lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task] = None
    
    async def add(self, item: T) -> Any:
        """
        Adds an item to the current batch and returns a future that will
        be resolved with the processing result.
        
        Args:
            item: The item to add to the batch.
            
        Returns:
            A future that resolves to the result of the batch processing.
        """
        future = asyncio.get_running_loop().create_future()
        
        async with self._lock:
            self._batch.append(item)
            self._futures.append(future)
            
            # Start the timeout timer if it's not already running
            if not self._timer_task or self._timer_task.done():
                self._timer_task = asyncio.create_task(self._timeout_handler())
            
            # If the batch is now full, process it immediately
            if len(self._batch) >= self.batch_size:
                await self._process_batch()
        
        return await future
    
    async def _timeout_handler(self):
        """Waits for the timeout and then triggers batch processing."""
        await asyncio.sleep(self.timeout)
        async with self._lock:
            if self._batch: # Check if batch wasn't processed already
                await self._process_batch()
    
    async def _process_batch(self):
        """Processes the current batch of items."""
        # Cancel the timeout task as it's no longer needed for this batch
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        
        if not self._batch:
            return
        
        # Make a copy of the batch and futures to work with
        batch = self._batch[:]
        futures = self._futures[:]
        
        # Clear the instance variables for the next batch
        self._batch.clear()
        self._futures.clear()
        
        try:
            if asyncio.iscoroutinefunction(self.process_func):
                results = await self.process_func(batch)
            else:
                # Allow sync functions too, run in executor for safety
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(None, self.process_func, batch)
            
            # Distribute results to the corresponding futures
            if isinstance(results, list) and len(results) == len(futures):
                for future, result in zip(futures, results):
                    if not future.done(): future.set_result(result)
            else:
                # If a single result is returned, apply it to all futures
                for future in futures:
                    if not future.done(): future.set_result(results)
                    
        except Exception as e:
            # If processing fails, propagate the exception to all futures
            logger.error(f"Batch processing failed: {e}")
            for future in futures:
                if not future.done(): future.set_exception(e)

# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

# Compile regex patterns once for efficiency
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
URL_PATTERN = re.compile(
    r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
)

def validate_email(email: str) -> bool:
    """Validates an email address format."""
    return bool(EMAIL_PATTERN.match(email))

def validate_url(url: str) -> bool:
    """Validates a URL format."""
    return bool(URL_PATTERN.match(url))

def validate_json(data: str) -> bool:
    """Validates if a string is valid JSON."""
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False

# ============================================================================
# ASYNC UTILITIES
# ============================================================================

async def gather_with_concurrency(n: int, *coros):
    """
    Runs coroutines concurrently with a specified limit on how many can run at once.
    
    Args:
        n: The maximum number of coroutines to run at the same time.
        *coros: The coroutines to run.
        
    Returns:
        A list of results from the coroutines.
    """
    semaphore = asyncio.Semaphore(n)
    
    async def sem_coro(coro):
        async with semaphore:
            return await coro
    
    return await asyncio.gather(*(sem_coro(c) for c in coros))

async def run_with_timeout(coro, timeout: float, default=None):
    """
    Runs a coroutine with a timeout.
    
    Args:
        coro: The coroutine to run.
        timeout: The timeout in seconds.
        default: The value to return if a timeout occurs.
        
    Returns:
        The result of the coroutine or the default value on timeout.
    """
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Coroutine timed out after {timeout}s")
        return default

# ============================================================================
# STRING UTILITIES
# ============================================================================

def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncates a string to a maximum length, adding a suffix if truncated.
    
    Args:
        s: The string to truncate.
        max_length: The maximum desired length of the output string.
        suffix: The suffix to append if the string is cut.
        
    Returns:
        The truncated string.
    """
    if len(s) <= max_length:
        return s
    
    truncate_at = max_length - len(suffix)
    return s[:truncate_at] + suffix

def sanitize_string(s: str) -> str:
    """
    Sanitizes a string by removing control characters and normalizing whitespace.
    
    Args:
        s: The string to sanitize.
        
    Returns:
        The sanitized string.
    """
    # Remove ASCII control characters
    s = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', s)
    # Normalize whitespace (replace multiple spaces/newlines with a single space)
    s = ' '.join(s.split())
    return s.strip()

# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    'CircuitBreaker',
    'CircuitBreakerError',
    'Cache',
    'Metrics',
    'RateLimiter',
    'async_retry',
    'Timer',
    'async_timer',
    'JSONEncoder',
    'json_dumps',
    'json_loads',
    'generate_hash',
    'generate_cache_key',
    'BatchProcessor',
    'validate_email',
    'validate_url',
    'validate_json',
    'gather_with_concurrency',
    'run_with_timeout',
    'truncate_string',
    'sanitize_string',
]
