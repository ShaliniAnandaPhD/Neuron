"""
utils.py - Utility Functions and Helpers for Neuron Framework

This module provides various utility functions and helpers that are used 
throughout the Neuron framework, including serialization, validation, 
logging utilities, and common operations.
"""

import asyncio
import functools
import inspect
import json
import logging
import os
import signal
import sys
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')
R = TypeVar('R')


def setup_logging(log_level: str = "INFO", 
                log_file: Optional[str] = None,
                log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s") -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        log_format: Format string for log messages
    """
    # Convert log level string to constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure logging
    handlers = []
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # Add file handler if log file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format=log_format
    )
    
    logger.info(f"Logging configured with level {log_level}")


def generate_id() -> str:
    """
    Generate a unique ID.
    
    Returns:
        Unique ID string
    """
    return str(uuid.uuid4())


def current_timestamp() -> float:
    """
    Get the current timestamp.
    
    Returns:
        Current timestamp in seconds since epoch
    """
    return time.time()


def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp as a string.
    
    Args:
        timestamp: Timestamp in seconds since epoch
        format_str: Format string for strftime
        
    Returns:
        Formatted timestamp string
    """
    return time.strftime(format_str, time.localtime(timestamp))


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> float:
    """
    Parse a timestamp string to a timestamp.
    
    Args:
        timestamp_str: Timestamp string
        format_str: Format string for strptime
        
    Returns:
        Timestamp in seconds since epoch
        
    Raises:
        ValueError: If the timestamp string cannot be parsed
    """
    return time.mktime(time.strptime(timestamp_str, format_str))


def serialize_to_json(obj: Any, pretty: bool = False) -> str:
    """
    Serialize an object to JSON.
    
    Args:
        obj: Object to serialize
        pretty: Whether to format the JSON with indentation
        
    Returns:
        JSON string
        
    Raises:
        TypeError: If the object cannot be serialized to JSON
    """
    indent = 2 if pretty else None
    
    # Handle Enum values
    def enum_serializer(obj):
        if isinstance(obj, Enum):
            return obj.value
        raise TypeError(f"Type {type(obj)} not serializable")
    
    return json.dumps(obj, indent=indent, default=enum_serializer)


def deserialize_from_json(json_str: str) -> Any:
    """
    Deserialize an object from JSON.
    
    Args:
        json_str: JSON string
        
    Returns:
        Deserialized object
        
    Raises:
        json.JSONDecodeError: If the JSON string is invalid
    """
    return json.loads(json_str)


def serialize_to_file(obj: Any, file_path: Union[str, Path], pretty: bool = False) -> None:
    """
    Serialize an object to a JSON file.
    
    Args:
        obj: Object to serialize
        file_path: Path to the file
        pretty: Whether to format the JSON with indentation
        
    Raises:
        TypeError: If the object cannot be serialized to JSON
        OSError: If the file cannot be written
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w') as f:
        json_str = serialize_to_json(obj, pretty)
        f.write(json_str)


def deserialize_from_file(file_path: Union[str, Path]) -> Any:
    """
    Deserialize an object from a JSON file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Deserialized object
        
    Raises:
        json.JSONDecodeError: If the JSON is invalid
        FileNotFoundError: If the file does not exist
        OSError: If the file cannot be read
    """
    with open(file_path, 'r') as f:
        json_str = f.read()
        return deserialize_from_json(json_str)


def validate_type(value: Any, expected_type: Type[T]) -> T:
    """
    Validate that a value is of the expected type.
    
    Args:
        value: Value to validate
        expected_type: Expected type
        
    Returns:
        The value if it is of the expected type
        
    Raises:
        TypeError: If the value is not of the expected type
    """
    if not isinstance(value, expected_type):
        raise TypeError(f"Expected {expected_type.__name__}, got {type(value).__name__}")
    return value


def validate_range(value: Union[int, float], 
                 min_value: Optional[Union[int, float]] = None,
                 max_value: Optional[Union[int, float]] = None) -> Union[int, float]:
    """
    Validate that a numeric value is within a range.
    
    Args:
        value: Value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        
    Returns:
        The value if it is within the range
        
    Raises:
        ValueError: If the value is outside the range
    """
    if min_value is not None and value < min_value:
        raise ValueError(f"Value {value} is less than minimum {min_value}")
    
    if max_value is not None and value > max_value:
        raise ValueError(f"Value {value} is greater than maximum {max_value}")
    
    return value


def validate_not_none(value: Optional[T], name: str = "value") -> T:
    """
    Validate that a value is not None.
    
    Args:
        value: Value to validate
        name: Name of the value for the error message
        
    Returns:
        The value if it is not None
        
    Raises:
        ValueError: If the value is None
    """
    if value is None:
        raise ValueError(f"{name} cannot be None")
    return value


def safe_call(func: Callable[..., T], *args, **kwargs) -> Tuple[Optional[T], Optional[Exception]]:
    """
    Safely call a function, catching any exceptions.
    
    Args:
        func: Function to call
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Tuple of (result, exception), where exception is None if no exception was raised
    """
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        return None, e


def retry(max_attempts: int = 3, 
         delay: float = 1.0,
         backoff_factor: float = 2.0,
         exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts (seconds)
        backoff_factor: Factor to multiply delay by after each attempt
        exceptions: Tuple of exception types to catch and retry on
        
    Returns:
        Decorated function
    
    Example:
        @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        def fetch_data():
            # Function that might fail
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} for {func.__name__} failed: {e}. "
                        f"Retrying in {current_delay:.2f} seconds."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
        
        return wrapper
    
    return decorator


def async_retry(max_attempts: int = 3, 
              delay: float = 1.0,
              backoff_factor: float = 2.0,
              exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    """
    Decorator to retry an async function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts (seconds)
        backoff_factor: Factor to multiply delay by after each attempt
        exceptions: Tuple of exception types to catch and retry on
        
    Returns:
        Decorated function
    
    Example:
        @async_retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        async def fetch_data():
            # Async function that might fail
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} for {func.__name__} failed: {e}. "
                        f"Retrying in {current_delay:.2f} seconds."
                    )
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor
        
        return wrapper
    
    return decorator


