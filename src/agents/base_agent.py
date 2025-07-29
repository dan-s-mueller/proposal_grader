"""
Generic agent class that loads templates and can be configured for different roles.
"""

import logging
import re
import json
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from ..utils.config_loader import ConfigLoader
import random


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


class PanelScorerAgent(BaseAgent):
    """Specialized agent for panel_scorer: runs async LLM calls per criterion and aggregates results."""

    async def review(self, proposal_text: str, supporting_docs: list, criteria: dict, solicitation_md: str, output_dir: Path = Path('output'), max_concurrent: int = 2):
        self.logger.info("[PanelScorerAgent] Starting review. Flattening criteria...")
        self.logger.info(f"[PanelScorerAgent] Top-level criteria keys: {list(criteria.keys())}")
        if "types" in criteria:
            criteria = criteria["types"]
        config_loader = ConfigLoader()
        llm_config = config_loader.get_llm_config("panel_scorer")
        llm = ChatOpenAI(
            model=llm_config["model"],
            temperature=llm_config["temperature"],
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        def flatten_criteria(criteria):
            flat = []
            for crit_type, type_data in criteria.items():
                if crit_type == "metadata":
                    continue
                type_weight = type_data.get("weight", None)
                for category, cat_data in type_data.get("categories", {}).items():
                    cat_weight = cat_data.get("weight", None)
                    for subcat, subcat_data in cat_data.get("sub_categories", {}).items():
                        flat.append({
                            "type": crit_type,
                            "category": category,
                            "sub_category": subcat,
                            "description": subcat_data.get("description", ""),
                            "scoring": subcat_data.get("scoring", {}),
                            "weight": subcat_data.get("weight", cat_weight if cat_weight is not None else type_weight)
                        })
            return flat
        eval_criteria = flatten_criteria(criteria)
        self.logger.info(f"[PanelScorerAgent] {len(eval_criteria)} criteria to score.")
        system_content = self.template
        supporting_text = ""
        for doc in supporting_docs:
            supporting_text += f"\n\n--- {doc.get('file_name', 'doc')} ---\n{doc.get('full_text', '')}"
        context = f"## Solicitation Context\n{solicitation_md}\n\n## Main Proposal\n{proposal_text}\n\n## Supporting Documents\n{supporting_text}"
        import re, json, asyncio
        # Load batching/retry config from system_config.json
        config_loader = ConfigLoader()
        scorer_config = config_loader.config.get('llm', {}).get('panel_scorer', {})
        batch_config = scorer_config.get('batch', {})
        batch_size = batch_config.get('batch_size', 2)
        warmup_count = batch_config.get('warmup_count', 4)
        warmup_delay = batch_config.get('warmup_delay', 3)
        base_delay = batch_config.get('base_delay', 5)
        max_retries = batch_config.get('max_retries', 8)
        self.logger.info(f"[PanelScorerAgent] Batch config: batch_size={batch_size}, warmup_count={warmup_count}, warmup_delay={warmup_delay}, base_delay={base_delay}, max_retries={max_retries}")
        semaphore = asyncio.Semaphore(max_concurrent)
        def safe_json_loads(s):
            # Replace single backslashes not followed by valid escape with double backslash
            s = re.sub(r'(?<!\\)\\(?!["/bfnrtu])', r'\\', s)
            try:
                return json.loads(s)
            except json.JSONDecodeError as e:
                self.logger.error(f"[PanelScorerAgent] JSON decode error: {e}\nRaw: {s}")
                raise
        async def score_criterion(criterion):
            crit_id = f"{criterion['type']}|{criterion['category']}|{criterion['sub_category']}"
            for attempt in range(max_retries):
                async with semaphore:
                    self.logger.info(f"[PanelScorerAgent] Scoring: {crit_id} (attempt {attempt+1})")
                    scoring = criterion.get("scoring", {})
                    scoring_lines = []
                    for label, desc in zip(["1.0", "2.0", "3.0", "4.0"], [scoring.get("unsatisfactory", ""), scoring.get("marginal", ""), scoring.get("satisfactory", ""), scoring.get("superior", "")]):
                        scoring_lines.append(f"- {label}: {desc}")
                    scoring_text = "\n".join(scoring_lines)
                    prompt = f"""
You are a panel reviewer. Score ONLY the following criterion:

Type: {criterion['type']}
Category: {criterion['category']}
Sub-Category: {criterion['sub_category']}

Description: {criterion['description']}

Scoring Rubric:
{scoring_text}

Return your answer as a JSON object with the following fields:
{{
  "score": float (1.0-4.0, 0.5 increments),
  "evidence": "string",
  "reasoning": "string",
  "improvements": "string"
}}

{self.agent_config.get('scoring_criteria', '')}
{self.agent_config.get('review_style', '')}

{context}
"""
                    messages = [SystemMessage(content=system_content), HumanMessage(content=prompt)]
                    try:
                        response = await llm.ainvoke(messages)
                        feedback = response.content
                        json_match = re.search(r'\{.*\}', feedback, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                            score_data = safe_json_loads(json_str)
                            if isinstance(score_data, dict) and "score" in score_data:
                                self.logger.info(f"[PanelScorerAgent] Success for {crit_id}")
                                return criterion, score_data, feedback
                    except Exception as e:
                        err_str = str(e).lower()
                        if "rate limit" in err_str or "429" in err_str:
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                            self.logger.warning(f"[PanelScorerAgent] Rate limit for {crit_id}, retrying in {delay:.2f}s (attempt {attempt+1})")
                            await asyncio.sleep(delay)
                            continue
                        self.logger.error(f"[PanelScorerAgent] Exception for {crit_id} on attempt {attempt+1}: {e}")
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        self.logger.warning(f"[PanelScorerAgent] Retry {crit_id} after {delay:.2f}s...")
                        await asyncio.sleep(delay)
            self.logger.error(f"[PanelScorerAgent] Failed to score {crit_id} after {max_retries} attempts.")
            return criterion, {"score": None, "evidence": "", "reasoning": "Could not parse response", "improvements": ""}, feedback if 'feedback' in locals() else ""
        # Serial warmup for first N criteria
        results = []
        self.logger.info(f"[PanelScorerAgent] Serial warmup for first {warmup_count} criteria...")
        for crit in eval_criteria[:warmup_count]:
            self.logger.info(f"[PanelScorerAgent] Warmup scoring: {crit['type']}|{crit['category']}|{crit['sub_category']}")
            result = await score_criterion(crit)
            results.append(result)
            self.logger.info(f"[PanelScorerAgent] Waiting {warmup_delay}s after warmup criterion...")
            await asyncio.sleep(warmup_delay)
        # Then process the rest in batches
        for i in range(warmup_count, len(eval_criteria), batch_size):
            batch = eval_criteria[i:i+batch_size]
            self.logger.info(f"[PanelScorerAgent] Processing batch {(i-warmup_count)//batch_size+1} ({len(batch)} criteria)...")
            batch_results = await asyncio.gather(*(score_criterion(crit) for crit in batch))
            results.extend(batch_results)
            if i + batch_size < len(eval_criteria):
                self.logger.info(f"[PanelScorerAgent] Waiting {base_delay}s before next batch...")
                await asyncio.sleep(base_delay)
        # Aggregate
        scores_json = {f"{c['type']}|{c['category']}|{c['sub_category']}": data for c, data, _ in results}
        # Build markdown table with weights and total score
        table_header = "| Type | Category | Sub-Category | Weight | Score | Evidence | Reasoning | Improvements |\n|---|---|---|---|---|---|---|---|"
        table_rows = []
        total_score = 0.0
        total_weight = 0.0
        improvements = []
        for crit, data, _ in results:
            weight = crit.get('weight', 0.0) or 0.0
            score = data.get('score', 0.0) or 0.0
            if score:
                total_score += score * weight
            total_weight += weight
            improvements.append(data.get('improvements', '').strip())
            row = f"| {crit['type']} | {crit['category']} | {crit['sub_category']} | {weight:.2f} | {score} | {data.get('evidence', '').replace('|', ' ')} | {data.get('reasoning', '').replace('|', ' ')} | {data.get('improvements', '').replace('|', ' ')} |"
            table_rows.append(row)
        markdown_table = table_header + "\n" + "\n".join(table_rows)
        # Calculate normalized total score (weighted average)
        normalized_score = total_score / total_weight if total_weight else 0.0
        # Summarize top recommended actions (improvements)
        top_actions = [imp for imp in improvements if imp and imp.lower() not in ("no significant improvements needed", "no significant improvements are necessary as the team already demonstrates outstanding qualifications and experience relevant to the nasa subtopic.")]
        top_actions = list(dict.fromkeys(top_actions))  # Remove duplicates, preserve order
        top_actions = top_actions[:5]  # Show top 5
        actions_md = "\n".join([f"- {a}" for a in top_actions]) if top_actions else "No major improvements recommended."
        summary = f"## Panel Reviewer Composite Score\n\n**Weighted Total Score:** {normalized_score:.2f} (out of 4.0)\n\n## Top Recommended Actions\n\n{actions_md}\n"
        # Save markdown table to file
        output_dir.mkdir(parents=True, exist_ok=True)
        table_path = output_dir / "panel_scorer_results.md"
        with open(table_path, "w", encoding="utf-8") as f:
            f.write(f"# Panel Scorer Results\n\n{summary}\n\n{markdown_table}\n\n<details><summary>Raw JSON</summary>\n\n```json\n{json.dumps(scores_json, indent=2)}\n```\n</details>\n\nMarkdown table saved to: {table_path}")
        # Compose feedback: summary + markdown table + raw JSON
        feedback = f"### Panel Scorer Results\n\n{summary}\n{markdown_table}\n\n<details><summary>Raw JSON</summary>\n\n```json\n{json.dumps(scores_json, indent=2)}\n```\n</details>\n\nMarkdown table saved to: {table_path}"
        return AgentOutput(
            agent_name=self.agent_id,
            feedback=feedback,
            scores={"panel_scorer_composite": normalized_score},
            action_items=top_actions,
            confidence=0.9
        ) 