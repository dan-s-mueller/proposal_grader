"""
LangGraph workflow for multi-role proposal review using configurable agents.
"""

import asyncio
import logging
from typing import Dict, Any, List
from pathlib import Path
from langgraph.graph import StateGraph, END
from openai import OpenAI
import os

from .state_models import ReviewState
from ..agents.agent_factory import AgentFactory
from ..core.document_processor import DocumentProcessor
from ..core.file_discovery import FileDiscovery
from ..core.solicitation_ingester import SolicitationIngester


class ReviewWorkflow:
    """LangGraph workflow for multi-role proposal review using configurable agents."""
    
    def __init__(self, openai_client: OpenAI, agent_config: List[str] = None, 
                 proposal_dir: Path = None, supporting_dir: Path = None, 
                 solicitation_dir: Path = None):
        self.client = openai_client
        self.logger = logging.getLogger(__name__)
        
        # Store document paths
        self.proposal_dir = proposal_dir
        self.supporting_dir = supporting_dir
        self.solicitation_dir = solicitation_dir
        
        # Default agent configuration
        if agent_config is None:
            agent_config = ["tech_lead", "business_strategist", "detail_checker", "panel_scorer", "storyteller"]
        
        # Create agent factory and validate configuration
        self.agent_factory = AgentFactory(openai_client)
        validation = self.agent_factory.validate_agent_config(agent_config)
        
        if not validation["valid"]:
            raise ValueError(f"Invalid agent configuration: {validation['errors']}")
        
        # Create agents
        self.agents = self.agent_factory.create_agents_from_config(agent_config)
        self.agent_config = agent_config
        
        # Create the workflow graph
        self.graph = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        
        # Create the state graph
        workflow = StateGraph(ReviewState)
        
        # Add document processing node
        workflow.add_node("process_documents", self._process_documents_node)
        
        # Add nodes for each agent
        for agent_id in self.agent_config:
            workflow.add_node(agent_id, self._create_agent_node(agent_id))
        
        # Add join node that waits for all agents
        workflow.add_node("join_agents", self._join_agents_node)
        
        # Add aggregator node
        workflow.add_node("aggregate_results", self._aggregate_results_node)
        
        # Define workflow: process documents first, then all agents run concurrently
        workflow.set_entry_point("process_documents")
        
        # All agents start after document processing
        for agent_id in self.agent_config:
            workflow.add_edge("process_documents", agent_id)
        
        # All agents feed into join node
        for agent_id in self.agent_config:
            workflow.add_edge(agent_id, "join_agents")
        
        # Join node feeds into aggregation
        workflow.add_edge("join_agents", "aggregate_results")
        workflow.add_edge("aggregate_results", END)
        
        return workflow.compile()
    
    async def _process_documents_node(self, state: ReviewState) -> ReviewState:
        """Process documents and populate state with parsed data."""
        self.logger.info("Processing documents...")
        
        try:
            # Validate file structure
            file_discovery = FileDiscovery()
            validation = file_discovery.validate_file_structure(
                self.proposal_dir, 
                self.supporting_dir, 
                self.solicitation_dir
            )
            
            if validation["errors"]:
                state.processing_error = f"File validation failed: {validation['errors']}"
                return state
            
            # Process main proposal
            processor = DocumentProcessor()
            main_proposal_path = file_discovery.find_main_proposal(self.proposal_dir)
            
            if not main_proposal_path:
                state.processing_error = "Main proposal not found"
                return state
            
            proposal_data = processor.process_main_proposal(main_proposal_path)
            state.proposal_text = proposal_data["full_text"]
            
            # Process supporting documents
            supporting_docs = processor.process_supporting_docs(self.supporting_dir)
            state.supporting_docs = supporting_docs
            
            # Process solicitation if available
            if self.solicitation_dir and self.solicitation_dir.exists():
                ingester = SolicitationIngester(self.client)
                solicitation_data = ingester.ingest_solicitation(self.solicitation_dir, Path("solicitation_md"))
                state.criteria = solicitation_data.get("criteria_data", {})
                state.solicitation_md = solicitation_data.get("solicitation_md", "")
            else:
                # Use default criteria if no solicitation
                state.criteria = {"evaluation_criteria": []}
                state.solicitation_md = ""
            
            state.documents_processed = True
            self.logger.info("Document processing completed successfully")
            
        except Exception as e:
            state.processing_error = f"Document processing failed: {str(e)}"
            self.logger.error(f"Document processing failed: {e}")
        
        return state
    
    def _create_agent_node(self, agent_id: str):
        """Create a node function for a specific agent."""
        
        async def agent_node(state: ReviewState) -> ReviewState:
            """Agent review node."""
            self.logger.info(f"Running {agent_id} review")
            
            # Check if documents were processed successfully
            if not state.documents_processed or state.processing_error:
                error_msg = state.processing_error or "Documents not processed"
                setattr(state, f"{agent_id}_output", {
                    "agent_name": agent_id,
                    "feedback": f"Error: {error_msg}",
                    "scores": {},
                    "action_items": [],
                    "confidence": 0.0
                })
                return state
            
            try:
                agent = self.agents[agent_id]
                output = await agent.review(
                    state.proposal_text,
                    state.supporting_docs,
                    state.criteria,
                    state.solicitation_md
                )
                
                # Store output in state
                setattr(state, f"{agent_id}_output", output.dict())
                self.logger.info(f"{agent_id} review completed")
                
            except Exception as e:
                self.logger.error(f"{agent_id} review failed: {e}")
                setattr(state, f"{agent_id}_output", {
                    "agent_name": agent_id,
                    "feedback": f"Error in {agent_id} review: {str(e)}",
                    "scores": {},
                    "action_items": [],
                    "confidence": 0.0
                })
            
            return state
        
        return agent_node
    
    async def _join_agents_node(self, state: ReviewState) -> ReviewState:
        """Join node that waits for all agents to complete."""
        self.logger.info("Checking if all agents have completed...")
        
        completed_agents = []
        for agent_id in self.agent_config:
            if hasattr(state, f"{agent_id}_output") and getattr(state, f"{agent_id}_output") is not None:
                completed_agents.append(agent_id)
        
        self.logger.info(f"Completed agents: {completed_agents}")
        
        if len(completed_agents) == len(self.agent_config):
            self.logger.info("All agents completed, proceeding to aggregation")
        else:
            self.logger.info(f"Waiting for {len(self.agent_config) - len(completed_agents)} more agents...")
        
        return state
    
    async def _aggregate_results_node(self, state: ReviewState) -> ReviewState:
        """Aggregate results from all agents."""
        self.logger.info("Aggregating results from all agents")
        
        # Collect all agent outputs
        agent_outputs = []
        for agent_id in self.agent_config:
            output = getattr(state, f"{agent_id}_output", None)
            if output:
                agent_outputs.append(output)
        
        state.all_agent_outputs = agent_outputs
        
        # Consolidate scores
        consolidated_scores = {}
        for output in agent_outputs:
            if output.get("scores"):
                consolidated_scores.update(output["scores"])
        
        state.consolidated_scores = consolidated_scores
        
        # Consolidate action items
        all_action_items = []
        for output in agent_outputs:
            if output.get("action_items"):
                all_action_items.extend(output["action_items"])
        
        state.action_items = all_action_items
        
        # Create summary
        summary = self._create_summary(agent_outputs, consolidated_scores, state.action_items)
        state.summary = summary
        
        self.logger.info("Results aggregation completed")
        return state
    
    def _create_summary(self, agent_outputs: list, consolidated_scores: Dict[str, float], action_items: List[str]) -> str:
        """Create a consolidated summary of all reviews."""
        summary = "# Multi-Agent Review Summary\n\n"
        
        # Add agent-specific summaries
        for output in agent_outputs:
            agent_name = output.get("agent_name", "Unknown")
            feedback = output.get("feedback", "")
            scores = output.get("scores", {})
            
            summary += f"## {agent_name.replace('_', ' ').title()}\n\n"
            summary += f"{feedback}\n\n"
            
            if scores:
                summary += "**Scores:**\n"
                for criterion, score in scores.items():
                    summary += f"- {criterion}: {score}\n"
                summary += "\n"
        
        # Add consolidated scores
        if consolidated_scores:
            summary += "## Consolidated Scores\n\n"
            for criterion, score in consolidated_scores.items():
                summary += f"- **{criterion}**: {score}\n"
            summary += "\n"
        
        # Add action items
        if action_items:
            summary += "## Action Items\n\n"
            for i, item in enumerate(action_items, 1):
                summary += f"{i}. {item}\n"
        
        return summary
    
    async def run_review(self, output_dir: Path) -> ReviewState:
        """Run the complete review workflow."""
        self.logger.info("Starting review workflow")
        
        # Initialize state
        initial_state = ReviewState(
            output_dir=output_dir
        )
        
        # Run the workflow
        final_state = await self.graph.ainvoke(initial_state)
        
        self.logger.info("Review workflow completed")
        return final_state
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about available agents."""
        return self.agent_factory.get_available_agents() 