def with_timeout(timeout: float) -> Callable:
    """
    Decorator to add a timeout to a function.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        Decorated function
    
    Example:
        @with_timeout(5.0)
        def long_running_function():
            # Function that might take too long
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result = [None]
            exception = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout)
            
            if thread.is_alive():
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout} seconds")
            
            if exception[0]:
                raise exception[0]
            
            return result[0]
        
        return wrapper
    
    return decorator


def async_with_timeout(timeout: float) -> Callable:
    """
    Decorator to add a timeout to an async function.
    
    Args:
        timeout: Timeout in seconds
        
    Returns:
        Decorated function
    
    Example:
        @async_with_timeout(5.0)
        async def long_running_function():
            # Async function that might take too long
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout} seconds")
        
        return wrapper
    
    return decorator


def measure_time(func: Callable[..., T]) -> Callable[..., Tuple[T, float]]:
    """
    Decorator to measure the execution time of a function.
    
    Args:
        func: Function to measure
        
    Returns:
        Decorated function that returns (result, elapsed_time)
    
    Example:
        @measure_time
        def my_function():
            # Function to measure
            pass
        
        result, elapsed = my_function()
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Tuple[T, float]:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        return result, elapsed_time
    
    return wrapper


def async_measure_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to measure the execution time of an async function.
    
    Args:
        func: Async function to measure
        
    Returns:
        Decorated function that returns (result, elapsed_time)
    
    Example:
        @async_measure_time
        async def my_function():
            # Async function to measure
            pass
        
        result, elapsed = await my_function()
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Tuple[Any, float]:
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        return result, elapsed_time
    
    return wrapper


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to memoize (cache) function results.
    
    Args:
        func: Function to memoize
        
    Returns:
        Decorated function
    
    Example:
        @memoize
        def expensive_function(x, y):
            # Expensive computation
            pass
    """
    cache = {}
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        # Create a key from the arguments
        key = str(args) + str(sorted(kwargs.items()))
        
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        
        return cache[key]
    
    # Add a method to clear the cache
    wrapper.clear_cache = lambda: cache.clear()
    
    return wrapper


