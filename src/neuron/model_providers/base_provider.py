"""Base class for all model providers in the Neuron framework."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class BaseModelProvider(ABC):
    """Abstract base class defining the interface for all model providers.
    
    Model providers serve as adapters between the Neuron framework and 
    various AI model services or libraries, allowing agents to utilize
    different types of models regardless of their implementation details.
    """
    
    @abstractmethod
    def generate_text(
        self, 
        prompt: str, 
        max_length: int = 1000, 
        temperature: float = 0.7, 
        **kwargs
    ) -> str:
        """Generate text based on the provided prompt.
        
        Args:
            prompt: The input text to generate a continuation for
            max_length: Maximum length of the generated text
            temperature: Controls randomness in generation (higher = more random)
            **kwargs: Additional model-specific parameters
            
        Returns:
            Generated text as a string
        """
        pass
    
    @abstractmethod
    def get_embeddings(
        self, 
        text: Union[str, List[str]], 
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Get vector embeddings for the provided text.
        
        Args:
            text: Single string or list of strings to embed
            **kwargs: Additional model-specific parameters
            
        Returns:
            Vector representation(s) of the input text
        """
        pass
    
    @abstractmethod
    def classify(
        self, 
        text: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Classify the provided text.
        
        Args:
            text: The text to classify
            **kwargs: Additional model-specific parameters
            
        Returns:
            Dictionary containing classification results (e.g., label, score)
        """
        pass
    
    @property
    def capabilities(self) -> List[str]:
        """List the capabilities of this model provider.
        
        Returns:
            List of capability strings (e.g., "text-generation", "embeddings")
        """
        return ["text-generation", "embeddings", "classification"]
    
    def get_token_count(self, text: str) -> int:
        """Get the number of tokens in the provided text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        # Default implementation - should be overridden by specific providers
        # with their own tokenization logic
        return len(text.split())
