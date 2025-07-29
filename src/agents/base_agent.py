"""
Generic agent class that loads templates and can be configured for different roles.
"""

import logging
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

import os
from langsmith import traceable
from langchain_openai import ChatOpenAI
# from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import HumanMessage, SystemMessage


class AgentOutput(BaseModel):
    """Output model for agent reviews."""
    agent_name: str
    feedback: str
    scores: Dict[str, float] = {}
    action_items: List[str] = []
    confidence: float = 0.0


class BaseAgent:
    """Generic agent class that loads templates and can be configured for different roles."""
    
    def __init__(self, agent_id: str, openai_client: ChatOpenAI):
        self.agent_id = agent_id
        self.client = openai_client
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Load agent template
        self.template = self._load_template(agent_id)
        self.agent_config = self._parse_template(self.template)
        
        # Initialize LangChain LLM
        from ..utils.config_loader import ConfigLoader
        config_loader = ConfigLoader()
        llm_config = config_loader.get_llm_config("agent_reviews")
        
        self.llm = ChatOpenAI(
            model=llm_config["model"],
            temperature=llm_config["temperature"],
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def _load_template(self, agent_id: str) -> str:
        """Load agent template from file."""
        template_path = Path(__file__).parent / "templates" / f"{agent_id}.md"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Agent template not found: {template_path}")
        
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _parse_template(self, template: str) -> Dict[str, Any]:
        """Parse agent template into structured configuration."""
        config = {}
        
        # Extract agent identity
        identity_match = re.search(r'## Agent Identity\n(.*?)\n\n', template, re.DOTALL)
        if identity_match:
            identity_text = identity_match.group(1)
            lines = identity_text.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
        
        # Extract other sections
        sections = {
            'expertise_areas': '## Expertise Areas',
            'critical_focus_areas': '## Critical Focus Areas',
            'output_format': '## Output Format',
            'scoring_criteria': '## Scoring Criteria',
            'review_style': '## Review Style'
        }
        
        for key, section_header in sections.items():
            pattern = f'{section_header}\n(.*?)(?=\n##|\Z)'
            match = re.search(pattern, template, re.DOTALL)
            if match:
                config[key] = match.group(1).strip()
        
        return config
    
    async def review(self, proposal_text: str, supporting_docs: List[Dict[str, Any]], 
               criteria: Dict[str, Any], solicitation_md: str) -> AgentOutput:
        """Perform the review using the agent's template and LLM."""
        
        # Create the prompt content
        system_content = self.template
        human_content = self._create_agent_prompt(proposal_text, supporting_docs, criteria, solicitation_md)
        
        # Create messages directly to avoid format string issues
        # from langchain.schema import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content)
        ]
        
        # Make the LLM call using LangChain async
        response = await self.llm.ainvoke(messages)
        feedback = response.content
        
        # Extract scores
        scores = self._extract_scores_from_feedback(feedback)
        
        # Extract action items
        action_items = self._extract_action_items(feedback)
        
        return AgentOutput(
            agent_name=self.agent_id,
            feedback=feedback,
            scores=scores,
            action_items=action_items,
            confidence=0.8
        )
    
    def _create_agent_prompt(self, proposal_text: str, supporting_docs: List[Dict[str, Any]], 
                            criteria: Dict[str, Any], solicitation_md: str) -> str:
        """
        Create agent-specific prompt using template.
        """
        # Combine supporting docs text
        supporting_text = ""
        for doc in supporting_docs:
            # Extract full_text from the standardized document structure
            if 'full_text' not in doc:
                raise ValueError(f"Document {doc.get('file_name', 'unknown')} missing 'full_text' field. Document structure: {list(doc.keys())}")
            content_text = doc['full_text']
            if not content_text or content_text.strip() == "":
                raise ValueError(f"Document {doc.get('file_name', 'unknown')} has empty or missing content")
            supporting_text += f"\n\n--- {doc['file_name']} ---\n{content_text}"
        
        # Create criteria summary
        criteria_summary = ""
        if criteria.get("evaluation_criteria"):
            criteria_summary = "## Evaluation Criteria\n\n"
            
            # Handle both flat list and nested structure
            evaluation_criteria = criteria["evaluation_criteria"]
            if isinstance(evaluation_criteria, list):
                # Flat list structure
                for criterion in evaluation_criteria:
                    criteria_summary += f"**{criterion['criterion']}** (Weight: {criterion['weight']}%)\n"
                    criteria_summary += f"{criterion['description']}\n\n"
            elif isinstance(evaluation_criteria, dict):
                # Nested structure - flatten it comprehensively
                for section_name, section_data in evaluation_criteria.items():
                    criteria_summary += f"### {section_name.replace('_', ' ').title()}\n\n"
                    if isinstance(section_data, dict):
                        for subsection_name, subsection_data in section_data.items():
                            if isinstance(subsection_data, dict):
                                for criterion_name, criterion_data in subsection_data.items():
                                    if isinstance(criterion_data, dict) and 'description' in criterion_data:
                                        weight = criterion_data.get('weight', 'N/A')
                                        description = criterion_data['description']
                                        criteria_summary += f"**{criterion_name.replace('_', ' ').title()}** (Weight: {weight}%)\n"
                                        criteria_summary += f"{description}\n\n"
        
        # Add scoring guidance if available
        if criteria.get("scoring_guidance"):
            criteria_summary += f"## Scoring Guidance\n\n{criteria['scoring_guidance']}\n\n"
        
        # Build prompt from template
        prompt = f"""# {self.agent_config.get('Name', self.agent_id)} Review

## Your Role
**Focus**: {self.agent_config.get('Focus', '')}
**What you hate**: {self.agent_config.get('Hates', '')}

## Your Expertise
{self.agent_config.get('expertise_areas', '')}

## Critical Focus Areas
{self.agent_config.get('critical_focus_areas', '')}

## Solicitation Context
{solicitation_md}

{criteria_summary}

## Main Proposal
{proposal_text}

## Supporting Documents
{supporting_text}

## Your Review
{self.agent_config.get('output_format', '')}

## Scoring Criteria
{self.agent_config.get('scoring_criteria', '')}

## Review Style
{self.agent_config.get('review_style', '')}

Provide a comprehensive review based on your role focus. Be specific, actionable, and cite evidence from the documents."""

        return prompt
    
    def _extract_scores_from_feedback(self, feedback: str) -> Dict[str, float]:
        """
        Extract scores from feedback based on agent type.
        """
        scores = {}
        
        # Try to extract JSON from the response (for panel scorer)
        if self.agent_id == "panel_scorer":
            try:
                json_match = re.search(r'\{.*\}', feedback, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    score_data = json.loads(json_str)
                    
                    for criterion, data in score_data.items():
                        if isinstance(data, dict) and "score" in data:
                            score = data["score"]
                            if isinstance(score, (int, float)) and 1.0 <= score <= 4.0:
                                scores[criterion] = float(score)
                    
                    return scores
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        # Generic score extraction
        score_patterns = [
            r"(\d+\.?\d*)/4",
            r"score.*?(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*out\s*of\s*4"
        ]
        
        for pattern in score_patterns:
            matches = re.findall(pattern, feedback.lower())
            if matches:
                try:
                    score = float(matches[0])
                    if 1.0 <= score <= 4.0:
                        # Round to nearest 0.5
                        score = round(score * 2) / 2
                        scores[f"{self.agent_id}_score"] = score
                        break
                except ValueError:
                    continue
        
        return scores
    
    def _extract_action_items(self, feedback: str) -> List[str]:
        """
        Extract action items from feedback text.
        """
        action_items = []
        lines = feedback.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*', '1.', '2.', '3.')):
                # Remove bullet/number and clean up
                cleaned = line.lstrip('•-*1234567890. ')
                if cleaned and len(cleaned) > 10:  # Minimum length for action item
                    action_items.append(cleaned)
        
        return action_items 