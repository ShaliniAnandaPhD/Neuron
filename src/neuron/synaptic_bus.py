"""
synaptic_bus.py - Communication System for Neuron Framework

This module implements the communication system for the Neuron framework,
allowing agents to exchange messages with each other. The SynapticBus
provides a flexible, asynchronous messaging infrastructure inspired by
how neurons communicate through synapses in the brain.

The SynapticBus supports various communication patterns, including
direct messaging, broadcasting, and publish-subscribe, with features
like message prioritization, routing, and delivery guarantees.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from .config import config
from .exceptions import (
    ChannelError,
    CommunicationError,
    MessageValidationError,
    SynapticBusError,
    ValidationError,
)
from .types import AgentID, Message, MessageID, MessagePriority

logger = logging.getLogger(__name__)


class DeliveryGuarantee(Enum):
    """
    Types of delivery guarantees for messages.
    
    This defines how the SynapticBus ensures messages are delivered
    to their recipients, with different trade-offs between reliability
    and performance.
    """
    AT_MOST_ONCE = "at_most_once"  # Fire and forget, no confirmation
    AT_LEAST_ONCE = "at_least_once"  # Retry until confirmed
    EXACTLY_ONCE = "exactly_once"  # Ensure exactly one delivery with deduplication


class Channel:
    """
    A named communication channel for groups of agents.
    
    Channels provide a way for agents to communicate without having to know
    each other's identities, similar to how different brain regions communicate
    through established pathways.
    """
    
    def __init__(self, name: str, buffer_size: int = 1000):
        """
        Initialize a channel.
        
        Args:
            name: Unique name for this channel
            buffer_size: Maximum number of messages to buffer
        """
        self.name = name
        self.buffer_size = buffer_size
        self._subscribers = set()  # Set of agent IDs
        self._message_queue = asyncio.Queue(maxsize=buffer_size)
        self._lock = asyncio.Lock()
        self._active = True
        
        logger.debug(f"Created channel: {name}")
    
    async def subscribe(self, agent_id: AgentID) -> None:
        """
        Subscribe an agent to this channel.
        
        Args:
            agent_id: ID of the agent to subscribe
            
        Raises:
            ChannelError: If the agent is already subscribed or the channel is inactive
        """
        async with self._lock:
            if not self._active:
                raise ChannelError(f"Channel {self.name} is not active")
            
            if agent_id in self._subscribers:
                logger.warning(f"Agent {agent_id} is already subscribed to channel {self.name}")
                return
            
            self._subscribers.add(agent_id)
            logger.debug(f"Agent {agent_id} subscribed to channel {self.name}")
    
    async def unsubscribe(self, agent_id: AgentID) -> None:
        """
        Unsubscribe an agent from this channel.
        
        Args:
            agent_id: ID of the agent to unsubscribe
            
        Raises:
            ChannelError: If the agent is not subscribed or the channel is inactive
        """
        async with self._lock:
            if not self._active:
                raise ChannelError(f"Channel {self.name} is not active")
            
            if agent_id not in self._subscribers:
                logger.warning(f"Agent {agent_id} is not subscribed to channel {self.name}")
                return
            
            self._subscribers.remove(agent_id)
            logger.debug(f"Agent {agent_id} unsubscribed from channel {self.name}")
    
    async def publish(self, message: Message) -> None:
        """
        Publish a message to this channel.
        
        Args:
            message: Message to publish
            
        Raises:
            ChannelError: If the channel is inactive or the queue is full
        """
        if not self._active:
            raise ChannelError(f"Channel {self.name} is not active")
        
        try:
            # Put the message in the queue with a timeout
            await asyncio.wait_for(
                self._message_queue.put(message),
                timeout=5.0
            )
            logger.debug(f"Published message {message.id} to channel {self.name}")
        except asyncio.TimeoutError:
            raise ChannelError(f"Channel {self.name} queue is full")
    
    async def get_message(self) -> Optional[Message]:
        """
        Get the next message from this channel.
        
        Returns:
            Next message in the queue, or None if the channel is inactive
            
        Note:
            This method is typically called by the SynapticBus, not directly by agents.
        """
        if not self._active:
            return None
        
        try:
            # Get a message from the queue with a timeout
            message = await asyncio.wait_for(
                self._message_queue.get(),
                timeout=0.1
            )
            self._message_queue.task_done()
            return message
        except asyncio.TimeoutError:
            return None
    
    def get_subscribers(self) -> Set[AgentID]:
        """
        Get the set of subscribers to this channel.
        
        Returns:
            Set of agent IDs subscribed to this channel
        """
        return self._subscribers.copy()
    
    def message_count(self) -> int:
        """
        Get the number of pending messages in this channel.
        
        Returns:
            Number of messages in the queue
        """
        return self._message_queue.qsize()
    
    def close(self) -> None:
        """
        Close this channel.
        
        This prevents further publishing and subscription changes.
        """
        self._active = False
        logger.debug(f"Closed channel: {self.name}")


class MessageRouter:
    """
    Routes messages to their destinations.
    
    The MessageRouter is responsible for determining which agents should
    receive a message, based on direct addressing, channel subscriptions,
    and routing rules.
    """
    
    def __init__(self):
        """Initialize the message router."""
        self._channels = {}  # Channel name -> Channel
        self._routing_rules = []  # List of (condition, targets) pairs
        self._lock = asyncio.Lock()
        
        logger.debug("Initialized MessageRouter")
    
    async def create_channel(self, name: str, buffer_size: int = 1000) -> Channel:
        """
        Create a new communication channel.
        
        Args:
            name: Unique name for the channel
            buffer_size: Maximum number of messages to buffer
            
        Returns:
            The created channel
            
        Raises:
            ChannelError: If a channel with the same name already exists
        """
        async with self._lock:
            if name in self._channels:
                raise ChannelError(f"Channel {name} already exists")
            
            channel = Channel(name, buffer_size)
            self._channels[name] = channel
            return channel
    
    async def remove_channel(self, name: str) -> None:
        """
        Remove a communication channel.
        
        Args:
            name: Name of the channel to remove
            
        Raises:
            ChannelError: If the channel does not exist
        """
        async with self._lock:
            if name not in self._channels:
                raise ChannelError(f"Channel {name} does not exist")
            
            channel = self._channels[name]
            channel.close()
            del self._channels[name]
    
    async def get_channel(self, name: str) -> Channel:
        """
        Get a communication channel by name.
        
        Args:
            name: Name of the channel to get
            
        Returns:
            The requested channel
            
        Raises:
            ChannelError: If the channel does not exist
        """
        async with self._lock:
            if name not in self._channels:
                raise ChannelError(f"Channel {name} does not exist")
            
            return self._channels[name]
    
    def get_all_channels(self) -> Dict[str, Channel]:
        """
        Get all communication channels.
        
        Returns:
            Dictionary mapping channel names to channels
        """
        return self._channels.copy()
    
    async def add_routing_rule(self, condition: Callable[[Message], bool],
                             targets: Union[AgentID, List[AgentID], str]) -> int:
        """
        Add a routing rule.
        
        Args:
            condition: Function that takes a message and returns True if the rule applies
            targets: Target agent ID(s) or channel name
            
        Returns:
            Rule ID (index in the routing rules list)
        """
        async with self._lock:
            rule_id = len(self._routing_rules)
            self._routing_rules.append((condition, targets))
            return rule_id
    
    async def remove_routing_rule(self, rule_id: int) -> bool:
        """
        Remove a routing rule.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            True if the rule was removed, False if it doesn't exist
        """
        async with self._lock:
            if 0 <= rule_id < len(self._routing_rules):
                self._routing_rules.pop(rule_id)
                return True
            return False
    
    async def route_message(self, message: Message) -> List[AgentID]:
        """
        Determine the recipients for a message.
        
        This handles direct addressing, channel publishing, and routing rules.
        
        Args:
            message: Message to route
            
        Returns:
            List of agent IDs that should receive the message
        """
        recipients = set()
        
        # Handle direct recipients
        if message.recipients:
            for recipient in message.recipients:
                # Check if recipient is a channel
                if recipient in self._channels:
                    # Publish to channel
                    channel = self._channels[recipient]
                    await channel.publish(message)
                    
                    # Add channel subscribers to recipients
                    recipients.update(channel.get_subscribers())
                else:
                    # Direct recipient
                    recipients.add(recipient)
        
        # Apply routing rules
        for condition, targets in self._routing_rules:
            try:
                if condition(message):
                    if isinstance(targets, str):
                        # Channel name
                        if targets in self._channels:
                            channel = self._channels[targets]
                            await channel.publish(message)
                            recipients.update(channel.get_subscribers())
                    elif isinstance(targets, list):
                        # List of agent IDs
                        recipients.update(targets)
                    else:
                        # Single agent ID
                        recipients.add(targets)
            except Exception as e:
                logger.error(f"Error applying routing rule: {e}")
        
        # Don't route to sender
        if message.sender in recipients:
            recipients.remove(message.sender)
        
        return list(recipients)


class MessageProcessor:
    """
    Processes messages before delivery.
    
    The MessageProcessor applies transformations, validations, and other
    processing to messages before they are delivered to recipients.
    """
    
    def __init__(self):
        """Initialize the message processor."""
        self._preprocessors = []  # List of preprocessor functions
        self._validators = []  # List of validator functions
        self._postprocessors = []  # List of postprocessor functions
        
        # Add default validators
        self._validators.append(self._validate_message_structure)
        
        logger.debug("Initialized MessageProcessor")
    
    def add_preprocessor(self, preprocessor: Callable[[Message], Message]) -> None:
        """
        Add a preprocessor function.
        
        Args:
            preprocessor: Function that takes a message and returns a processed message
        """
        self._preprocessors.append(preprocessor)
    
    def add_validator(self, validator: Callable[[Message], bool]) -> None:
        """
        Add a validator function.
        
        Args:
            validator: Function that takes a message and returns True if valid
        """
        self._validators.append(validator)
    
    def add_postprocessor(self, postprocessor: Callable[[Message], Message]) -> None:
        """
        Add a postprocessor function.
        
        Args:
            postprocessor: Function that takes a message and returns a processed message
        """
        self._postprocessors.append(postprocessor)
    
    async def process_message(self, message: Message) -> Message:
        """
        Process a message.
        
        This applies all preprocessors, validators, and postprocessors.
        
        Args:
            message: Message to process
            
        Returns:
            Processed message
            
        Raises:
            MessageValidationError: If the message fails validation
        """
        # Apply preprocessors
        processed_message = message
        for preprocessor in self._preprocessors:
            try:
                processed_message = preprocessor(processed_message)
            except Exception as e:
                logger.error(f"Error in preprocessor: {e}")
        
        # Apply validators
        for validator in self._validators:
            try:
                if not validator(processed_message):
                    raise MessageValidationError(f"Message failed validation: {processed_message.id}")
            except Exception as e:
                if isinstance(e, MessageValidationError):
                    raise
                logger.error(f"Error in validator: {e}")
                raise MessageValidationError(f"Error validating message: {e}")
        
        # Apply postprocessors
        for postprocessor in self._postprocessors:
            try:
                processed_message = postprocessor(processed_message)
            except Exception as e:
                logger.error(f"Error in postprocessor: {e}")
        
        return processed_message
    
    def _validate_message_structure(self, message: Message) -> bool:
        """
        Validate the basic structure of a message.
        
        Args:
            message: Message to validate
            
        Returns:
            True if the message is valid, False otherwise
        """
        if not message.id:
            logger.error("Message missing ID")
            return False
        
        if not message.sender:
            logger.error("Message missing sender")
            return False
        
        return True


class DeliveryManager:
    """
    Manages message delivery with different delivery guarantees.
    
    The DeliveryManager ensures messages are delivered according to the
    specified delivery guarantee, handling retries, acknowledgments,
    and deduplication as needed.
    """
    
    def __init__(self, default_guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE,
                max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the delivery manager.
        
        Args:
            default_guarantee: Default delivery guarantee to use
            max_retries: Maximum number of delivery retries
            retry_delay: Delay between retries (seconds)
        """
        self._default_guarantee = default_guarantee
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._delivery_attempts = {}  # MessageID -> (attempts, last_attempt_time)
        self._delivered_messages = set()  # Set of delivered message IDs (for deduplication)
        self._lock = asyncio.Lock()
        
        # Set up cleanup task
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
        
        logger.debug(f"Initialized DeliveryManager with {default_guarantee.name}")
    
    async def prepare_delivery(self, message: Message) -> Tuple[Message, DeliveryGuarantee]:
        """
        Prepare a message for delivery.
        
        This adds delivery metadata to the message and determines the
        appropriate delivery guarantee.
        
        Args:
            message: Message to prepare
            
        Returns:
            Tuple of (prepared message, delivery guarantee)
        """
        async with self._lock:
            # Determine delivery guarantee
            guarantee = self._default_guarantee
            if "delivery_guarantee" in message.metadata:
                try:
                    guarantee = DeliveryGuarantee(message.metadata["delivery_guarantee"])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid delivery guarantee in message {message.id}, using default")
            
            # Add delivery metadata
            if "delivery" not in message.metadata:
                message.metadata["delivery"] = {}
            
            message.metadata["delivery"]["attempt"] = 1
            message.metadata["delivery"]["timestamp"] = time.time()
            
            # Record delivery attempt
            self._delivery_attempts[message.id] = (1, time.time())
            
            return message, guarantee
    
    async def handle_delivery(self, message: Message, recipient: AgentID,
                            guarantee: DeliveryGuarantee) -> bool:
        """
        Handle delivery of a message to a recipient.
        
        This implements the delivery guarantee logic, including
        deduplication for EXACTLY_ONCE delivery.
        
        Args:
            message: Message to deliver
            recipient: ID of the recipient agent
            guarantee: Delivery guarantee to use
            
        Returns:
            True if delivery should proceed, False if it should be skipped
        """
        async with self._lock:
            # For EXACTLY_ONCE, check if already delivered
            if guarantee == DeliveryGuarantee.EXACTLY_ONCE:
                delivery_key = f"{message.id}:{recipient}"
                if delivery_key in self._delivered_messages:
                    logger.debug(f"Skipping duplicate delivery of {message.id} to {recipient}")
                    return False
                self._delivered_messages.add(delivery_key)
            
            return True
    
    async def record_delivery_result(self, message: Message, recipient: AgentID,
                                   successful: bool, guarantee: DeliveryGuarantee) -> bool:
        """
        Record the result of a delivery attempt.
        
        Args:
            message: Delivered message
            recipient: ID of the recipient agent
            successful: Whether delivery was successful
            guarantee: Delivery guarantee used
            
        Returns:
            True if retry is needed, False otherwise
        """
        if successful:
            # Successful delivery
            return False
        
        # Failed delivery
        if guarantee == DeliveryGuarantee.AT_MOST_ONCE:
            # No retry for AT_MOST_ONCE
            return False
        
        async with self._lock:
            # Check if we should retry
            attempts, last_attempt = self._delivery_attempts.get(message.id, (0, 0))
            
            if attempts >= self._max_retries:
                # Max retries reached
                logger.warning(f"Max retries reached for message {message.id} to {recipient}")
                return False
            
            # Update delivery attempts
            self._delivery_attempts[message.id] = (attempts + 1, time.time())
            
            # Update message metadata
            if "delivery" not in message.metadata:
                message.metadata["delivery"] = {}
            
            message.metadata["delivery"]["attempt"] = attempts + 1
            message.metadata["delivery"]["timestamp"] = time.time()
            
            return True
    
    async def cleanup(self) -> None:
        """
        Clean up delivery tracking data.
        
        This removes old delivery records to prevent memory leaks.
        """
        async with self._lock:
            current_time = time.time()
            
            # Only clean up periodically
            if current_time - self._last_cleanup < self._cleanup_interval:
                return
            
            self._last_cleanup = current_time
            
            # Clean up delivery attempts
            expired_messages = []
            for message_id, (attempts, last_attempt) in self._delivery_attempts.items():
                if current_time - last_attempt > 3600:  # 1 hour
                    expired_messages.append(message_id)
            
            for message_id in expired_messages:
                del self._delivery_attempts[message_id]
            
            # Clean up delivered messages
            # This is simplified; a real implementation would use a time-based expiration strategy
            if len(self._delivered_messages) > 10000:
                self._delivered_messages.clear()
            
            logger.debug(f"Cleaned up delivery tracking data: {len(expired_messages)} expired messages")


