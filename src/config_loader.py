"""
Configuration loader for calendar data generation.

This module handles loading configuration from YAML files and environment variables.
It follows the "Configuration as Code" pattern where all settings are externalized.

Why this approach?
- Separates configuration from code (12-factor app principle)
- Easy to modify settings without changing code
- Supports different environments (dev, prod)
- Secure handling of API keys via environment variables
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """
    Handles loading and managing configuration from YAML and environment variables.
    
    This class implements the "Configuration Hierarchy" pattern:
    1. Load base config from YAML file
    2. Override with environment variables (for secrets and deployment-specific settings)
    
    This ensures sensitive data (API keys) never go into version control.
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the config loader with a two-step loading process.
        
        Args:
            config_path: Path to the YAML configuration file
        
        Process:
        1. Load .env file (for local development)
        2. Load YAML config (for application settings)
        3. Override YAML with environment variables (for security)
        """
        # Step 1: Load environment variables from .env file (if exists)
        # This is crucial for local development - keeps API keys out of code
        load_dotenv()
        
        # Step 2: Load the main configuration structure
        self.config_path = Path(config_path)
        self.config = self._load_yaml_config()
        
        # Step 3: Override sensitive values with environment variables
        # This allows deployment flexibility and security
        self._override_with_env_vars()
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    def _override_with_env_vars(self):
        """Override configuration with environment variables where available."""
        # API Keys
        if os.getenv('OPENAI_API_KEY'):
            self.config.setdefault('api', {}).setdefault('openai', {})['api_key'] = os.getenv('OPENAI_API_KEY')
        
        if os.getenv('DEEPSEEK_API_KEY'):
            self.config.setdefault('api', {}).setdefault('deepseek', {})['api_key'] = os.getenv('DEEPSEEK_API_KEY')
        
        # Can add more API keys here for other LLM providers ... 
        
        # Redis Configuration
        if os.getenv('REDIS_HOST'):
            self.config.setdefault('database', {}).setdefault('redis', {})['host'] = os.getenv('REDIS_HOST')
        
        if os.getenv('REDIS_PORT'):
            self.config.setdefault('database', {}).setdefault('redis', {})['port'] = int(os.getenv('REDIS_PORT'))
        
        if os.getenv('REDIS_PASSWORD'):
            self.config.setdefault('database', {}).setdefault('redis', {})['password'] = os.getenv('REDIS_PASSWORD')
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration key (e.g., 'api.openai.model')
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_api_config(self, provider: str) -> Dict[str, Any]:
        """Get API configuration for a specific provider.
        
        Args:
            provider: API provider name ('openai' or 'deepseek')
            
        Returns:
            API configuration dictionary
        """
        return self.get(f'api.{provider}', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return self.get('database.redis', {})
    
    def get_generation_config(self) -> Dict[str, Any]:
        """Get data generation configuration."""
        return self.get('generation', {})
    
    def get_prompts(self) -> Dict[str, str]:
        """Get LLM prompts configuration."""
        return self.get('prompts', {}) 