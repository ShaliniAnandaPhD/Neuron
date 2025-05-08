"""Hugging Face Transformers integration for the Neuron framework."""

import os
from typing import Any, Dict, List, Optional, Union, Tuple

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    AutoModel, 
    pipeline,
    PreTrainedTokenizer,
    PreTrainedModel
)

from neuron.model_providers.base_provider import BaseModelProvider


class HuggingFaceProvider(BaseModelProvider):
    """Model provider that uses Hugging Face Transformers models.
    
    This provider enables Neuron agents to utilize thousands of open-source 
    models from the Hugging Face Hub, allowing for specialized agents with
    different capabilities and resource requirements.
    """
    
    def __init__(
        self, 
        model_id: str, 
        task: str = "text-generation", 
        device: Optional[str] = None,
        quantization: Optional[str] = None,
        model_kwargs: Dict[str, Any] = None,
        cache_dir: Optional[str] = None,
    ):
        """Initialize the Hugging Face model provider.
        
        Args:
            model_id: Hugging Face model ID (e.g., "mistralai/Mistral-7B-Instruct-v0.2")
            task: The task this model will be used for (e.g., "text-generation", 
                  "sentiment-analysis", "feature-extraction")
            device: Device to run the model on ("cpu", "cuda", "cuda:0", etc.)
            quantization: Quantization method to use (e.g., "4bit", "8bit") or None
            model_kwargs: Additional keyword arguments for model loading
            cache_dir: Directory to cache downloaded models
        """
        self.model_id = model_id
        self.task = task
        self.model_kwargs = model_kwargs or {}
        self.cache_dir = cache_dir
        
        # Determine device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        # Handle quantization
        if quantization:
            if quantization == "4bit":
                self.model_kwargs["load_in_4bit"] = True
            elif quantization == "8bit":
                self.model_kwargs["load_in_8bit"] = True
            
        # Initialize appropriate models based on task
        self._initialize_models()
            
    def _initialize_models(self):
        """Initialize the appropriate models based on the task."""
        # Set up task-specific initialization
        if self.task == "text-generation":
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_id, 
                    cache_dir=self.cache_dir
                )
                
                # Some models require special handling for tokenizer
                if not self.tokenizer.pad_token:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_id,
                    device_map=self.device if self.device.startswith("cuda") else "auto",
                    cache_dir=self.cache_dir,
                    **self.model_kwargs
                )
                self.pipeline = None
                
            except Exception as e:
                # Fallback to pipeline API if direct loading fails
                print(f"Warning: Direct model loading failed, falling back to pipeline: {e}")
                self.tokenizer = None
                self.model = None
                self.pipeline = pipeline(
                    self.task,
                    model=self.model_id,
                    device=0 if self.device == "cuda" else -1 if self.device == "cpu" else self.device,
                    cache_dir=self.cache_dir,
                    **self.model_kwargs
                )
        elif self.task == "feature-extraction":
            # For embeddings, load model directly
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                cache_dir=self.cache_dir
            )
            self.model = AutoModel.from_pretrained(
                self.model_id,
                device_map=self.device if self.device.startswith("cuda") else "auto",
                cache_dir=self.cache_dir,
                **self.model_kwargs
            )
            self.pipeline = None
        else:
            # For other tasks, use the pipeline API
            self.tokenizer = None
            self.model = None
            self.pipeline = pipeline(
                self.task,
                model=self.model_id,
                device=0 if self.device == "cuda" else -1 if self.device == "cpu" else self.device,
                cache_dir=self.cache_dir,
                **self.model_kwargs
            )
    
    def generate_text(
        self, 
        prompt: str, 
        max_length: int = 1000, 
        temperature: float = 0.7, 
        **kwargs
    ) -> str:
        """Generate text using the loaded model.
        
        Args:
            prompt: Input text to generate from
            max_length: Maximum length of the generated text
            temperature: Controls randomness (higher = more random)
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text as a string
            
        Raises:
            ValueError: If the provider is not configured for text generation
        """
        if self.task != "text-generation":
            raise ValueError(f"This provider is configured for {self.task}, not text-generation")
        
        # Use pipeline if available
        if self.pipeline is not None:
            result = self.pipeline(
                prompt, 
                max_length=max_length,
                temperature=temperature,
                **kwargs
            )
            if isinstance(result, list):
                return result[0]["generated_text"]
            return result
        
        # Otherwise use model directly
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        generation_kwargs = {
            "max_length": max_length,
            "temperature": temperature,
            "do_sample": temperature > 0,
            **kwargs
        }
        
        # Handle potential kwargs conflicts
        if "num_return_sequences" not in generation_kwargs:
            generation_kwargs["num_return_sequences"] = 1
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs.get("attention_mask", None),
                **generation_kwargs
            )
            
        # Decode and return the generated text
        if outputs.shape[0] > 1:
            return [self.tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    def get_embeddings(
        self, 
        text: Union[str, List[str]], 
        **kwargs
    ) -> Union[List[float], List[List[float]]]:
        """Get embeddings for the provided text.
        
        Args:
            text: Text(s) to generate embeddings for
            **kwargs: Additional embedding parameters
            
        Returns:
            Vector representation(s) of the input text
            
        Raises:
            ValueError: If the provider is not configured for embeddings
        """
        if self.task != "feature-extraction":
            raise ValueError(f"This provider is configured for {self.task}, not feature-extraction")
        
        # Use pipeline if available
        if self.pipeline is not None:
            return self.pipeline(text, **kwargs)
        
        # Otherwise use model directly
        is_list = isinstance(text, list)
        texts = text if is_list else [text]
        
        # Tokenize and get embeddings
        inputs = self.tokenizer(
            texts, 
            padding=True, 
            truncation=True, 
            return_tensors="pt"
        ).to(self.device)
        
        with torch.no_grad():
            # Get the model's output
            outputs = self.model(**inputs, **kwargs)
            
            # Most embedding models return the last hidden state
            if hasattr(outputs, "last_hidden_state"):
                # Mean pooling - take average of all tokens
                embeddings = outputs.last_hidden_state.mean(dim=1)
            else:
                # If no last_hidden_state, use the first output
                embeddings = outputs[0].mean(dim=1)
                
        # Convert to list and return
        result = embeddings.cpu().numpy().tolist()
        return result if is_list else result[0]
    
    def classify(
        self, 
        text: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Classify the provided text.
        
        Args:
            text: The text to classify
            **kwargs: Additional classification parameters
            
        Returns:
            Dictionary with classification results (e.g., label, score)
            
        Raises:
            ValueError: If the provider is not configured for classification
        """
        if self.task not in ["text-classification", "sentiment-analysis"]:
            raise ValueError(f"This provider is configured for {self.task}, not classification")
        
        if self.pipeline is None:
            raise ValueError("Classification requires using the pipeline API")
        
        result = self.pipeline(text, **kwargs)
        
        # Ensure consistent return format
        if isinstance(result, list):
            if len(result) == 1:
                return result[0]
            return {"results": result}
        return result
    
    def get_token_count(self, text: str) -> int:
        """Get the number of tokens in the provided text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        if self.tokenizer is not None:
            return len(self.tokenizer.encode(text))
        
        # Fallback to approximate count if no tokenizer
        return super().get_token_count(text)

    @property
    def capabilities(self) -> List[str]:
        """List the capabilities of this model provider.
        
        Returns:
            List of capability strings
        """
        capabilities = []
        
        if self.task == "text-generation":
            capabilities.append("text-generation")
        elif self.task == "feature-extraction":
            capabilities.append("embeddings")
        elif self.task in ["text-classification", "sentiment-analysis"]:
            capabilities.append("classification")
            
        return capabilities


class MistralProvider(HuggingFaceProvider):
    """Specialized provider for Mistral models with optimized settings."""
    
    def __init__(
        self, 
        model_version: str = "7B-Instruct-v0.2",
        device: Optional[str] = None,
        quantization: Optional[str] = None,
        **kwargs
    ):
        """Initialize a Mistral model provider with optimized settings.
        
        Args:
            model_version: Mistral model version (e.g., "7B-Instruct-v0.2")
            device: Device to run on ("cpu", "cuda", etc.)
            quantization: Quantization method ("4bit", "8bit", or None)
            **kwargs: Additional model provider arguments
        """
        model_id = f"mistralai/Mistral-{model_version}"
        super().__init__(
            model_id=model_id,
            task="text-generation",
            device=device,
            quantization=quantization,
            **kwargs
        )
        
    def format_prompt(self, message: str) -> str:
        """Format a prompt in Mistral's chat template.
        
        Args:
            message: The message to format
            
        Returns:
            Formatted prompt string
        """
        return f"<s>[INST] {message} [/INST]"


class LlamaProvider(HuggingFaceProvider):
    """Specialized provider for Llama models with optimized settings."""
    
    def __init__(
        self, 
        model_version: str = "2-7b-chat-hf",
        device: Optional[str] = None,
        quantization: Optional[str] = None,
        **kwargs
    ):
        """Initialize a Llama model provider with optimized settings.
        
        Args:
            model_version: Llama model version (e.g., "2-7b-chat-hf")
            device: Device to run on ("cpu", "cuda", etc.)
            quantization: Quantization method ("4bit", "8bit", or None)
            **kwargs: Additional model provider arguments
        """
        model_id = f"meta-llama/Llama-{model_version}"
        super().__init__(
            model_id=model_id,
            task="text-generation",
            device=device,
            quantization=quantization,
            **kwargs
        )
