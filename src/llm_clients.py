"""
LLM clients for OpenAI and DeepSeek APIs.

This module implements the "Strategy Pattern" to handle different LLM providers.
Each provider has different API formats, but we use a common interface.

Architecture Benefits:
- Easy to add new LLM providers
- Consistent interface regardless of provider
- Error handling and retry logic in one place
- Rate limiting and API quota management

Design Pattern: Strategy + Factory
- Strategy: Common interface for all LLM clients
- Factory: Creates the right client based on provider name
"""

import json
import time
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import openai
from openai import OpenAI


class LLMClient(ABC):
    """
    Abstract base class for LLM clients (Strategy Pattern).
    
    This defines the common interface that all LLM providers must implement.
    By using an abstract base class, we ensure consistency and can easily
    swap between different providers without changing other code.
    
    Why this pattern?
    - Consistent interface for all LLM providers
    - Easy to add new providers (just inherit and implement)
    - Error handling and validation in one place
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with configuration dictionary.
        
        Args:
            config: Dictionary containing API settings (keys, models, etc.)
        
        Raises:
            ValueError: If API key is missing from config
        """
        self.config = config
        self.api_key = config.get('api_key')
        
        # Validate that we have an API key - fail fast if not
        if not self.api_key:
            raise ValueError(f"API key not found in config: {config}")
    
    @abstractmethod
    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """
        Generate text using the LLM - must be implemented by each provider.
        
        Args:
            prompt: The text prompt to send to the LLM
            max_retries: Number of times to retry on failure
            
        Returns:
            Generated text response from the LLM
            
        Raises:
            Exception: If generation fails after all retries
        """
        pass
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM, handling common formatting issues."""
        # Remove markdown formatting if present
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        
        response = response.strip()
        
        # Try to extract JSON from response if it contains other text
        start_markers = ['{', '[']
        end_markers = ['}', ']']
        
        for start_marker, end_marker in zip(start_markers, end_markers):
            start_idx = response.find(start_marker)
            if start_idx != -1:
                # Find the matching closing bracket/brace
                bracket_count = 0
                for i, char in enumerate(response[start_idx:], start_idx):
                    if char == start_marker:
                        bracket_count += 1
                    elif char == end_marker:
                        bracket_count -= 1
                        if bracket_count == 0:
                            response = response[start_idx:i+1]
                            break
                break
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Response excerpt: {response[:200]}...")
            
            # Try to fix common JSON issues
            try:
                # Fix trailing commas
                import re
                fixed_response = re.sub(r',(\s*[}\]])', r'\1', response)
                return json.loads(fixed_response)
            except:
                pass
                
            raise ValueError(f"Invalid JSON response from LLM: {str(e)[:100]}")


class OpenAIClient(LLMClient):
    """Client for OpenAI GPT API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = OpenAI(api_key=self.api_key)
        self.model = config.get('model', 'gpt-3.5-turbo')
        self.max_tokens = config.get('max_tokens', 1000)
        self.temperature = config.get('temperature', 0.7)
    
    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """Generate text using OpenAI API."""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that generates realistic data for calendar applications. Always return valid JSON as requested."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from OpenAI")
                
                return content.strip()
                
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                raise
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"OpenAI API error (attempt {attempt + 1}): {e}")
                    time.sleep(1)
                    continue
                raise
        
        raise Exception(f"Failed to generate text after {max_retries} attempts")


class DeepSeekClient(LLMClient):
    """Client for DeepSeek API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.deepseek.com/v1')
        self.model = config.get('model', 'deepseek-chat')
        self.max_tokens = config.get('max_tokens', 1000)
        self.temperature = config.get('temperature', 0.7)
    
    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """Generate text using DeepSeek API."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {"role": "system", "content": "You are a helpful assistant that generates realistic data for calendar applications. Always return valid JSON as requested."},
                {"role": "user", "content": prompt}
            ],
            'max_tokens': self.max_tokens,
            'temperature': self.temperature
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"Rate limit hit, waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    response.raise_for_status()
                
                response.raise_for_status()
                data = response.json()
                
                if 'choices' not in data or not data['choices']:
                    raise ValueError("Invalid response format from DeepSeek")
                
                content = data['choices'][0]['message']['content']
                if not content:
                    raise ValueError("Empty response from DeepSeek")
                
                return content.strip()
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"DeepSeek API error (attempt {attempt + 1}): {e}")
                    time.sleep(1)
                    continue
                raise
        
        raise Exception(f"Failed to generate text after {max_retries} attempts")


class LLMClientFactory:
    """Factory for creating LLM clients."""
    
    @staticmethod
    def create_client(provider: str, config: Dict[str, Any]) -> LLMClient:
        """Create an LLM client based on the provider.
        
        Args:
            provider: Provider name ('openai' or 'deepseek')
            config: Provider configuration
            
        Returns:
            LLM client instance
        """
        if provider.lower() == 'openai':
            return OpenAIClient(config)
        elif provider.lower() == 'deepseek':
            return DeepSeekClient(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def get_available_providers() -> list:
        """Get list of available providers."""
        return ['openai', 'deepseek'] 