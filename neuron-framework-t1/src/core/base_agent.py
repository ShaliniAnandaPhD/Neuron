import weave
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class Message:
    type: str
    payload: Dict[str, Any]
    source: str
    target: str
    timestamp: float = None
    message_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.message_id is None:
            import uuid
            self.message_id = str(uuid.uuid4())

@weave.op()
class BaseAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.message_queue = asyncio.Queue()
        self.is_running = False
        
    async def send_message(self, message: Message) -> Message:
        """Send message to target agent"""
        # In production, this would route through message bus
        # For testing, we'll handle directly
        return message
    
    def get_timestamp(self) -> float:
        return time.time()
    
    @abstractmethod
    async def process_message(self, message: Message) -> Message:
        pass