class SynapticBus:
    """
    Central communication system for the Neuron framework.
    
    The SynapticBus provides the infrastructure for message exchange between
    agents, handling routing, delivery, and channel management. It's conceptually
    similar to the synaptic connections between neurons in the brain.
    """
    
    def __init__(self):
        """Initialize the SynapticBus."""
        self._router = None
        self._processor = None
        self._delivery_manager = None
        self._agent_callbacks = {}  # AgentID -> callback function
        self._message_queue = None
        self._processing_task = None
        self._stop_event = None
        self._lock = threading.RLock()
        
        logger.info("Initialized SynapticBus")
    
    def initialize(self) -> None:
        """
        Initialize the SynapticBus components.
        
        This sets up the router, processor, delivery manager, and message queue.
        """
        with self._lock:
            # Create components
            self._router = MessageRouter()
            self._processor = MessageProcessor()
            
            # Get delivery guarantee from config
            delivery_guarantee_name = config.get(
                "synaptic_bus", "delivery_guarantees", "at_least_once"
            )
            try:
                delivery_guarantee = DeliveryGuarantee(delivery_guarantee_name)
            except ValueError:
                logger.warning(f"Invalid delivery guarantee in config: {delivery_guarantee_name}")
                delivery_guarantee = DeliveryGuarantee.AT_LEAST_ONCE
            
            self._delivery_manager = DeliveryManager(
                default_guarantee=delivery_guarantee,
                max_retries=config.get("synaptic_bus", "retry_attempts", 3),
                retry_delay=config.get("synaptic_bus", "retry_delay", 1.0)
            )
            
            # Initialize message queue
            max_queue_size = config.get("synaptic_bus", "max_queue_size", 10000)
            self._message_queue = asyncio.Queue(maxsize=max_queue_size)
            
            # Initialize stop event
            self._stop_event = asyncio.Event()
            
            # Create default channels
            self._create_default_channels()
            
            logger.info("SynapticBus components initialized")
    
    def _create_default_channels(self) -> None:
        """Create default communication channels."""
        asyncio.create_task(self._router.create_channel("broadcast"))
        asyncio.create_task(self._router.create_channel("errors"))
        asyncio.create_task(self._router.create_channel("system"))
        
        logger.debug("Created default channels")
    
    def start(self) -> None:
        """
        Start the SynapticBus.
        
        This begins processing messages from the queue and delivering
        them to recipients.
        """
        with self._lock:
            if self._processing_task is not None:
                logger.warning("SynapticBus is already running")
                return
            
            # Clear stop event
            self._stop_event.clear()
            
            # Start message processing task
            self._processing_task = asyncio.create_task(self._process_messages())
            
            logger.info("SynapticBus started")
    
    def stop(self) -> None:
        """
        Stop the SynapticBus.
        
        This gracefully terminates message processing and delivery.
        """
        with self._lock:
            if self._processing_task is None:
                logger.warning("SynapticBus is not running")
                return
            
            # Set stop event
            self._stop_event.set()
            
            # Cancel processing task
            self._processing_task.cancel()
            self._processing_task = None
            
            logger.info("SynapticBus stopped")
    
    async def send(self, message: Message) -> None:
        """
        Send a message.
        
        This adds the message to the processing queue.
        
        Args:
            message: Message to send
            
        Raises:
            SynapticBusError: If the message queue is full or the bus is not running
        """
        if self._message_queue is None or self._processing_task is None:
            raise SynapticBusError("SynapticBus is not initialized or not running")
        
        try:
            # Add to queue with timeout
            await asyncio.wait_for(
                self._message_queue.put(message),
                timeout=5.0
            )
            logger.debug(f"Queued message {message.id} from {message.sender}")
        except asyncio.TimeoutError:
            raise SynapticBusError("Message queue is full")
    
    async def register_agent(self, agent_id: AgentID, callback: Callable[[Message], None]) -> None:
        """
        Register an agent to receive messages.
        
        Args:
            agent_id: ID of the agent
            callback: Function to call when a message is delivered
            
        Raises:
            ValueError: If the agent is already registered
        """
        with self._lock:
            if agent_id in self._agent_callbacks:
                raise ValueError(f"Agent {agent_id} is already registered")
            
            self._agent_callbacks[agent_id] = callback
            logger.debug(f"Registered agent: {agent_id}")
    
    async def unregister_agent(self, agent_id: AgentID) -> None:
        """
        Unregister an agent.
        
        Args:
            agent_id: ID of the agent
            
        Raises:
            ValueError: If the agent is not registered
        """
        with self._lock:
            if agent_id not in self._agent_callbacks:
                raise ValueError(f"Agent {agent_id} is not registered")
            
            del self._agent_callbacks[agent_id]
            logger.debug(f"Unregistered agent: {agent_id}")
    
    async def create_channel(self, name: str, buffer_size: int = 1000) -> Channel:
        """
        Create a new communication channel.
        
        Args:
            name: Unique name for the channel
            buffer_size: Maximum number of messages to buffer
            
        Returns:
            The created channel
            
        Raises:
            ChannelError: If a channel with the same name already exists
        """
        return await self._router.create_channel(name, buffer_size)
    
    async def remove_channel(self, name: str) -> None:
        """
        Remove a communication channel.
        
        Args:
            name: Name of the channel to remove
            
        Raises:
            ChannelError: If the channel does not exist
        """
        await self._router.remove_channel(name)
    
    async def subscribe_to_channel(self, agent_id: AgentID, channel_name: str) -> None:
        """
        Subscribe an agent to a channel.
        
        Args:
            agent_id: ID of the agent to subscribe
            channel_name: Name of the channel
            
        Raises:
            ChannelError: If the channel does not exist or the agent is already subscribed
        """
        channel = await self._router.get_channel(channel_name)
        await channel.subscribe(agent_id)
    
    async def unsubscribe_from_channel(self, agent_id: AgentID, channel_name: str) -> None:
        """
        Unsubscribe an agent from a channel.
        
        Args:
            agent_id: ID of the agent to unsubscribe
            channel_name: Name of the channel
            
        Raises:
            ChannelError: If the channel does not exist or the agent is not subscribed
        """
        channel = await self._router.get_channel(channel_name)
        await channel.unsubscribe(agent_id)
    
    async def publish_to_channel(self, sender: AgentID, channel_name: str,
                              content: Any, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        Publish a message to a channel.
        
        Args:
            sender: ID of the sending agent
            channel_name: Name of the channel
            content: Message content
            metadata: Additional message metadata
            
        Returns:
            The published message
            
        Raises:
            ChannelError: If the channel does not exist
        """
        channel = await self._router.get_channel(channel_name)
        
        # Create the message
        message = Message.create(
            sender=sender,
            recipients=[channel_name],  # Channel name as recipient
            content=content,
            metadata=metadata or {}
        )
        
        # Publish to the channel
        await channel.publish(message)
        
        return message
    
    async def add_routing_rule(self, condition: Callable[[Message], bool],
                             targets: Union[AgentID, List[AgentID], str]) -> int:
        """
        Add a routing rule.
        
        Args:
            condition: Function that takes a message and returns True if the rule applies
            targets: Target agent ID(s) or channel name
            
        Returns:
            Rule ID (index in the routing rules list)
        """
        return await self._router.add_routing_rule(condition, targets)
    
    async def remove_routing_rule(self, rule_id: int) -> bool:
        """
        Remove a routing rule.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            True if the rule was removed, False if it doesn't exist
        """
        return await self._router.remove_routing_rule(rule_id)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the SynapticBus.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            "queue_size": self._message_queue.qsize() if self._message_queue else 0,
            "registered_agents": len(self._agent_callbacks),
            "channels": {}
        }
        
        # Get channel statistics
        for name, channel in self._router.get_all_channels().items():
            stats["channels"][name] = {
                "subscribers": len(channel.get_subscribers()),
                "messages": channel.message_count()
            }
        
        return stats
    
    async def _process_messages(self) -> None:
        """
        Process messages from the queue.
        
        This is the main message processing loop that:
        1. Gets messages from the queue
        2. Processes them
        3. Routes them to recipients
        4. Delivers them to recipient agents
        """
        try:
            while not self._stop_event.is_set():
                try:
                    # Get message from queue with timeout
                    try:
                        message = await asyncio.wait_for(
                            self._message_queue.get(),
                            timeout=0.1
                        )
                    except asyncio.TimeoutError:
                        # Periodic cleanup
                        await self._delivery_manager.cleanup()
                        continue
                    
                    # Process the message
                    try:
                        processed_message = await self._processor.process_message(message)
                    except MessageValidationError as e:
                        logger.error(f"Message validation failed: {e}")
                        self._message_queue.task_done()
                        continue
                    
                    # Prepare for delivery
                    prepared_message, guarantee = await self._delivery_manager.prepare_delivery(processed_message)
                    
                    # Route the message
                    recipients = await self._router.route_message(prepared_message)
                    
                    # Deliver to each recipient
                    for recipient in recipients:
                        await self._deliver_message(prepared_message, recipient, guarantee)
                    
                    # Mark as done
                    self._message_queue.task_done()
                    
                except asyncio.CancelledError:
                    # Stop processing
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
        except asyncio.CancelledError:
            logger.debug("Message processing task cancelled")
        except Exception as e:
            logger.error(f"Error in message processing loop: {e}")
    
    async def _deliver_message(self, message: Message, recipient: AgentID, 
                             guarantee: DeliveryGuarantee) -> None:
        """
        Deliver a message to a recipient.
        
        Args:
            message: Message to deliver
            recipient: ID of the recipient agent
            guarantee: Delivery guarantee to use
        """
        try:
            # Check if we should deliver (deduplication)
            should_deliver = await self._delivery_manager.handle_delivery(
                message, recipient, guarantee
            )
            
            if not should_deliver:
                return
            
            # Get recipient callback
            callback = self._agent_callbacks.get(recipient)
            if not callback:
                logger.warning(f"Recipient {recipient} not registered, message {message.id} dropped")
                return
            
            # Deliver the message
            try:
                await callback(message)
                successful = True
            except Exception as e:
                logger.error(f"Error delivering message {message.id} to {recipient}: {e}")
                successful = False
            
            # Record delivery result
            should_retry = await self._delivery_manager.record_delivery_result(
                message, recipient, successful, guarantee
            )
            
            if should_retry:
                # Re-queue for retry after delay
                retry_delay = self._delivery_manager._retry_delay
                await asyncio.sleep(retry_delay)
                await self.send(message)
        except Exception as e:
            logger.error(f"Error in message delivery: {e}")
"""