def log_exceptions(logger_instance: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator to log exceptions raised by a function.
    
    Args:
        logger_instance: Logger to use, or None to use the module logger
        
    Returns:
        Decorated function
    
    Example:
        @log_exceptions()
        def my_function():
            # Function that might raise exceptions
            pass
    """
    log = logger_instance or logger
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.exception(f"Exception in {func.__name__}: {e}")
                raise
        
        return wrapper
    
    return decorator


def async_log_exceptions(logger_instance: Optional[logging.Logger] = None) -> Callable:
    """
    Decorator to log exceptions raised by an async function.
    
    Args:
        logger_instance: Logger to use, or None to use the module logger
        
    Returns:
        Decorated function
    
    Example:
        @async_log_exceptions()
        async def my_function():
            # Async function that might raise exceptions
            pass
    """
    log = logger_instance or logger
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log.exception(f"Exception in {func.__name__}: {e}")
                raise
        
        return wrapper
    
    return decorator


@contextmanager
def capture_exceptions() -> None:
    """
    Context manager to capture and log exceptions.
    
    Example:
        with capture_exceptions():
            # Code that might raise exceptions
            pass
    """
    try:
        yield
    except Exception as e:
        logger.exception(f"Captured exception: {e}")
        raise


@contextmanager
def temporary_attribute(obj: Any, attribute: str, value: Any) -> None:
    """
    Context manager to temporarily set an attribute on an object.
    
    Args:
        obj: Object to modify
        attribute: Attribute name
        value: Temporary value
    
    Example:
        with temporary_attribute(my_object, 'attribute', 'temporary_value'):
            # Code using the temporary attribute
            pass
    """
    original = getattr(obj, attribute, None)
    setattr(obj, attribute, value)
    try:
        yield
    finally:
        if original is None:
            delattr(obj, attribute)
        else:
            setattr(obj, attribute, original)


def run_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Run an async function in the current event loop.
    
    If no event loop is running, a new one is created.
    
    Args:
        func: Async function to run
        
    Returns:
        Function that runs the async function and returns its result
    
    Example:
        @run_async
        async def my_async_function():
            # Async code
            pass
        
        result = my_async_function()  # No need for await
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Create a new loop for this call
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(func(*args, **kwargs))
            finally:
                new_loop.close()
        else:
            return loop.run_until_complete(func(*args, **kwargs))
    
    return wrapper


def is_async(func: Callable) -> bool:
    """
    Check if a function is asynchronous.
    
    Args:
        func: Function to check
        
    Returns:
        True if the function is asynchronous, False otherwise
    """
    return inspect.iscoroutinefunction(func) or inspect.isawaitable(func)


def to_async(func: Callable[..., T]) -> Callable[..., Any]:
    """
    Convert a synchronous function to an asynchronous one.
    
    Args:
        func: Synchronous function
        
    Returns:
        Asynchronous function
    
    Example:
        sync_func = lambda x: x * 2
        async_func = to_async(sync_func)
        result = await async_func(5)  # Returns 10
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return func(*args, **kwargs)
    
    return wrapper


def to_sync(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Convert an asynchronous function to a synchronous one.
    
    Args:
        func: Asynchronous function
        
    Returns:
        Synchronous function
    
    Example:
        async def async_func(x):
            return x * 2
            
        sync_func = to_sync(async_func)
        result = sync_func(5)  # Returns 10, no await needed
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        return run_async(func)(*args, **kwargs)
    
    return wrapper


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deeply merge two dictionaries.
    
    The second dictionary takes precedence when there are conflicts.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Key of the parent dictionary
        separator: Separator for keys
        
    Returns:
        Flattened dictionary
    
    Example:
        flatten_dict({'a': {'b': 1, 'c': 2}, 'd': 3})
        # Returns {'a.b': 1, 'a.c': 2, 'd': 3}
    """
    items = []
    for key, value in d.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(d: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    Unflatten a flattened dictionary.
    
    Args:
        d: Flattened dictionary
        separator: Separator for keys
        
    Returns:
        Nested dictionary
    
    Example:
        unflatten_dict({'a.b': 1, 'a.c': 2, 'd': 3})
        # Returns {'a': {'b': 1, 'c': 2}, 'd': 3}
    """
    result = {}
    
    for key, value in d.items():
        parts = key.split(separator)
        
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


def get_nested_value(d: Dict[str, Any], key_path: str, separator: str = '.', default: Any = None) -> Any:
    """
    Get a value from a nested dictionary using a key path.
    
    Args:
        d: Dictionary to get the value from
        key_path: Path to the key, separated by separator
        separator: Separator for keys
        default: Default value if the key doesn't exist
        
    Returns:
        Value at the key path, or default if not found
    
    Example:
        get_nested_value({'a': {'b': {'c': 42}}}, 'a.b.c')  # Returns 42
    """
    parts = key_path.split(separator)
    current = d
    
    try:
        for part in parts:
            current = current[part]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(d: Dict[str, Any], key_path: str, value: Any, separator: str = '.') -> Dict[str, Any]:
    """
    Set a value in a nested dictionary using a key path.
    
    Args:
        d: Dictionary to set the value in
        key_path: Path to the key, separated by separator
        value: Value to set
        separator: Separator for keys
        
    Returns:
        Modified dictionary
    
    Example:
        set_nested_value({'a': {'b': {}}}, 'a.b.c', 42)
        # Returns {'a': {'b': {'c': 42}}}
    """
    parts = key_path.split(separator)
    current = d
    
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]
    
    current[parts[-1]] = value
    return d


def get_thread_stack_traces() -> Dict[int, str]:
    """
    Get stack traces for all threads.
    
    Returns:
        Dictionary mapping thread IDs to stack traces
    """
    traces = {}
    for thread_id, frame in sys._current_frames().items():
        trace = ''.join(traceback.format_stack(frame))
        traces[thread_id] = trace
    
    return traces


def log_thread_stack_traces(log_level: int = logging.INFO) -> None:
    """
    Log stack traces for all threads.
    
    Args:
        log_level: Logging level
    """
    traces = get_thread_stack_traces()
    
    for thread_id, trace in traces.items():
        thread_name = None
        for thread in threading.enumerate():
            if thread.ident == thread_id:
                thread_name = thread.name
                break
        
        identifier = f"{thread_name} ({thread_id})" if thread_name else f"Thread-{thread_id}"
        logger.log(log_level, f"Stack trace for thread {identifier}:\n{trace}")


def register_signal_handler(sig: signal.Signals, handler: Callable[[int, Any], None]) -> None:
    """
    Register a signal handler.
    
    Args:
        sig: Signal to handle
        handler: Signal handler function
    
    Example:
        def handle_sigterm(signum, frame):
            print("Received SIGTERM")
            
        register_signal_handler(signal.SIGTERM, handle_sigterm)
    """
    try:
        signal.signal(sig, handler)
    except (ValueError, OSError):
        logger.warning(f"Failed to register signal handler for {sig.name}")


@contextmanager
def open_atomic(file_path: Union[str, Path], mode: str = 'w', **kwargs) -> None:
    """
    Context manager for atomic file operations.
    
    This writes to a temporary file and then renames it to the target file,
    which is an atomic operation on most file systems.
    
    Args:
        file_path: Path to the file
        mode: File mode
        **kwargs: Additional arguments for open()
    
    Example:
        with open_atomic('data.txt', 'w') as f:
            f.write('Hello, world!')
    """
    file_path = Path(file_path)
    temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
    
    try:
        with open(temp_path, mode, **kwargs) as f:
            yield f
        
        # Ensure the file is flushed to disk
        os.fsync(f.fileno())
        
        # Atomic rename
        os.replace(temp_path, file_path)
    except Exception:
        # Clean up the temporary file
        if temp_path.exists():
            temp_path.unlink()
        raise


def chunked_iterable(iterable, chunk_size: int):
    """
    Break an iterable into chunks.
    
    Args:
        iterable: Iterable to chunk
        chunk_size: Size of each chunk
        
    Yields:
        Chunks of the iterable
    
    Example:
        for chunk in chunked_iterable(range(10), 3):
            print(chunk)
        # Prints: [0, 1, 2], [3, 4, 5], [6, 7, 8], [9]
    """
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    
    if chunk:
        yield chunk


def exponential_backoff(base_delay: float = 1.0, 
                      max_delay: float = 60.0,
                      factor: float = 2.0) -> Callable[[], float]:
    """
    Create a generator for exponential backoff delays.
    
    Args:
        base_delay: Initial delay
        max_delay: Maximum delay
        factor: Multiplication factor for each step
        
    Returns:
        Function that returns the next delay
    
    Example:
        backoff = exponential_backoff()
        delay = backoff()  # Initial delay
        delay = backoff()  # Next delay
    """
    attempt = 0
    
    def next_delay() -> float:
        nonlocal attempt
        delay = min(base_delay * (factor ** attempt), max_delay)
        attempt += 1
        return delay
    
    return next_delay


def rate_limit(calls: int, period: float) -> Callable:
    """
    Decorator for rate limiting a function.
    
    Args:
        calls: Maximum number of calls
        period: Time period in seconds
        
    Returns:
        Decorated function
    
    Example:
        @rate_limit(5, 60)  # 5 calls per minute
        def rate_limited_function():
            # Function call that should be rate limited
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Call history: list of timestamps
        history = []
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            nonlocal history
            now = time.time()
            
            # Remove expired calls from history
            cutoff = now - period
            history = [t for t in history if t >= cutoff]
            
            # Check rate limit
            if len(history) >= calls:
                raise RuntimeError(f"Rate limit exceeded: {calls} calls per {period} seconds")
            
            # Add this call to history
            history.append(now)
            
            # Call the function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def async_rate_limit(calls: int, period: float) -> Callable:
    """
    Decorator for rate limiting an async function.
    
    Args:
        calls: Maximum number of calls
        period: Time period in seconds
        
    Returns:
        Decorated function
    
    Example:
        @async_rate_limit(5, 60)  # 5 calls per minute
        async def rate_limited_function():
            # Async function call that should be rate limited
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Call history: list of timestamps
        history = []
        lock = asyncio.Lock()
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            nonlocal history
            now = time.time()
            
            async with lock:
                # Remove expired calls from history
                cutoff = now - period
                history = [t for t in history if t >= cutoff]
                
                # Check rate limit
                if len(history) >= calls:
                    raise RuntimeError(f"Rate limit exceeded: {calls} calls per {period} seconds")
                
                # Add this call to history
                history.append(now)
            
            # Call the function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def timer(message: Optional[str] = None, 
        logger_instance: Optional[logging.Logger] = None,
        log_level: int = logging.INFO) -> Callable:
    """
    Decorator to time a function and log the elapsed time.
    
    Args:
        message: Optional message to include in the log
        logger_instance: Logger to use, or None to use the module logger
        log_level: Logging level
        
    Returns:
        Decorated function
    
    Example:
        @timer("Processing data")
        def process_data():
            # Function to time
            pass
    """
    log = logger_instance or logger
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            msg = message or f"Executing {func.__name__}"
            
            log.log(log_level, f"{msg}...")
            start_time = time.time()
            
            result = func(*args, **kwargs)
            
            elapsed = time.time() - start_time
            log.log(log_level, f"{msg} completed in {elapsed:.3f} seconds")
            
            return result
        
        return wrapper
    
    return decorator


def async_timer(message: Optional[str] = None, 
              logger_instance: Optional[logging.Logger] = None,
              log_level: int = logging.INFO) -> Callable:
    """
    Decorator to time an async function and log the elapsed time.
    
    Args:
        message: Optional message to include in the log
        logger_instance: Logger to use, or None to use the module logger
        log_level: Logging level
        
    Returns:
        Decorated function
    
    Example:
        @async_timer("Processing data")
        async def process_data():
            # Async function to time
            pass
    """
    log = logger_instance or logger
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            msg = message or f"Executing {func.__name__}"
            
            log.log(log_level, f"{msg}...")
            start_time = time.time()
            
            result = await func(*args, **kwargs)
            
            elapsed = time.time() - start_time
            log.log(log_level, f"{msg} completed in {elapsed:.3f} seconds")
            
            return result
        
        return wrapper
    
    return decorator
"""
