"""
LangGraph workflow for multi-role proposal review using configurable agents.
"""

import asyncio
import logging
from typing import Dict, Any, List, Callable
from pathlib import Path
from langgraph.graph import StateGraph, END
from openai import OpenAI
import os
import json

from .state_models import ReviewState
from ..agents.agent_factory import AgentFactory
from ..core.document_processor import DocumentProcessor
from ..core.file_discovery import FileDiscovery


class ReviewWorkflow:
    """LangGraph workflow for multi-role proposal review using configurable agents."""
    
    def __init__(self, openai_client: OpenAI, agent_config: List[str] = None, 
                 proposal_dir: Path = None, supporting_dir: Path = None, 
                 solicitation_dir: Path = None, should_process_docs: bool = True):
        self.client = openai_client
        self.logger = logging.getLogger(__name__)
        
        # Store document paths - convert strings to Path objects
        self.proposal_dir = Path(proposal_dir) if proposal_dir else None
        self.supporting_dir = Path(supporting_dir) if supporting_dir else None
        self.solicitation_dir = Path(solicitation_dir) if solicitation_dir else None
        self.should_process_docs = should_process_docs
        
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
        workflow.add_node("process_documents", self._create_document_processing_node())
        
        # Add nodes for each agent
        for agent_id in self.agent_config:
            workflow.add_node(agent_id, self._create_agent_node(agent_id))
        
        # Add join node that waits for all agents
        workflow.add_node("join_agents", self._join_agents_node)
        
        # Add aggregator node
        workflow.add_node("aggregate_results", self._aggregate_results_node)
        
        # Define workflow: process documents first, then agents run sequentially
        workflow.set_entry_point("process_documents")
        
        # Connect agents sequentially instead of concurrently
        previous_node = "process_documents"
        for agent_id in self.agent_config:
            workflow.add_edge(previous_node, agent_id)
            previous_node = agent_id
        
        # Last agent feeds into join node
        workflow.add_edge(previous_node, "join_agents")
        
        # Join node feeds into aggregation
        workflow.add_edge("join_agents", "aggregate_results")
        workflow.add_edge("aggregate_results", END)
        
        return workflow.compile()
    
    def _create_document_processing_node(self) -> Callable:
        """Create a node for processing documents."""
        
        def process_documents(state: ReviewState) -> ReviewState:
            """Process all documents and load criteria."""
            self.logger.info("Processing documents...")
            
            # Process main proposal
            if self.proposal_dir and self.proposal_dir.exists():
                processor = DocumentProcessor()
                file_discovery = FileDiscovery()
                main_proposal_path = file_discovery.find_main_proposal(self.proposal_dir)
                
                if main_proposal_path:
                    proposal_data = processor.process_main_proposal(main_proposal_path)
                    if 'full_text' not in proposal_data:
                        raise ValueError(f"Main proposal processing failed: missing 'full_text' field. Available fields: {list(proposal_data.keys())}")
                    state.proposal_text = proposal_data['full_text']
                    if not state.proposal_text or state.proposal_text.strip() == "":
                        raise ValueError("Main proposal has empty or missing content")
                    self.logger.info(f"Processed main proposal: {len(state.proposal_text)} characters")
                else:
                    raise FileNotFoundError("No main proposal found")
            else:
                raise FileNotFoundError("No proposal directory found")
            
            # Process supporting documents
            if self.supporting_dir and self.supporting_dir.exists():
                processor = DocumentProcessor()
                supporting_docs = processor.process_supporting_docs(self.supporting_dir)
                state.supporting_docs = supporting_docs
                self.logger.info(f"Processed {len(state.supporting_docs)} supporting documents")
            else:
                raise FileNotFoundError("No supporting documents directory found")
            
            # Process solicitation documents and load criteria
            if self.solicitation_dir and self.solicitation_dir.exists():
                processor = DocumentProcessor()
                solicitation_data = processor.process_solicitation_docs(self.solicitation_dir)
                state.solicitation_md = self._create_solicitation_markdown(solicitation_data["solicitation_documents"])
                
                # Load criteria from static file
                criteria_file = self.solicitation_dir / "criteria.json"
                if criteria_file.exists():
                    with open(criteria_file, 'r', encoding='utf-8') as f:
                        state.criteria = json.load(f)
                    self.logger.info(f"Loaded criteria from {criteria_file}")
                else:
                    raise FileNotFoundError(f"criteria.json not found in {self.solicitation_dir}")
            else:
                raise FileNotFoundError("No solicitation directory found")
            
            # Mark documents as processed
            state.documents_processed = True
            self.logger.info("Document processing completed successfully")
            
            return state
        
        return process_documents
    
    def _create_solicitation_markdown(self, solicitation_documents: List[Dict[str, Any]]) -> str:
        """Create a markdown summary of solicitation documents."""
        if not solicitation_documents:
            raise ValueError("No solicitation documents found")
        
        markdown = "# Solicitation Documents Summary\n\n"
        
        for doc in solicitation_documents:
            if 'full_text' not in doc:
                raise ValueError(f"Solicitation document {doc.get('file_name', 'unknown')} missing 'full_text' field. Document structure: {list(doc.keys())}")
            content_text = doc['full_text']
            if not content_text or content_text.strip() == "":
                raise ValueError(f"Solicitation document {doc.get('file_name', 'unknown')} has empty or missing content")
            markdown += f"## {doc['file_name']}\n\n"
            markdown += f"{content_text}\n\n"
        
        return markdown
    
    def _create_agent_node(self, agent_id: str):
        """Create a node for a specific agent."""
        
        async def agent_node(state: ReviewState) -> ReviewState:
            """Agent node that performs review with LangChain tracing."""
            
            # Check if documents were processed successfully
            if not state.documents_processed:
                self.logger.error("Documents not processed, skipping agent review")
                return state
            
            if state.processing_error:
                self.logger.error(f"Document processing failed: {state.processing_error}")
                return state
            
            self.logger.info(f"Running {agent_id} review")
            
            try:
                agent = self.agents[agent_id]
                output = agent.review(
                    state.proposal_text,
                    state.supporting_docs,
                    state.criteria,
                    state.solicitation_md
                )
                
                # Store output in state using dictionary
                state.agent_outputs[agent_id] = output.dict()
                state.completed_agents.append(agent_id)
                self.logger.info(f"{agent_id} review completed")
                
            except Exception as e:
                self.logger.error(f"{agent_id} review failed: {e}")
                state.agent_outputs[agent_id] = {
                    "agent_name": agent_id,
                    "feedback": f"Error in {agent_id} review: {str(e)}",
                    "scores": {},
                    "action_items": [],
                    "confidence": 0.0
                }
                state.completed_agents.append(agent_id)
            
            return state
        
        return agent_node
    
    async def _join_agents_node(self, state: ReviewState) -> ReviewState:
        """Join node that waits for all agents to complete."""
        self.logger.info("Checking if all agents have completed...")
        
        self.logger.info(f"Completed agents: {state.completed_agents}")
        
        if len(state.completed_agents) == len(self.agent_config):
            self.logger.info("All agents completed, proceeding to aggregation")
        else:
            self.logger.info(f"Waiting for {len(self.agent_config) - len(state.completed_agents)} more agents...")
        
        return state
    
    async def _aggregate_results_node(self, state: ReviewState) -> ReviewState:
        """Aggregate results from all agents."""
        self.logger.info("Aggregating results from all agents")
        
        # Collect all agent outputs
        agent_outputs = []
        for agent_id in self.agent_config:
            output = state.agent_outputs.get(agent_id, None)
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
        
        # Debug: Check what type we got back
        self.logger.info(f"Workflow returned type: {type(final_state)}")
        if hasattr(final_state, '__dict__'):
            self.logger.info(f"Final state attributes: {list(final_state.__dict__.keys())}")
        else:
            self.logger.info(f"Final state is not an object: {final_state}")
        
        self.logger.info("Review workflow completed")
        return final_state
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about available agents."""
        return self.agent_factory.get_available_agents() 