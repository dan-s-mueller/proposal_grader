"""
Solicitation ingester for processing solicitation documents and extracting evaluation criteria.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI
import os


class SolicitationIngester:
    """Handles processing of solicitation documents and criteria extraction."""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.logger = logging.getLogger(__name__)
    
    def extract_criteria_from_solicitation(self, solicitation_texts: List[Dict[str, Any]], 
                                         technical_description: str, 
                                         faq_guidance: str) -> Dict[str, Any]:
        """
        Extract evaluation criteria from solicitation documents using LLM.
        """
        self.logger.info("Extracting evaluation criteria from solicitation documents")
        
        # Combine all solicitation text
        combined_text = ""
        for doc in solicitation_texts:
            combined_text += f"\n\n--- {doc['file_name']} ---\n{doc['content']}"
        
        # Create prompt for criteria extraction
        system_prompt = """You are an expert at analyzing government solicitations and extracting evaluation criteria.

Your task is to analyze the provided solicitation documents and extract:
1. Evaluation criteria and their descriptions
2. Scoring rubrics and requirements
3. Technical requirements and constraints
4. Business/commercial requirements

Return a structured JSON with the following format:
{
    "evaluation_criteria": [
        {
            "criterion": "string",
            "description": "string", 
            "weight": float,
            "scoring_levels": {
                "unsatisfactory": "string",
                "marginal": "string", 
                "satisfactory": "string",
                "superior": "string"
            }
        }
    ],
    "technical_requirements": ["string"],
    "business_requirements": ["string"],
    "constraints": ["string"]
}"""

        user_prompt = f"""Analyze the following solicitation documents and extract evaluation criteria:

TECHNICAL DESCRIPTION:
{technical_description}

FAQ GUIDANCE:
{faq_guidance}

SOLICITATION DOCUMENTS:
{combined_text}

Extract all evaluation criteria, scoring rubrics, and requirements. Be comprehensive and precise."""

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            # Parse the response
            content = response.choices[0].message.content
            criteria_data = json.loads(content)
            
            self.logger.info(f"Extracted {len(criteria_data.get('evaluation_criteria', []))} evaluation criteria")
            return criteria_data
            
        except Exception as e:
            self.logger.error(f"Failed to extract criteria: {e}")
            # Return a basic structure if extraction fails
            return {
                "evaluation_criteria": [],
                "technical_requirements": [],
                "business_requirements": [],
                "constraints": []
            }
    
    def create_solicitation_markdown(self, solicitation_texts: List[Dict[str, Any]], 
                                   technical_description: str, 
                                   faq_guidance: str) -> str:
        """
        Create a markdown summary of the solicitation.
        """
        markdown_content = "# NASA SBIR Ignite Solicitation\n\n"
        
        if technical_description:
            markdown_content += "## Technical Description\n\n"
            markdown_content += technical_description + "\n\n"
        
        if faq_guidance:
            markdown_content += "## FAQ Guidance\n\n"
            markdown_content += faq_guidance + "\n\n"
        
        if solicitation_texts:
            markdown_content += "## Solicitation Documents\n\n"
            for doc in solicitation_texts:
                markdown_content += f"### {doc['file_name']}\n\n"
                markdown_content += doc['content'][:1000] + "...\n\n"  # Truncate for readability
        
        return markdown_content
    
    def save_solicitation_data(self, criteria_data: Dict[str, Any], 
                             solicitation_md: str, 
                             output_dir: Path):
        """
        Save extracted criteria and solicitation markdown to files.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save criteria JSON
        criteria_path = output_dir / "criteria.json"
        with open(criteria_path, "w", encoding="utf-8") as f:
            json.dump(criteria_data, f, indent=2)
        
        # Save solicitation markdown
        solicitation_path = output_dir / "solicitation.md"
        with open(solicitation_path, "w", encoding="utf-8") as f:
            f.write(solicitation_md)
        
        self.logger.info(f"Saved solicitation data to {output_dir}")
        self.logger.info(f"  - Criteria: {criteria_path}")
        self.logger.info(f"  - Solicitation: {solicitation_path}")
    
    def ingest_solicitation(self, solicitation_dir: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Main method to ingest solicitation documents and extract criteria.
        """
        self.logger.info(f"Ingesting solicitation from {solicitation_dir}")
        
        # Process solicitation documents
        from .document_processor import DocumentProcessor
        processor = DocumentProcessor()
        solicitation_data = processor.process_solicitation_docs(solicitation_dir)
        
        # Extract criteria using LLM
        criteria_data = self.extract_criteria_from_solicitation(
            solicitation_data["solicitation_documents"],
            "",  # No longer using technical_description and faq_guidance separately
            ""
        )
        
        # Create solicitation markdown
        solicitation_md = self.create_solicitation_markdown(
            solicitation_data["solicitation_documents"],
            "",  # No longer using technical_description and faq_guidance separately
            ""
        )
        
        # Save data to output folder
        output_dir = Path("output")  # Always use output/ folder
        self.save_solicitation_data(criteria_data, solicitation_md, output_dir)
        
        return {
            "criteria_data": criteria_data,
            "solicitation_md": solicitation_md,
            "output_dir": output_dir
        } 