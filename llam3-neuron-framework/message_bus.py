#!/usr/bin/env python3
"""
Message Bus for LLaMA3 Neuron Framework
Handles inter-agent communication and message routing
"""

import asyncio
from typing import Dict, List, Callable, Optional, Any
from collections import defaultdict
import json
import time

from config import (
    MessagePriority,
    get_logger,
    REDIS_URL,
    REDIS_PREFIX,
    REDIS_LOCK_PREFIX,
    LOCK_EXPIRY
)
from models import Message, AgentState
from utils import Metrics, async_retry

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# MESSAGE BUS INTERFACE
# ============================================================================

class MessageHandler:
    """Type for message handler callbacks"""
    def __call__(self, message: Message) -> Optional[Message]:
        pass

class MessageBus:
    """
    Central message bus for inter-agent communication
    Handles message routing, queuing, and delivery
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize message bus
        
        Args:
            redis_url: Redis connection URL for distributed messaging
        """
        self.redis_url = redis_url or REDIS_URL
        self._subscribers: Dict[str, List[MessageHandler]] = defaultdict(list)
        self._agent_handlers: Dict[str, MessageHandler] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._priority_queues: Dict[MessagePriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in MessagePriority
        }
        self._metrics = Metrics("message_bus")
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        # Redis client (optional for distributed setup)
        self._redis_client = None
        self._pubsub = None
    
    async def start(self):
        """Start the message bus"""
        logger.info("Starting message bus")
        
        # Initialize Redis if URL provided
        if self.redis_url and self.redis_url != "redis://localhost:6379":
            try:
                import redis.asyncio as redis
                self._redis_client = await redis.from_url(self.redis_url)
                self._pubsub = self._redis_client.pubsub()
                await self._pubsub.subscribe(f"{REDIS_PREFIX}messages")
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory messaging.")
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_messages())
        
        # Start Redis listener if connected
        if self._pubsub:
            asyncio.create_task(self._redis_listener())
        
        logger.info("Message bus started")
    
    async def stop(self):
        """Stop the message bus"""
        logger.info("Stopping message bus")
        self._running = False
        
        # Cancel processor task
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Close Redis connections
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        
        if self._redis_client:
            await self._redis_client.close()
        
        logger.info("Message bus stopped")
    
    def register_agent(self, agent_id: str, handler: MessageHandler):
        """
        Register an agent's message handler
        
        Args:
            agent_id: Agent identifier
            handler: Message handler function
        """
        self._agent_handlers[agent_id] = handler
        logger.debug(f"Registered agent {agent_id}")
    
    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent
        
        Args:
            agent_id: Agent identifier
        """
        if agent_id in self._agent_handlers:
            del self._agent_handlers[agent_id]
            logger.debug(f"Unregistered agent {agent_id}")
    
    def subscribe(self, message_type: str, handler: MessageHandler):
        """
        Subscribe to messages of a specific type
        
        Args:
            message_type: Type of messages to subscribe to
            handler: Message handler function
        """
        self._subscribers[message_type].append(handler)
        logger.debug(f"Subscribed to message type: {message_type}")
    
    def unsubscribe(self, message_type: str, handler: MessageHandler):
        """
        Unsubscribe from messages of a specific type
        
        Args:
            message_type: Type of messages to unsubscribe from
            handler: Message handler function
        """
        if message_type in self._subscribers:
            try:
                self._subscribers[message_type].remove(handler)
                logger.debug(f"Unsubscribed from message type: {message_type}")
            except ValueError:
                pass
    
    async def send_message(self, message: Message):
        """
        Send a message through the bus
        
        Args:
            message: Message to send
        """
        # Update message timestamp
        message.updated_at = asyncio.get_event_loop().time()
        
        # Add to appropriate priority queue
        await self._priority_queues[message.priority].put(message)
        
        # Publish to Redis if connected
        if self._redis_client:
            try:
                await self._redis_client.publish(
                    f"{REDIS_PREFIX}messages",
                    message.to_json()
                )
            except Exception as e:
                logger.error(f"Failed to publish message to Redis: {e}")
        
        # Update metrics
        await self._metrics.increment("messages_sent")
        await self._metrics.increment(f"messages_sent_{message.priority.name.lower()}")
        
        logger.debug(
            f"Sent message from {message.source_agent} to {message.target_agent} "
            f"(type: {message.message_type}, priority: {message.priority.name})"
        )
    
    async def broadcast_message(self, message: Message):
        """
        Broadcast a message to all agents
        
        Args:
            message: Message to broadcast
        """
        # Set target as broadcast
        message.target_agent = "*"
        await self.send_message(message)
    
    async def _process_messages(self):
        """Process messages from queues"""
        while self._running:
            try:
                # Process messages by priority
                for priority in MessagePriority:
                    queue = self._priority_queues[priority]
                    
                    # Process up to 10 messages per priority level
                    for _ in range(10):
                        if queue.empty():
                            break
                        
                        try:
                            message = await asyncio.wait_for(
                                queue.get(),
                                timeout=0.1
                            )
                            await self._deliver_message(message)
                        except asyncio.TimeoutError:
                            break
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                await asyncio.sleep(1)
    
    async def _deliver_message(self, message: Message):
        """
        Deliver a message to its target(s)
        
        Args:
            message: Message to deliver
        """
        start_time = time.time()
        
        try:
            # Check if message is expired
            if message.is_expired():
                logger.warning(f"Message {message.id} expired, dropping")
                await self._metrics.increment("messages_expired")
                return
            
            delivered = False
            
            # Handle broadcast messages
            if message.target_agent == "*":
                for agent_id, handler in self._agent_handlers.items():
                    if agent_id != message.source_agent:
                        await self._call_handler(handler, message)
                        delivered = True
            
            # Handle targeted messages
            elif message.target_agent in self._agent_handlers:
                handler = self._agent_handlers[message.target_agent]
                response = await self._call_handler(handler, message)
                delivered = True
                
                # Handle response message if any
                if response:
                    response.correlation_id = message.id
                    response.reply_to = message.id
                    await self.send_message(response)
            
            # Handle message type subscribers
            if message.message_type in self._subscribers:
                for handler in self._subscribers[message.message_type]:
                    await self._call_handler(handler, message)
                    delivered = True
            
            # Update delivery status
            message.delivered = delivered
            
            # Update metrics
            if delivered:
                await self._metrics.increment("messages_delivered")
                latency = (time.time() - start_time) * 1000
                await self._metrics.record("delivery_latency_ms", latency)
            else:
                await self._metrics.increment("messages_undelivered")
                logger.warning(
                    f"No handler found for message to {message.target_agent} "
                    f"(type: {message.message_type})"
                )
                
        except Exception as e:
            logger.error(f"Error delivering message {message.id}: {e}")
            await self._metrics.increment("messages_failed")
    
    async def _call_handler(self, handler: MessageHandler, message: Message) -> Optional[Message]:
        """
        Call a message handler with error handling
        
        Args:
            handler: Handler function to call
            message: Message to pass to handler
            
        Returns:
            Optional response message
        """
        try:
            # Mark message as acknowledged
            message.acknowledged = True
            
            # Call handler
            if asyncio.iscoroutinefunction(handler):
                response = await handler(message)
            else:
                response = handler(message)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            await self._metrics.increment("handler_errors")
            return None
    
    async def _redis_listener(self):
        """Listen for messages from Redis"""
        while self._running and self._pubsub:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message['type'] == 'message':
                    # Parse message
                    data = json.loads(message['data'])
                    msg = Message.from_dict(data)
                    
                    # Add to queue if not from this instance
                    # (avoid processing our own messages twice)
                    if not hasattr(msg, '_local'):
                        await self._priority_queues[msg.priority].put(msg)
                        
            except Exception as e:
                logger.error(f"Error in Redis listener: {e}")
                await asyncio.sleep(1)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics
        
        Returns:
            Dictionary of statistics
        """
        stats = await self._metrics.get_all()
        
        # Add queue sizes
        stats['queue_sizes'] = {
            priority.name: queue.qsize()
            for priority, queue in self._priority_queues.items()
        }
        
        # Add handler counts
        stats['registered_agents'] = len(self._agent_handlers)
        stats['subscriptions'] = {
            msg_type: len(handlers)
            for msg_type, handlers in self._subscribers.items()
        }
        
        return stats

