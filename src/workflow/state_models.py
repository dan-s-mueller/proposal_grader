"""
State models for the LangGraph review workflow.
"""

from typing import Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field
from pathlib import Path

def merge_dicts(left, right, **kwargs):
    if left is None:
        left = {}
    if right is None:
        right = {}
    merged = dict(left)
    merged.update(right)
    return merged

class ReviewState(BaseModel):
    """State model for the review workflow."""
    
    # Document processing status
    documents_processed: bool = Field(default=False, description="Whether documents have been processed")
    processing_error: Optional[str] = Field(default=None, description="Error during document processing")
    
    # Input data (populated after document processing)
    proposal_text: str = Field(default="", description="Main proposal text")
    supporting_docs: List[Dict[str, Any]] = Field(default_factory=list, description="Supporting document contents")
    criteria: Dict[str, Any] = Field(default_factory=dict, description="Evaluation criteria from solicitation")
    solicitation_md: str = Field(default="", description="Solicitation markdown")
    
    # Agent outputs (stored as dictionary to handle dynamic agents)
    agent_outputs: Annotated[Dict[str, Any], merge_dicts] = Field(default_factory=dict, description="Agent outputs by agent_id")
    
    # Aggregated results
    all_agent_outputs: List[Dict[str, Any]] = Field(default_factory=list, description="All agent outputs")
    consolidated_scores: Dict[str, float] = Field(default_factory=dict, description="Consolidated scores")
    summary: str = Field(default="", description="Consolidated summary")
    action_items: List[str] = Field(default_factory=list, description="Consolidated action items")
    
    # Output paths
    output_dir: Path = Field(description="Output directory for results")
    
    class Config:
        arbitrary_types_allowed = True
    
    def is_all_agents_complete(self, expected_agents: List[str]) -> bool:
        """Check if all expected agents have completed."""
        return set(expected_agents).issubset(set(self.agent_outputs.keys())) 