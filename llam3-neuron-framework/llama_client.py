#!/usr/bin/env python3
"""
LLaMA3 API Client
Handles all interactions with LLaMA3 model API
"""

import asyncio
import aiohttp
import time
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
import backoff
import tiktoken
from contextlib import asynccontextmanager

from config import (
    LLAMA3_API_ENDPOINT,
    LLAMA3_API_KEY,
    LLAMA3_CONTEXT_WINDOW,
    LLAMA3_MAX_GENERATION,
    REQUEST_TIMEOUT,
    TOKEN_RATE_LIMIT,
    get_logger
)
from models import ErrorDetail

# ============================================================================
# LOGGING
# ============================================================================

logger = get_logger(__name__)

# ============================================================================
# EXCEPTIONS
# ============================================================================

class LLaMAAPIError(Exception):
    """Base exception for LLaMA API errors"""
    pass

class LLaMATimeoutError(LLaMAAPIError):
    """Timeout error when calling LLaMA API"""
    pass

class LLaMATokenLimitError(LLaMAAPIError):
    """Token limit exceeded error"""
    pass

class LLaMAConnectionError(LLaMAAPIError):
    """Connection error to LLaMA API"""
    pass

# ============================================================================
# TOKEN COUNTING
# ============================================================================

class TokenCounter:
    """
    Token counter for LLaMA3 models
    Uses tiktoken for accurate token counting
    """
    
    def __init__(self):
        """Initialize token counter with LLaMA3 tokenizer"""
        try:
            # Use the appropriate encoding for LLaMA models
            # Note: You may need to use a specific LLaMA tokenizer
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Failed to load tokenizer: {e}. Using approximate counting.")
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Fallback to approximate counting (1 token ≈ 4 characters)
            return len(text) // 4
    
    def truncate_to_limit(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to fit within token limit
        
        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens
            
        Returns:
            Truncated text
        """
        tokens = self.count_tokens(text)
        if tokens <= max_tokens:
            return text
        
        if self.encoding:
            # Precise truncation using tokenizer
            encoded = self.encoding.encode(text)
            truncated = encoded[:max_tokens]
            return self.encoding.decode(truncated)
        else:
            # Approximate truncation
            ratio = max_tokens / tokens
            char_limit = int(len(text) * ratio * 0.95)  # 95% to be safe
            return text[:char_limit]

# ============================================================================
# RATE LIMITER
# ============================================================================

class TokenRateLimiter:
    """
    Token-based rate limiter for API calls
    Implements a sliding window rate limiting algorithm
    """
    
    def __init__(self, tokens_per_minute: int = TOKEN_RATE_LIMIT):
        """
        Initialize rate limiter
        
        Args:
            tokens_per_minute: Maximum tokens per minute
        """
        self.tokens_per_minute = tokens_per_minute
        self.window_start = time.time()
        self.tokens_used = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int):
        """
        Acquire tokens from rate limiter
        
        Args:
            tokens: Number of tokens to acquire
            
        Raises:
            LLaMATokenLimitError: If tokens would exceed rate limit
        """
        async with self._lock:
            current_time = time.time()
            window_elapsed = current_time - self.window_start
            
            # Reset window if a minute has passed
            if window_elapsed >= 60:
                self.window_start = current_time
                self.tokens_used = 0
            
            # Check if we can acquire tokens
            if self.tokens_used + tokens > self.tokens_per_minute:
                # Calculate wait time
                wait_time = 60 - window_elapsed
                logger.warning(f"Rate limit reached. Need to wait {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                
                # Reset window after waiting
                self.window_start = time.time()
                self.tokens_used = 0
            
            # Acquire tokens
            self.tokens_used += tokens
            logger.debug(f"Acquired {tokens} tokens. Used: {self.tokens_used}/{self.tokens_per_minute}")

# ============================================================================
# LLAMA CLIENT
# ============================================================================

@dataclass
class LLaMARequest:
    """
    Request to LLaMA3 API
    
    Attributes:
        prompt: Input prompt
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Top-p sampling parameter
        frequency_penalty: Frequency penalty
        presence_penalty: Presence penalty
        stop_sequences: Stop sequences
        stream: Whether to stream response
        system_prompt: System prompt for instruction
    """
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    system_prompt: Optional[str] = None

@dataclass
class LLaMAResponse:
    """
    Response from LLaMA3 API
    
    Attributes:
        text: Generated text
        tokens_used: Total tokens used (prompt + completion)
        prompt_tokens: Tokens in prompt
        completion_tokens: Tokens in completion
        finish_reason: Reason for completion (stop, length, etc.)
        model: Model used
        latency_ms: API latency in milliseconds
    """
    text: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    model: str
    latency_ms: float

class LLaMAClient:
    """
    Client for interacting with LLaMA3 API
    Handles connection pooling, retries, and rate limiting
    """
    
    def __init__(self, 
                 api_endpoint: str = LLAMA3_API_ENDPOINT,
                 api_key: str = LLAMA3_API_KEY,
                 max_retries: int = 3,
                 timeout: float = REQUEST_TIMEOUT):
        """
        Initialize LLaMA client
        
        Args:
            api_endpoint: API endpoint URL
            api_key: API authentication key
            max_retries: Maximum number of retries
            timeout: Request timeout in seconds
        """
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        self.token_counter = TokenCounter()
        self.rate_limiter = TokenRateLimiter()
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Create HTTP session"""
        if not self._session:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Connections per host
                ttl_dns_cache=300  # DNS cache timeout
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
            logger.info("LLaMA client connected")
    
    async def close(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("LLaMA client disconnected")
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, LLaMATimeoutError),
        max_tries=3,
        max_time=30
    )
    async def generate(self, request: LLaMARequest) -> LLaMAResponse:
        """
        Generate text using LLaMA3 API
        
        Args:
            request: LLaMA request parameters
            
        Returns:
            LLaMA response
            
        Raises:
            LLaMAAPIError: If API call fails
        """
        if not self._session:
            await self.connect()
        
        # Prepare prompt with system message if provided
        if request.system_prompt:
            full_prompt = f"System: {request.system_prompt}\n\nUser: {request.prompt}\n\nAssistant:"
        else:
            full_prompt = request.prompt
        
        # Count tokens
        prompt_tokens = self.token_counter.count_tokens(full_prompt)
        max_total_tokens = min(
            prompt_tokens + request.max_tokens,
            LLAMA3_CONTEXT_WINDOW
        )
        
        # Check token limits
        if prompt_tokens > LLAMA3_CONTEXT_WINDOW:
            raise LLaMATokenLimitError(
                f"Prompt tokens ({prompt_tokens}) exceed context window ({LLAMA3_CONTEXT_WINDOW})"
            )
        
        # Acquire rate limit tokens
        estimated_total_tokens = prompt_tokens + request.max_tokens
        await self.rate_limiter.acquire(estimated_total_tokens)
        
        # Prepare API request
        api_request = {
            "prompt": full_prompt,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stop": request.stop_sequences or [],
            "stream": request.stream
        }
        
        # Make API call
        start_time = time.time()
        
        try:
            if request.stream:
                return await self._generate_stream(api_request, prompt_tokens, start_time)
            else:
                return await self._generate_batch(api_request, prompt_tokens, start_time)
                
        except asyncio.TimeoutError:
            raise LLaMATimeoutError(f"Request timed out after {self.timeout} seconds")
        except aiohttp.ClientError as e:
            raise LLaMAConnectionError(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in LLaMA generation: {e}")
            raise LLaMAAPIError(f"API error: {str(e)}")
    
    async def _generate_batch(self, 
                             api_request: Dict[str, Any], 
                             prompt_tokens: int,
                             start_time: float) -> LLaMAResponse:
        """
        Generate text in batch mode (non-streaming)
        
        Args:
            api_request: API request payload
            prompt_tokens: Number of prompt tokens
            start_time: Request start time
            
        Returns:
            LLaMA response
        """
        async with self._session.post(
            f"{self.api_endpoint}/completions",
            json=api_request
        ) as response:
            # Check response status
            if response.status != 200:
                error_text = await response.text()
                raise LLaMAAPIError(f"API error {response.status}: {error_text}")
            
            # Parse response
            data = await response.json()
            
            # Extract response data
            generated_text = data["choices"][0]["text"]
            completion_tokens = data["usage"]["completion_tokens"]
            total_tokens = data["usage"]["total_tokens"]
            finish_reason = data["choices"][0]["finish_reason"]
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            return LLaMAResponse(
                text=generated_text,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                finish_reason=finish_reason,
                model=data.get("model", "llama3"),
                latency_ms=latency_ms
            )
    
    async def _generate_stream(self,
                              api_request: Dict[str, Any],
                              prompt_tokens: int,
                              start_time: float) -> AsyncGenerator[str, None]:
        """
        Generate text in streaming mode
        
        Args:
            api_request: API request payload
            prompt_tokens: Number of prompt tokens
            start_time: Request start time
            
        Yields:
            Generated text chunks
        """
        async with self._session.post(
            f"{self.api_endpoint}/completions",
            json=api_request
        ) as response:
            # Check response status
            if response.status != 200:
                error_text = await response.text()
                raise LLaMAAPIError(f"API error {response.status}: {error_text}")
            
            # Stream response
            completion_tokens = 0
            async for line in response.content:
                if line:
                    try:
                        # Parse SSE format
                        if line.startswith(b"data: "):
                            data = json.loads(line[6:])
                            if "choices" in data:
                                chunk = data["choices"][0].get("text", "")
                                if chunk:
                                    completion_tokens += self.token_counter.count_tokens(chunk)
                                    yield chunk
                    except json.JSONDecodeError:
                        continue
            
            # Log final metrics
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Stream completed: {completion_tokens} tokens in {latency_ms:.1f}ms"
            )
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            LLaMAAPIError: If API call fails
        """
        if not self._session:
            await self.connect()
        
        # Count tokens for rate limiting
        total_tokens = sum(self.token_counter.count_tokens(text) for text in texts)
        await self.rate_limiter.acquire(total_tokens)
        
        # Make API call
        try:
            async with self._session.post(
                f"{self.api_endpoint}/embeddings",
                json={"input": texts}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise LLaMAAPIError(f"API error {response.status}: {error_text}")
                
                data = await response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                
                return embeddings
                
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise LLaMAAPIError(f"Embedding error: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if LLaMA API is healthy
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            if not self._session:
                await self.connect()
            
            async with self._session.get(
                f"{self.api_endpoint}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# ============================================================================
# FACTORY FUNCTION
# ============================================================================

@asynccontextmanager
async def create_llama_client(**kwargs) -> LLaMAClient:
    """
    Create LLaMA client with context manager
    
    Args:
        **kwargs: Client configuration options
        
    Yields:
        LLaMA client instance
    """
    client = LLaMAClient(**kwargs)
    try:
        await client.connect()
        yield client
    finally:
        await client.close()