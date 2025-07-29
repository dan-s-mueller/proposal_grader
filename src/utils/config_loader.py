"""
Configuration loader for LLM settings and system parameters.
"""

import json
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """Load and manage system configuration."""
    
    def __init__(self, config_path: str = "config/system_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Could not load config from {self.config_path}: {e}")
    
    def get_llm_config(self, context: str = "default") -> Dict[str, Any]:
        """Get LLM configuration for a specific context."""
        config = self.config.get("llm", {}).get(context, {})
        
        if not config:
            # Fallback to default if context not found
            config = self.config.get("llm", {}).get("default", {})
        
        # Ensure we have at least a model
        if "model" not in config:
            raise ValueError(f"No model specified for LLM context: {context}")
        
        return {
            "model": config["model"],
            "temperature": config.get("temperature", 0.5)  # Default temperature if not specified
        }
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.config.get("output", {})
    
    def get_default_agents(self) -> list:
        """Get list of default agents."""
        return self.config.get("default_agents", [])
    
    def list_llm_contexts(self) -> Dict[str, str]:
        """List available LLM contexts."""
        llm_configs = self.config.get("llm", {})
        contexts = {}
        
        for context in llm_configs.keys():
            contexts[context] = f"LLM configuration for {context}"
        
        return contexts 