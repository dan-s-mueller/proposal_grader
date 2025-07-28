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
    
    def extract_criteria_from_solicitation(self, solicitation_documents: List[Dict[str, Any]], 
                                        technical_description: str, faq_guidance: str) -> Dict[str, Any]:
        """Extract evaluation criteria from solicitation documents using LLM."""
        
        # Load LLM configuration
        from ..utils.config_loader import ConfigLoader
        config_loader = ConfigLoader()
        llm_config = config_loader.get_llm_config("solicitation_processing")
        
        # Combine all solicitation content
        all_content = []
        for doc in solicitation_documents:
            all_content.append(f"Document: {doc['file_name']}\n{doc['content']}\n")
        
        combined_content = "\n".join(all_content)
        
        prompt = f"""
        Extract evaluation criteria from the following solicitation documents.
        
        Solicitation Documents:
        {combined_content}
        
        Technical Description:
        {technical_description}
        
        FAQ Guidance:
        {faq_guidance}
        
        Please extract and structure the evaluation criteria in JSON format with the following structure:
        {{
            "evaluation_criteria": [
                {{
                    "criterion": "Criterion name",
                    "description": "Detailed description",
                    "weight": "High/Medium/Low",
                    "max_score": 4.0
                }}
            ],
            "scoring_guidance": "General guidance on scoring",
            "technical_requirements": ["requirement1", "requirement2"],
            "business_requirements": ["requirement1", "requirement2"]
        }}
        
        Focus on:
        1. Technical evaluation criteria
        2. Business/commercial evaluation criteria
        3. Innovation and feasibility criteria
        4. Team qualifications and experience
        5. Commercialization potential
        """
        
        response = self.client.chat.completions.create(
            model=llm_config["model"],
            messages=[
                {"role": "system", "content": "You are an expert at analyzing SBIR/STTR solicitations and extracting evaluation criteria."},
                {"role": "user", "content": prompt}
            ],
            temperature=llm_config["temperature"]
        )
        
        try:
            # Try to parse JSON response
            criteria_text = response.choices[0].message.content
            criteria_data = json.loads(criteria_text)
            return criteria_data
        except json.JSONDecodeError:
            # Fallback to structured text if JSON parsing fails
            self.logger.warning("Failed to parse JSON response, using fallback structure")
            return {
                "evaluation_criteria": [],
                "scoring_guidance": criteria_text,
                "technical_requirements": [],
                "business_requirements": []
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