"""
Agent factory for creating and managing agents based on configuration.
"""

import logging
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from .base_agent import BaseAgent


class AgentFactory:
    """Factory for creating and managing agents."""
    
    def __init__(self, openai_client: ChatOpenAI):
        self.client = openai_client
        self.logger = logging.getLogger(__name__)
        self.agents = {}
    
    def create_agent(self, agent_id: str) -> BaseAgent:
        """
        Create an agent instance.
        """
        if agent_id not in self.agents:
            self.agents[agent_id] = BaseAgent(agent_id, self.client)
            self.logger.info(f"Created agent: {agent_id}")
        
        return self.agents[agent_id]
    
    def create_agents_from_config(self, agent_config: List[str]) -> Dict[str, BaseAgent]:
        """
        Create multiple agents from a configuration list.
        """
        agents = {}
        
        for agent_id in agent_config:
            try:
                agents[agent_id] = self.create_agent(agent_id)
            except Exception as e:
                self.logger.error(f"Failed to create agent {agent_id}: {e}")
                continue
        
        return agents
    
    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get dictionary of available agent templates with their information.
        """
        import os
        from pathlib import Path
        
        templates_dir = Path(__file__).parent / "templates"
        available = {}
        
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.md"):
                agent_id = template_file.stem
                
                # Try to load agent info from template
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        template_content = f.read()
                    
                    # Extract basic info from template
                    lines = template_content.split('\n')
                    name = agent_id.replace('_', ' ').title()
                    focus = ""
                    hates = ""
                    
                    for i, line in enumerate(lines):
                        if line.startswith('**Focus**:'):
                            focus = line.replace('**Focus**:', '').strip()
                        elif line.startswith('**What you hate**:'):
                            hates = line.replace('**What you hate**:', '').strip()
                    
                    available[agent_id] = {
                        "name": name,
                        "focus": focus,
                        "hates": hates,
                        "template_path": str(template_file)
                    }
                except Exception as e:
                    # Fallback if template can't be parsed
                    available[agent_id] = {
                        "name": agent_id.replace('_', ' ').title(),
                        "focus": "Not specified",
                        "hates": "Not specified",
                        "template_path": str(template_file)
                    }
        
        return available
    
    def validate_agent_config(self, agent_config: List[str]) -> Dict[str, Any]:
        """
        Validate agent configuration.
        """
        available_agents = self.get_available_agents()
        validation_result = {
            "valid": True,
            "agents": {},
            "errors": [],
            "warnings": []
        }
        
        for agent_id in agent_config:
            if agent_id in available_agents:
                validation_result["agents"][agent_id] = "available"
            else:
                validation_result["agents"][agent_id] = "not_found"
                validation_result["errors"].append(f"Agent template not found: {agent_id}")
                validation_result["valid"] = False
        
        if not agent_config:
            validation_result["errors"].append("No agents specified")
            validation_result["valid"] = False
        
        return validation_result 