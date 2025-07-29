"""
State models for the LangGraph review workflow.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pathlib import Path


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
    agent_outputs: Dict[str, Any] = Field(default_factory=dict, description="Agent outputs by agent_id")
    
    # Track completed agents to avoid concurrent update conflicts
    completed_agents: List[str] = Field(default_factory=list, description="List of completed agent IDs")
    
    # Aggregated results
    all_agent_outputs: List[Dict[str, Any]] = Field(default_factory=list, description="All agent outputs")
    consolidated_scores: Dict[str, float] = Field(default_factory=dict, description="Consolidated scores")
    summary: str = Field(default="", description="Consolidated summary")
    action_items: List[str] = Field(default_factory=list, description="Consolidated action items")
    
    # Output paths
    output_dir: Path = Field(description="Output directory for results")
    
    class Config:
        arbitrary_types_allowed = True 