"""
Trace Logger Module for Neuron Architecture

Records detailed execution paths, agent decisions, and memory
operations for debugging and analysis.

"""

import json
import time
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Callable
from datetime import datetime
import threading
import queue

logger = logging.getLogger(__name__)

class TraceLogger:
    """
    Logs detailed execution traces for debugging, analysis,
    and visualization of circuit execution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the trace logger with configuration parameters.
        
        Args:
            config: Configuration for logging
        """
        # Basic configuration
        self.enabled = config.get("trace_enabled", True)
        self.log_dir = Path(config.get("trace_log_dir", "./logs/traces"))
        self.max_events_per_trace = config.get("max_events_per_trace", 10000)
        self.flush_interval = config.get("flush_interval", 10)  # seconds
        self.compression_enabled = config.get("compression_enabled", True)
        self.compress_after = config.get("compress_after", 86400)  # 1 day
        self.min_log_level = config.get("min_log_level", "DEBUG")
        
        # Detail level configuration
        self.log_data_content = config.get("log_data_content", False)  # Whether to log data content or just metadata
        self.max_data_size = config.get("max_data_size", 1024)  # Max bytes for data content
        self.include_system_info = config.get("include_system_info", True)
        self.event_sampling_rate = config.get("event_sampling_rate", 1.0)  # 1.0 = log everything
        
        # Retention configuration
        self.max_traces = config.get("max_traces", 1000)
        self.max_trace_age = config.get("max_trace_age", 30 * 86400)  # 30 days
        self.auto_prune = config.get("auto_prune", True)
        
        # Create log directory if it doesn't exist
        if self.enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
        # Initialize trace state
        self._init_trace_state()
        
        # Set up async logging if configured
        self.async_logging = config.get("async_logging", False)
        if self.async_logging and self.enabled:
            self._setup_async_logging()
            
        logger.info(f"Initialized TraceLogger (enabled={self.enabled}, "
                  f"dir={self.log_dir}, async={self.async_logging})")
    
    def _init_trace_state(self) -> None:
        """Initialize or reset trace state."""
        self.current_trace: Optional[Dict[str, Any]] = None
        self.trace_stack: List[Dict[str, Any]] = []
        self.event_counter = 0
        self.current_span: Optional[Dict[str, Any]] = None
        self.span_stack: List[Dict[str, Any]] = []
        self.last_flush_time = time.time()
        self._trace_lock = threading.RLock()
    
    def _setup_async_logging(self) -> None:
        """Set up asynchronous logging thread and queue."""
        self._log_queue = queue.Queue()
        self._stop_logging = threading.Event()
        self._log_thread = threading.Thread(target=self._async_logger, daemon=True)
        self._log_thread.start()
        logger.debug("Started asynchronous logging thread")
    
    def _async_logger(self) -> None:
        """Background thread for asynchronous logging."""
        while not self._stop_logging.is_set():
            try:
                # Get item from queue with timeout
                item = self._log_queue.get(timeout=0.5)
                
                if item["type"] == "event":
                    trace_id = item["trace_id"]
                    event = item["event"]
                    self._append_event_to_file(trace_id, event)
                elif item["type"] == "trace_end":
                    trace = item["trace"]
                    self._write_trace_to_file(trace)
                
                self._log_queue.task_done()
            except queue.Empty:
                # Check if we need to prune old traces
                if self.auto_prune and time.time() - self.last_flush_time > 3600:  # Every hour
                    self._prune_old_traces()
                    self.last_flush_time = time.time()
            except Exception as e:
                logger.error(f"Error in async logger: {e}")
    
    def start_trace(self, metadata: Dict[str, Any]) -> str:
        """
        Start a new execution trace with the given metadata.
        
        Args:
            metadata: Information about the trace context
            
        Returns:
            trace_id: ID of the new trace
        """
        if not self.enabled:
            return ""
            
        with self._trace_lock:
            # Push current trace to stack if it exists
            if self.current_trace is not None:
                self.trace_stack.append(self.current_trace)
            
            # Generate trace ID
            trace_id = str(uuid.uuid4())
            
            # Create new trace
            self.current_trace = {
                "trace_id": trace_id,
                "start_time": time.time(),
                "events": [],
                "metadata": metadata.copy(),
                "spans": [],
                "status": "running"
            }
            
            # Add system info if configured
            if self.include_system_info:
                self.current_trace["system_info"] = self._collect_system_info()
                
            # Reset event counter
            self.event_counter = 0
            
            logger.debug(f"Started trace {trace_id}")
            return trace_id
    
    def end_trace(self, status: str = "completed", 
                 result: Optional[Dict[str, Any]] = None) -> str:
        """
        End the current trace and save it to disk.
        
        Args:
            status: Final status of the execution
            result: Optional result data
            
        Returns:
            trace_path: Path where trace was saved
        """
        if not self.enabled or self.current_trace is None:
            return ""
            
        with self._trace_lock:
            # Close any open spans
            while self.span_stack:
                self.end_span("auto_closed")
                
            # Update trace with end info
            self.current_trace["end_time"] = time.time()
            self.current_trace["duration"] = self.current_trace["end_time"] - self.current_trace["start_time"]
            self.current_trace["status"] = status
            self.current_trace["event_count"] = self.event_counter
            
            if result:
                if self.log_data_content:
                    self.current_trace["result"] = self._truncate_data(result)
                else:
                    self.current_trace["result"] = {"type": str(type(result).__name__)}
            
            # Get trace info for return
            trace_id = self.current_trace["trace_id"]
            trace_file = self.log_dir / f"{trace_id}.json"
            
            # Save trace to disk
            if self.async_logging:
                self._log_queue.put({
                    "type": "trace_end",
                    "trace": self.current_trace
                })
            else:
                self._write_trace_to_file(self.current_trace)
                
            # Restore previous trace if it exists
            if self.trace_stack:
                self.current_trace = self.trace_stack.pop()
            else:
                self.current_trace = None
                
            logger.debug(f"Ended trace {trace_id}, saved to {trace_file}")
            return str(trace_file)
    
    def _write_trace_to_file(self, trace: Dict[str, Any]) -> None:
        """
        Write a complete trace to disk.
        
        Args:
            trace: Trace data to write
        """
        try:
            trace_id = trace["trace_id"]
            trace_file = self.log_dir / f"{trace_id}.json"
            
            with open(trace_file, 'w') as f:
                json.dump(trace, f, indent=2)
                
            # Prune old traces if needed
            if self.auto_prune:
                self._prune_old_traces()
                
        except Exception as e:
            logger.error(f"Error writing trace to file: {e}")
    
    def log_event(self, event_type: str, component_id: str, 
                 data: Dict[str, Any]) -> None:
        """
        Log an event in the current trace.
        
        Args:
            event_type: Type of event (agent_call, memory_access, etc.)
            component_id: ID of the component generating the event
            data: Event data
        """
        if not self.enabled or self.current_trace is None:
            return
            
        # Apply sampling rate - skip some events if configured
        if self.event_sampling_rate < 1.0 and self.event_sampling_rate > 0:
            if event_type not in ('error', 'warning') and random.random() > self.event_sampling_rate:
                return
                
        with self._trace_lock:
            # Check if we've hit the max events limit
            if self.event_counter >= self.max_events_per_trace:
                if self.event_counter == self.max_events_per_trace:
                    # Log a special event indicating we're now dropping events
                    truncation_event = {
                        "event_id": str(uuid.uuid4()),
                        "event_type": "trace_truncated",
                        "component_id": "trace_logger",
                        "timestamp": time.time(),
                        "sequence": self.event_counter,
                        "data": {"message": f"Trace truncated at {self.max_events_per_trace} events"}
                    }
                    
                    if self.current_span:
                        truncation_event["span_id"] = self.current_span["span_id"]
                        
                    self.current_trace["events"].append(truncation_event)
                    self.event_counter += 1
                    
                return
                
            # Create event record
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "component_id": component_id,
                "timestamp": time.time(),
                "sequence": self.event_counter
            }
            
            # Add span ID if in a span
            if self.current_span:
                event["span_id"] = self.current_span["span_id"]
                
            # Add data with truncation if needed
            if self.log_data_content:
                event["data"] = self._truncate_data(data)
            else:
                # Just record the data type
                event["data_type"] = str(type(data).__name__)
                
            # Increment event counter
            self.event_counter += 1
                
            # Add to trace events or write directly if async
            if self.async_logging:
                self._log_queue.put({
                    "type": "event",
                    "trace_id": self.current_trace["trace_id"],
                    "event": event
                })
            else:
                self.current_trace["events"].append(event)
                
                # Flush to disk periodically if we have many events
                if self.event_counter % 1000 == 0 or time.time() - self.last_flush_time > self.flush_interval:
                    self._flush_events()
    
    def _append_event_to_file(self, trace_id: str, event: Dict[str, Any]) -> None:
        """
        Append a single event to a trace file without loading the whole file.
        
        Args:
            trace_id: ID of the trace
            event: Event data to append
        """
        try:
            trace_file = self.log_dir / f"{trace_id}.json"
            
            # If file doesn't exist yet, we need to create it
            if not trace_file.exists():
                # We need the current trace data
                if self.current_trace and self.current_trace["trace_id"] == trace_id:
                    trace_data = self.current_trace.copy()
                    trace_data["events"] = [event]
                    
                    with open(trace_file, 'w') as f:
                        json.dump(trace_data, f)
                    return
                else:
                    # Can't append to non-existent file
                    logger.warning(f"Cannot append event to non-existent trace file: {trace_id}")
                    return
            
            # Read the file to get current content
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
                
            # Append the event and write back
            trace_data["events"].append(event)
            trace_data["event_count"] = len(trace_data["events"])
            
            with open(trace_file, 'w') as f:
                json.dump(trace_data, f)
                
        except Exception as e:
            logger.error(f"Error appending event to trace file: {e}")
    
    def _flush_events(self) -> None:
        """Flush current events to disk."""
        if not self.enabled or self.current_trace is None:
            return
            
        try:
            trace_id = self.current_trace["trace_id"]
            trace_file = self.log_dir / f"{trace_id}.json"
            
            # If file doesn't exist, write the whole trace
            if not trace_file.exists():
                with open(trace_file, 'w') as f:
                    json.dump(self.current_trace, f)
            else:
                # Otherwise read the file, update events, and write back
                with open(trace_file, 'r') as f:
                    trace_data = json.load(f)
                    
                trace_data["events"] = self.current_trace["events"]
                trace_data["event_count"] = len(trace_data["events"])
                
                with open(trace_file, 'w') as f:
                    json.dump(trace_data, f)
                    
            self.last_flush_time = time.time()
                
        except Exception as e:
            logger.error(f"Error flushing events to disk: {e}")
    
    def _truncate_data(self, data: Any) -> Any:
        """
        Truncate data to the maximum allowed size.
        
        Args:
            data: Data to truncate
            
        Returns:
            truncated_data: Truncated data
        """
        if data is None:
            return None
            
        # For basic types, just return as is
        if isinstance(data, (bool, int, float)):
            return data
            
        # For strings, truncate if too long
        if isinstance(data, str):
            if len(data) > self.max_data_size:
                return data[:self.max_data_size] + "... [truncated]"
            return data
            
        # For lists, process each element with recursion
        if isinstance(data, list):
            # Check if list is too large
            if len(data) > 100:
                truncated = data[:100]
                result = [self._truncate_data(item) for item in truncated]
                result.append(f"... [truncated {len(data) - 100} more items]")
                return result
            return [self._truncate_data(item) for item in data]
            
        # For dictionaries, process recursively
        if isinstance(data, dict):
            result = {}
            
            # Process each key-value pair
            for key, value in list(data.items())[:100]:  # Limit to 100 keys
                result[key] = self._truncate_data(value)
                
            # Add note if dictionary was truncated
            if len(data) > 100:
                result["__truncated__"] = f"Dictionary truncated, {len(data) - 100} keys omitted"
                
            return result
            
        # For other types, convert to string and truncate
        try:
            data_str = str(data)
            if len(data_str) > self.max_data_size:
                return data_str[:self.max_data_size] + "... [truncated]"
            return data_str
        except:
            return f"<{type(data).__name__} object - cannot serialize>"
    
    def start_span(self, span_type: str, component_id: str, 
                  metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new span for grouping related events.
        
        Args:
            span_type: Type of span (agent_execution, memory_operation, etc.)
            component_id: ID of the component starting the span
            metadata: Optional metadata about the span
            
        Returns:
            span_id: ID of the new span
        """
        if not self.enabled or self.current_trace is None:
            return ""
            
        with self._trace_lock:
            # Create new span
            span_id = str(uuid.uuid4())
            
            # Push current span to stack if exists
            if self.current_span is not None:
                self.span_stack.append(self.current_span)
                parent_span_id = self.current_span["span_id"]
            else:
                parent_span_id = None
                
            # Create the span
            self.current_span = {
                "span_id": span_id,
                "span_type": span_type,
                "component_id": component_id,
                "start_time": time.time(),
                "parent_span_id": parent_span_id,
                "metadata": metadata or {}
            }
            
            # Add to trace spans
            self.current_trace["spans"].append(self.current_span)
            
            # Log a span_start event
            self.log_event("span_start", component_id, {
                "span_id": span_id,
                "span_type": span_type,
                "parent_span_id": parent_span_id,
                "metadata": metadata or {}
            })
            
            return span_id
    
    def end_span(self, status: str = "completed", 
                result: Optional[Dict[str, Any]] = None) -> None:
        """
        End the current span.
        
        Args:
            status: Final status of the span
            result: Optional result data
        """
        if not self.enabled or self.current_trace is None or self.current_span is None:
            return
            
        with self._trace_lock:
            # Update span with end info
            self.current_span["end_time"] = time.time()
            self.current_span["duration"] = self.current_span["end_time"] - self.current_span["start_time"]
            self.current_span["status"] = status
            
            if result and self.log_data_content:
                self.current_span["result"] = self._truncate_data(result)
                
            # Log a span_end event
            self.log_event("span_end", self.current_span["component_id"], {
                "span_id": self.current_span["span_id"],
                "span_type": self.current_span["span_type"],
                "duration": self.current_span["duration"],
                "status": status
            })
            
            # Restore previous span if it exists
            if self.span_stack:
                self.current_span = self.span_stack.pop()
            else:
                self.current_span = None
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """
        Collect system information for trace context.
        
        Returns:
            system_info: Dictionary of system information
        """
        import platform
        import psutil
        
        try:
            info = {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "processor": platform.processor(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "hostname": platform.node(),
                "timestamp": datetime.now().isoformat()
            }
            
            return info
        except Exception as e:
            logger.warning(f"Error collecting system info: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _prune_old_traces(self) -> int:
        """
        Prune old traces to stay within limits.
        
        Returns:
            pruned_count: Number of traces pruned
        """
        if not self.enabled or not self.auto_prune:
            return 0
            
        try:
            # List all trace files
            trace_files = list(self.log_dir.glob("*.json"))
            
            # If under the limit, no need to prune
            if len(trace_files) <= self.max_traces:
                return 0
                
            # Get file info
            file_info = []
            current_time = time.time()
            
            for file_path in trace_files:
                try:
                    mtime = file_path.stat().st_mtime
                    age = current_time - mtime
                    
                    # Remove very old files immediately
                    if age > self.max_trace_age:
                        file_path.unlink()
                        continue
                        
                    file_info.append((file_path, mtime))
                except:
                    # If can't get info, assume it's old
                    file_path.unlink()
                    
            # Sort by modification time (oldest first)
            file_info.sort(key=lambda x: x[1])
            
            # Determine how many to remove
            to_remove = max(0, len(file_info) - self.max_traces)
            
            # Remove oldest files
            for i in range(to_remove):
                file_path = file_info[i][0]
                file_path.unlink()
                
            return to_remove
                
        except Exception as e:
            logger.error(f"Error pruning old traces: {e}")
            return 0
    
    def get_trace_info(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a specific trace.
        
        Args:
            trace_id: ID of the trace
            
        Returns:
            trace_info: Dictionary with trace metadata
        """
        if not self.enabled:
            return None
            
        try:
            trace_file = self.log_dir / f"{trace_id}.json"
            
            if not trace_file.exists():
                return None
                
            # Read just the top-level info, not events
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
                
            # Create a summary without events
            info = {
                "trace_id": trace_data.get("trace_id"),
                "start_time": trace_data.get("start_time"),
                "end_time": trace_data.get("end_time"),
                "duration": trace_data.get("duration"),
                "status": trace_data.get("status"),
                "event_count": trace_data.get("event_count", len(trace_data.get("events", []))),
                "metadata": trace_data.get("metadata", {})
            }
            
            return info
                
        except Exception as e:
            logger.error(f"Error getting trace info: {e}")
            return None
    
    def get_trace_events(self, trace_id: str, 
                       filters: Optional[Dict[str, Any]] = None,
                       limit: Optional[int] = None,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get events from a specific trace with optional filtering.
        
        Args:
            trace_id: ID of the trace
            filters: Optional filters for event type, component, etc.
            limit: Maximum number of events to return
            offset: Offset for pagination
            
        Returns:
            events: List of events matching filters
        """
        if not self.enabled:
            return []
            
        try:
            trace_file = self.log_dir / f"{trace_id}.json"
            
            if not trace_file.exists():
                return []
                
            # Read the trace file
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
                
            events = trace_data.get("events", [])
            
            # Apply filters if provided
            if filters:
                filtered_events = []
                
                for event in events:
                    match = True
                    
                    for key, value in filters.items():
                        if key == "time_range":
                            # Special case for time range filter
                            start_time, end_time = value
                            if event["timestamp"] < start_time or event["timestamp"] > end_time:
                                match = False
                                break
                        elif key == "span_id" and key in event:
                            if event[key] != value:
                                match = False
                                break
                        elif key == "component_id" and key in event:
                            if event[key] != value:
                                match = False
                                break
                        elif key == "event_type" and key in event:
                            if event[key] != value:
                                match = False
                                break
                                
                    if match:
                        filtered_events.append(event)
                        
                events = filtered_events
                
            # Apply pagination
            if offset:
                events = events[offset:]
                
            if limit:
                events = events[:limit]
                
            return events
                
        except Exception as e:
            logger.error(f"Error getting trace events: {e}")
            return []
    
    def get_trace_spans(self, trace_id: str) -> List[Dict[str, Any]]:
        """
        Get spans from a specific trace.
        
        Args:
            trace_id: ID of the trace
            
        Returns:
            spans: List of spans in the trace
        """
        if not self.enabled:
            return []
            
        try:
            trace_file = self.log_dir / f"{trace_id}.json"
            
            if not trace_file.exists():
                return []
                
            # Read the trace file
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
                
            return trace_data.get("spans", [])
                
        except Exception as e:
            logger.error(f"Error getting trace spans: {e}")
            return []
    
    def list_traces(self, limit: int = 100, 
                  filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List available traces with metadata.
        
        Args:
            limit: Maximum number of traces to return
            filters: Optional filters for trace status, time range, etc.
            
        Returns:
            traces: List of trace summaries
        """
        if not self.enabled:
            return []
            
        try:
            # List all trace files
            trace_files = list(self.log_dir.glob("*.json"))
            
            # Extract basic info from each file
            traces = []
            
            for file_path in trace_files[:limit * 2]:  # Get more than needed for filtering
                try:
                    # Read just enough to get metadata
                    with open(file_path, 'r') as f:
                        trace_data = json.load(f)
                        
                    # Create summary
                    info = {
                        "trace_id": trace_data.get("trace_id"),
                        "start_time": trace_data.get("start_time"),
                        "end_time": trace_data.get("end_time", 0),
                        "duration": trace_data.get("duration", 0),
                        "status": trace_data.get("status"),
                        "event_count": trace_data.get("event_count", len(trace_data.get("events", []))),
                        "metadata": trace_data.get("metadata", {})
                    }
                    
                    # Apply filters if provided
                    if filters:
                        match = True
                        
                        for key, value in filters.items():
                            if key == "status" and info["status"] != value:
                                match = False
                                break
                            elif key == "time_range":
                                start_time, end_time = value
                                if info["start_time"] < start_time or (info["end_time"] and info["end_time"] > end_time):
                                    match = False
                                    break
                            elif key == "metadata":
                                # Check if all metadata key-values match
                                for meta_key, meta_value in value.items():
                                    if meta_key not in info["metadata"] or info["metadata"][meta_key] != meta_value:
                                        match = False
                                        break
                                        
                            if not match:
                                break
                                
                        if not match:
                            continue
                            
                    traces.append(info)
                    
                    # If we have enough after filtering, stop
                    if len(traces) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error reading trace file {file_path}: {e}")
                    
            # Sort by start time (newest first)
            traces.sort(key=lambda x: x["start_time"], reverse=True)
            
            return traces[:limit]
                
        except Exception as e:
            logger.error(f"Error listing traces: {e}")
            return []
    
    def compress_old_traces(self) -> int:
        """
        Compress old trace files to save space.
        
        Returns:
            compressed_count: Number of traces compressed
        """
        if not self.enabled or not self.compression_enabled:
            return 0
            
        try:
            import gzip
            import shutil
            
            # List all trace files
            trace_files = list(self.log_dir.glob("*.json"))
            compressed_count = 0
            current_time = time.time()
            
            for file_path in trace_files:
                # Skip already compressed files
                if file_path.suffix == ".gz":
                    continue
                    
                # Check if file is old enough to compress
                mtime = file_path.stat().st_mtime
                age = current_time - mtime
                
                if age > self.compress_after:
                    # Compress file
                    try:
                        compressed_path = file_path.with_suffix(".json.gz")
                        
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                                
                        # Verify the compressed file exists before deleting original
                        if compressed_path.exists():
                            file_path.unlink()
                            compressed_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Error compressing trace file {file_path}: {e}")
                        
            return compressed_count
                
        except Exception as e:
            logger.error(f"Error compressing old traces: {e}")
            return 0
    
    def shutdown(self) -> None:
        """
        Shutdown the trace logger, flushing any pending data.
        """
        if not self.enabled:
            return
            
        with self._trace_lock:
            # Flush any pending events
            if self.current_trace is not None:
                self._flush_events()
                
            # Stop async logging thread if running
            if self.async_logging:
                self._stop_logging.set()
                self._log_thread.join(timeout=2.0)
                
                # Process any remaining items in the queue
                try:
                    while not self._log_queue.empty():
                        item = self._log_queue.get_nowait()
                        
                        if item["type"] == "event":
                            trace_id = item["trace_id"]
                            event = item["event"]
                            self._append_event_to_file(trace_id, event)
                        elif item["type"] == "trace_end":
                            trace = item["trace"]
                            self._write_trace_to_file(trace)
                            
                        self._log_queue.task_done()
                except:
                    pass
                    
            logger.info("Trace logger shutdown complete")

# Trace Logger Summary
# -------------------
# The TraceLogger module provides comprehensive execution path recording for
# debugging, performance analysis, and visualization of component interactions
# in the Neuron architecture.
#
# Key features:
#
# 1. Detailed Event Logging:
#    - Records component interactions, data flow, and decision points
#    - Captures timing information for performance analysis
#    - Organizes events into logical spans for hierarchical tracking
#    - Configurable data content logging with size limits
#
# 2. Efficient Storage Management:
#    - Supports asynchronous background logging for performance
#    - Implements trace file rotation and pruning policies
#    - Compresses older traces to save disk space
#    - Configurable retention policies for log management
#
# 3. Flexible Query Capabilities:
#    - Filters events by type, component, time range, or span
#    - Provides pagination for handling large trace files
#    - Offers metadata-based trace search functionality
#    - Supports extraction of trace statistics and summaries
#
# 4. Execution Context Tracking:
#    - Maintains hierarchical span structure for nested operations
#    - Records system information for environmental context
#    - Preserves metadata about execution conditions
#    - Tracks execution status and results
#
# 5. Performance Considerations:
#    - Event sampling for high-volume operations
#    - Configurable log levels for different detail requirements
#    - Optional content truncation to limit file size
#    - Thread-safe implementation for concurrent operations
#
# This module is essential for observability in the Neuron architecture, enabling
# detailed analysis of execution paths, component performance, and system behavior
# for debugging and optimization purposes.
