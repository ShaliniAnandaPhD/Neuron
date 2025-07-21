#!/usr/bin/env python3
"""
Agent Manager - AI Agent Coordination and Management
Handles multiple AI agents with different performance characteristics

This module manages:
- Standard Agent (OpenAI GPT-4) - High quality, moderate speed
- Ultra-Fast Agent (GROQ Llama3) - Lower quality, very high speed  
- Agent initialization and health monitoring
- Request routing and load balancing
- Error handling and fallback strategies
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import openai
import httpx
from pathlib import Path

from .config_manager import PipelineConfig
from .synthetic_market_data import MarketMessage


class AgentType(Enum):
    """Available agent types"""
    STANDARD = "standard"      # OpenAI GPT-4 - balanced quality/speed
    ULTRA_FAST = "ultra_fast"  # GROQ Llama3 - optimized for speed


@dataclass
class AgentResponse:
    """Response from an AI agent"""
    success: bool
    data: Optional[Dict[str, Any]]
    processing_time_ms: float
    agent_type: AgentType
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class AgentHealth:
    """Agent health status"""
    agent_type: AgentType
    is_healthy: bool
    last_check: datetime
    response_time_ms: float
    error_rate: float
    total_requests: int
    successful_requests: int
    consecutive_failures: int


class StandardAgent:
    """
    Standard Agent using OpenAI GPT-4
    Provides high-quality responses with moderate latency
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.StandardAgent")
        
        # Initialize OpenAI client
        self.client = openai.AsyncOpenAI(
            api_key=config.openai_api_key,
            timeout=config.api_timeout_seconds,
            max_retries=config.api_max_retries
        )
        
        # Agent configuration
        self.model = config.openai_model
        self.max_tokens = 150
        self.temperature = 0.1
        
        # Health tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.consecutive_failures = 0
        self.last_response_time = 0.0
        
        self.logger.info(f"StandardAgent initialized with model: {self.model}")
    
    async def process_message(self, message: MarketMessage) -> AgentResponse:
        """Process market message using OpenAI GPT-4"""
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Construct prompt for financial analysis
            prompt = self._build_financial_prompt(message)
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial trading assistant. Analyze market data and provide structured trading insights."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            processing_time = (time.time() - start_time) * 1000
            self.last_response_time = processing_time
            
            # Parse response
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            # Success
            self.successful_requests += 1
            self.consecutive_failures = 0
            
            return AgentResponse(
                success=True,
                data={
                    "analysis": analysis_data,
                    "model_used": self.model,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                    "message_id": message.message_id
                },
                processing_time_ms=processing_time,
                agent_type=AgentType.STANDARD
            )
            
        except json.JSONDecodeError as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"JSON parsing failed: {e}"
            self.logger.error(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.STANDARD,
                error_message=error_msg
            )
            
        except openai.APITimeoutError as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"OpenAI API timeout: {e}"
            self.logger.error(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.STANDARD,
                error_message=error_msg
            )
            
        except openai.RateLimitError as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"OpenAI rate limit exceeded: {e}"
            self.logger.warning(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.STANDARD,
                error_message=error_msg
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"OpenAI API error: {e}"
            self.logger.error(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.STANDARD,
                error_message=error_msg
            )
    
    def _build_financial_prompt(self, message: MarketMessage) -> str:
        """Build financial analysis prompt"""
        return f"""
Analyze this market data and provide trading insights in JSON format:

Symbol: {message.symbol}
Price: ${message.price:.2f}
Volume: {message.volume:,}
Market Condition: {message.market_condition.value}
Timestamp: {message.timestamp}

Please respond with JSON containing:
{{
    "recommendation": "BUY/SELL/HOLD",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "risk_level": "LOW/MEDIUM/HIGH",
    "price_target": numerical_value,
    "stop_loss": numerical_value
}}
"""
    
    async def health_check(self) -> AgentHealth:
        """Perform health check"""
        try:
            start_time = time.time()
            
            # Simple health check request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'healthy' in JSON format."}],
                max_tokens=10,
                response_format={"type": "json_object"}
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return AgentHealth(
                agent_type=AgentType.STANDARD,
                is_healthy=True,
                last_check=datetime.now(),
                response_time_ms=response_time,
                error_rate=1 - (self.successful_requests / max(self.total_requests, 1)),
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                consecutive_failures=self.consecutive_failures
            )
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            
            return AgentHealth(
                agent_type=AgentType.STANDARD,
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=999999,
                error_rate=1.0,
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                consecutive_failures=self.consecutive_failures
            )


class UltraFastAgent:
    """
    Ultra-Fast Agent using GROQ Llama3
    Optimized for minimum latency with acceptable quality
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.UltraFastAgent")
        
        # Initialize GROQ client
        self.client = httpx.AsyncClient(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {config.groq_api_key}"},
            timeout=config.api_timeout_seconds
        )
        
        # Agent configuration
        self.model = config.groq_model
        self.max_tokens = 100  # Shorter responses for speed
        self.temperature = 0.0  # Deterministic for speed
        
        # Health tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.consecutive_failures = 0
        self.last_response_time = 0.0
        
        self.logger.info(f"UltraFastAgent initialized with model: {self.model}")
    
    async def process_message(self, message: MarketMessage) -> AgentResponse:
        """Process market message using GROQ Llama3"""
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Construct optimized prompt for speed
            prompt = self._build_fast_prompt(message)
            
            # Call GROQ API
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Provide fast financial analysis in JSON format."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "response_format": {"type": "json_object"}
                }
            )
            
            processing_time = (time.time() - start_time) * 1000
            self.last_response_time = processing_time
            
            if response.status_code != 200:
                raise Exception(f"GROQ API error: {response.status_code} - {response.text}")
            
            # Parse response
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"]
            analysis_data = json.loads(content)
            
            # Success
            self.successful_requests += 1
            self.consecutive_failures = 0
            
            return AgentResponse(
                success=True,
                data={
                    "analysis": analysis_data,
                    "model_used": self.model,
                    "tokens_used": response_data.get("usage", {}).get("total_tokens", 0),
                    "message_id": message.message_id
                },
                processing_time_ms=processing_time,
                agent_type=AgentType.ULTRA_FAST
            )
            
        except json.JSONDecodeError as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"JSON parsing failed: {e}"
            self.logger.error(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.ULTRA_FAST,
                error_message=error_msg
            )
            
        except httpx.TimeoutException as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"GROQ API timeout: {e}"
            self.logger.error(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.ULTRA_FAST,
                error_message=error_msg
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            error_msg = f"GROQ API error: {e}"
            self.logger.error(error_msg)
            self.consecutive_failures += 1
            
            return AgentResponse(
                success=False,
                data=None,
                processing_time_ms=processing_time,
                agent_type=AgentType.ULTRA_FAST,
                error_message=error_msg
            )
    
    def _build_fast_prompt(self, message: MarketMessage) -> str:
        """Build optimized prompt for fast processing"""
        return f"""
Quick analysis for {message.symbol}: ${message.price:.2f}, vol: {message.volume}, condition: {message.market_condition.value}

JSON response:
{{
    "action": "BUY/SELL/HOLD",
    "confidence": 0.0-1.0,
    "reason": "brief",
    "target": price_number
}}
"""
    
    async def health_check(self) -> AgentHealth:
        """Perform health check"""
        try:
            start_time = time.time()
            
            # Simple health check request
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Respond with JSON: {\"status\": \"healthy\"}"}],
                    "max_tokens": 10,
                    "response_format": {"type": "json_object"}
                }
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return AgentHealth(
                    agent_type=AgentType.ULTRA_FAST,
                    is_healthy=True,
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                    error_rate=1 - (self.successful_requests / max(self.total_requests, 1)),
                    total_requests=self.total_requests,
                    successful_requests=self.successful_requests,
                    consecutive_failures=self.consecutive_failures
                )
            else:
                raise Exception(f"Health check failed: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            
            return AgentHealth(
                agent_type=AgentType.ULTRA_FAST,
                is_healthy=False,
                last_check=datetime.now(),
                response_time_ms=999999,
                error_rate=1.0,
                total_requests=self.total_requests,
                successful_requests=self.successful_requests,
                consecutive_failures=self.consecutive_failures
            )
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()


class AgentManager:
    """
    Centralized agent management system
    
    Manages multiple AI agents, health monitoring, and request routing
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize agents
        self.standard_agent = StandardAgent(config)
        self.ultra_fast_agent = UltraFastAgent(config)
        
        # Agent registry
        self.agents = {
            AgentType.STANDARD: self.standard_agent,
            AgentType.ULTRA_FAST: self.ultra_fast_agent
        }
        
        # Health monitoring
        self.health_status: Dict[AgentType, AgentHealth] = {}
        self.last_health_check = datetime.now()
        self.health_check_interval = timedelta(minutes=5)
        
        # Request routing
        self.request_count_by_agent: Dict[AgentType, int] = {
            AgentType.STANDARD: 0,
            AgentType.ULTRA_FAST: 0
        }
        
        self.logger.info("AgentManager initialized with 2 agents")
    
    async def initialize(self):
        """Initialize all agents and perform initial health checks"""
        self.logger.info("Initializing agents...")
        
        # Perform initial health checks
        await self._perform_health_checks()
        
        # Verify at least one agent is healthy
        healthy_agents = [
            agent_type for agent_type, health in self.health_status.items()
            if health.is_healthy
        ]
        
        if not healthy_agents:
            raise RuntimeError("No healthy agents available")
        
        self.logger.info(f"Agents initialized. Healthy agents: {[a.value for a in healthy_agents]}")
    
    async def process_message(self, message: MarketMessage, preferred_agent: AgentType) -> AgentResponse:
        """Process message using specified agent with fallback"""
        
        # Check if health check is needed
        if datetime.now() - self.last_health_check > self.health_check_interval:
            asyncio.create_task(self._perform_health_checks())
        
        # Try preferred agent first
        if self._is_agent_healthy(preferred_agent):
            try:
                response = await self._route_to_agent(message, preferred_agent)
                self.request_count_by_agent[preferred_agent] += 1
                return response
            except Exception as e:
                self.logger.warning(f"Preferred agent {preferred_agent.value} failed: {e}")
        
        # Fallback to other healthy agents
        for agent_type in AgentType:
            if agent_type != preferred_agent and self._is_agent_healthy(agent_type):
                try:
                    self.logger.info(f"Falling back to agent: {agent_type.value}")
                    response = await self._route_to_agent(message, agent_type)
                    self.request_count_by_agent[agent_type] += 1
                    return response
                except Exception as e:
                    self.logger.warning(f"Fallback agent {agent_type.value} failed: {e}")
        
        # All agents failed
        error_msg = "All agents unavailable"
        self.logger.error(error_msg)
        
        return AgentResponse(
            success=False,
            data=None,
            processing_time_ms=0,
            agent_type=preferred_agent,
            error_message=error_msg
        )
    
    async def _route_to_agent(self, message: MarketMessage, agent_type: AgentType) -> AgentResponse:
        """Route message to specific agent"""
        agent = self.agents[agent_type]
        return await agent.process_message(message)
    
    def _is_agent_healthy(self, agent_type: AgentType) -> bool:
        """Check if agent is healthy"""
        health = self.health_status.get(agent_type)
        if not health:
            return False
        
        # Consider agent unhealthy if:
        # - Health check failed
        # - Too many consecutive failures
        # - Last health check too old
        time_since_check = datetime.now() - health.last_check
        
        return (
            health.is_healthy and
            health.consecutive_failures < 5 and
            time_since_check < timedelta(minutes=10)
        )
    
    async def _perform_health_checks(self):
        """Perform health checks on all agents"""
        self.logger.debug("Performing agent health checks...")
        
        try:
            health_tasks = [
                agent.health_check() for agent in self.agents.values()
            ]
            
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
            
            for result in health_results:
                if isinstance(result, AgentHealth):
                    self.health_status[result.agent_type] = result
                    self.logger.debug(
                        f"Agent {result.agent_type.value}: "
                        f"healthy={result.is_healthy}, "
                        f"response_time={result.response_time_ms:.1f}ms"
                    )
                else:
                    self.logger.error(f"Health check failed: {result}")
            
            self.last_health_check = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Health check error: {e}")
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics"""
        stats = {
            "request_counts": {
                agent_type.value: count
                for agent_type, count in self.request_count_by_agent.items()
            },
            "health_status": {},
            "total_requests": sum(self.request_count_by_agent.values()),
            "last_health_check": self.last_health_check.isoformat()
        }
        
        # Add health information
        for agent_type, health in self.health_status.items():
            stats["health_status"][agent_type.value] = {
                "is_healthy": health.is_healthy,
                "response_time_ms": health.response_time_ms,
                "error_rate": health.error_rate,
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
                "consecutive_failures": health.consecutive_failures,
                "last_check": health.last_check.isoformat()
            }
        
        return stats
    
    def get_preferred_agent_for_latency(self, target_latency_ms: float) -> AgentType:
        """Get preferred agent based on target latency"""
        
        # Check recent performance
        for agent_type, health in self.health_status.items():
            if (health.is_healthy and 
                health.response_time_ms <= target_latency_ms and
                health.consecutive_failures < 2):
                return agent_type
        
        # Fallback: return fastest healthy agent
        healthy_agents = [
            (agent_type, health.response_time_ms)
            for agent_type, health in self.health_status.items()
            if health.is_healthy
        ]
        
        if healthy_agents:
            fastest_agent = min(healthy_agents, key=lambda x: x[1])
            return fastest_agent[0]
        
        # Final fallback
        return AgentType.ULTRA_FAST
    
    async def cleanup(self):
        """Cleanup all agents"""
        self.logger.info("Cleaning up agents...")
        
        try:
            await self.ultra_fast_agent.cleanup()
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
        
        self.logger.info("Agent cleanup completed")