# ============================================================================
# DISTRIBUTED MESSAGE BUS
# ============================================================================

class DistributedMessageBus(MessageBus):
    """
    Distributed message bus implementation using Redis
    Supports multiple instances for scaling
    """
    
    def __init__(self, redis_url: str, instance_id: str):
        """
        Initialize distributed message bus
        
        Args:
            redis_url: Redis connection URL
            instance_id: Unique instance identifier
        """
        super().__init__(redis_url)
        self.instance_id = instance_id
        self._lock_prefix = f"{REDIS_LOCK_PREFIX}{instance_id}:"
    
    @async_retry(max_attempts=3, delay=1.0)
    async def acquire_lock(self, resource: str, timeout: int = LOCK_EXPIRY) -> bool:
        """
        Acquire distributed lock
        
        Args:
            resource: Resource to lock
            timeout: Lock timeout in seconds
            
        Returns:
            True if lock acquired
        """
        if not self._redis_client:
            return True  # No Redis, no need for distributed lock
        
        lock_key = f"{self._lock_prefix}{resource}"
        
        try:
            # Try to acquire lock with NX (not exists) and EX (expiry)
            result = await self._redis_client.set(
                lock_key,
                self.instance_id,
                nx=True,
                ex=timeout
            )
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to acquire lock for {resource}: {e}")
            return False
    
    async def release_lock(self, resource: str):
        """
        Release distributed lock
        
        Args:
            resource: Resource to unlock
        """
        if not self._redis_client:
            return
        
        lock_key = f"{self._lock_prefix}{resource}"
        
        try:
            # Only delete if we own the lock
            current_owner = await self._redis_client.get(lock_key)
            if current_owner and current_owner.decode() == self.instance_id:
                await self._redis_client.delete(lock_key)
                
        except Exception as e:
            logger.error(f"Failed to release lock for {resource}: {e}")
    
    async def register_instance(self):
        """Register this instance in Redis"""
        if not self._redis_client:
            return
        
        instance_key = f"{REDIS_PREFIX}instances:{self.instance_id}"
        instance_data = {
            "id": self.instance_id,
            "started_at": time.time(),
            "last_heartbeat": time.time()
        }
        
        try:
            await self._redis_client.hset(
                instance_key,
                mapping=instance_data
            )
            await self._redis_client.expire(instance_key, 300)  # 5 minute expiry
            
        except Exception as e:
            logger.error(f"Failed to register instance: {e}")
    
    async def get_active_instances(self) -> List[str]:
        """
        Get list of active instances
        
        Returns:
            List of instance IDs
        """
        if not self._redis_client:
            return [self.instance_id]
        
        try:
            pattern = f"{REDIS_PREFIX}instances:*"
            keys = await self._redis_client.keys(pattern)
            
            instances = []
            for key in keys:
                instance_id = key.decode().split(":")[-1]
                instances.append(instance_id)
            
            return instances
            
        except Exception as e:
            logger.error(f"Failed to get active instances: {e}")
            return [self.instance_id]

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_message_bus(distributed: bool = False, **kwargs) -> MessageBus:
    """
    Create message bus instance
    
    Args:
        distributed: Whether to create distributed message bus
        **kwargs: Additional configuration
        
    Returns:
        Message bus instance
    """
    if distributed:
        instance_id = kwargs.get('instance_id', f"neuron_{int(time.time())}")
        redis_url = kwargs.get('redis_url', REDIS_URL)
        return DistributedMessageBus(redis_url, instance_id)
    else:
        return MessageBus(kwargs.get('redis_url'))