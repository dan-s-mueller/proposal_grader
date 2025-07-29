"""
LangGraph workflow for multi-role proposal review using configurable agents.
"""

import logging
from typing import Dict, Any, List, Callable
from pathlib import Path
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os
import json

from .state_models import ReviewState
from ..agents.agent_factory import AgentFactory
from ..core.document_processor import DocumentProcessor
from ..core.file_discovery import FileDiscovery


class ReviewWorkflow:
    """LangGraph workflow for multi-role proposal review using configurable agents."""
    
    def __init__(self, openai_client: ChatOpenAI, agent_config: List[str] = None, 
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
        """Create the LangGraph workflow with async agent execution and join node."""
        workflow = StateGraph(ReviewState)
        workflow.add_node("process_documents", self._create_document_processing_node())
        for agent_id in self.agent_config:
            workflow.add_node(agent_id, self._create_agent_node(agent_id))
        workflow.add_node("join_agents", self._join_agents_node)
        workflow.add_node("aggregate_results", self._aggregate_results_node)
        workflow.set_entry_point("process_documents")
        # Fan-out: process_documents → all agents
        for agent_id in self.agent_config:
            workflow.add_edge("process_documents", agent_id)
        # Fan-in: all agents → join_agents
        for agent_id in self.agent_config:
            workflow.add_edge(agent_id, "join_agents")
        # Join to aggregation
        workflow.add_edge("join_agents", "aggregate_results")
        workflow.add_edge("aggregate_results", END)
        return workflow.compile()
    
    def _create_document_processing_node(self) -> Callable:
        """Create a node for processing documents."""
        
        async def process_documents(state: ReviewState) -> ReviewState:
            """Process all documents and load criteria."""
            if self.should_process_docs:
                self.logger.info("Processing documents...")
            else:
                self.logger.info("Using cached processed documents (--no-process-docs flag)")
            
            # Process main proposal
            if self.proposal_dir and self.proposal_dir.exists():
                file_discovery = FileDiscovery()
                main_proposal_path = file_discovery.find_main_proposal(self.proposal_dir)
                
                if main_proposal_path:
                    if self.should_process_docs:
                        processor = DocumentProcessor()
                        proposal_data = processor.process_main_proposal(main_proposal_path)
                    else:
                        # Load from cache only without creating DocumentProcessor
                        proposal_data = self._load_cached_document(main_proposal_path, "main_proposal")
                    
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
                if self.should_process_docs:
                    processor = DocumentProcessor()
                    supporting_docs = processor.process_supporting_docs(self.supporting_dir)
                else:
                    # Load from cache only without creating DocumentProcessor
                    supporting_docs = []
                    for doc_path in FileDiscovery().find_supporting_docs(self.supporting_dir):
                        doc_data = self._load_cached_document(doc_path, "supporting")
                        supporting_docs.append(doc_data)
                
                state.supporting_docs = supporting_docs
                self.logger.info(f"Processed {len(state.supporting_docs)} supporting documents")
            else:
                raise FileNotFoundError("No supporting documents directory found")
            
            # Process solicitation documents and load criteria
            if self.solicitation_dir and self.solicitation_dir.exists():
                if self.should_process_docs:
                    processor = DocumentProcessor()
                    solicitation_data = processor.process_solicitation_docs(self.solicitation_dir)
                else:
                    # Load from cache only without creating DocumentProcessor
                    solicitation_docs = []
                    file_discovery = FileDiscovery()
                    solicitation_files = file_discovery.find_solicitation_docs(self.solicitation_dir)
                    
                    # Iterate through all file types
                    for file_type, file_paths in solicitation_files.items():
                        for doc_path in file_paths:
                            doc_data = self._load_cached_document(doc_path, "solicitation")
                            solicitation_docs.append(doc_data)
                    solicitation_data = {"solicitation_documents": solicitation_docs}
                
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
    
    def _load_cached_document(self, original_path: Path, doc_type: str) -> Dict[str, Any]:
        """Load a cached processed document without creating DocumentProcessor."""
        import json
        
        # Get the processed document path
        if doc_type == "main_proposal":
            # Main proposal is stored in the proposal directory's processed folder
            processed_dir = original_path.parent / "processed"
        elif doc_type == "supporting":
            # Supporting docs are stored in the proposal directory's processed folder
            # original_path is like: documents/proposal/supporting_docs/support/file.pdf
            # We need: documents/proposal/processed/
            processed_dir = original_path.parent.parent.parent / "processed"
        elif doc_type == "solicitation":
            # Solicitation docs are stored in the solicitation directory's processed folder
            # original_path could be like: documents/solicitation/supporting_docs/file.csv
            # or: documents/solicitation/file.pdf
            # We need: documents/solicitation/processed/
            if "supporting_docs" in str(original_path):
                processed_dir = original_path.parent.parent / "processed"
            else:
                processed_dir = original_path.parent / "processed"
        else:
            processed_dir = original_path.parent / "processed"
        
        base_name = original_path.stem
        if doc_type == "supporting":
            processed_path = processed_dir / f"supporting_{base_name}_processed.json"
        elif doc_type == "solicitation":
            processed_path = processed_dir / f"solicitation_{base_name}_processed.json"
        else:
            processed_path = processed_dir / f"{base_name}_processed.json"
        
        if not processed_path.exists():
            raise FileNotFoundError(f"Cached processed document not found: {processed_path}")
        
        try:
            with open(processed_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.logger.info(f"Loaded cached document: {list(data.keys()) if data else 'None'}")
                
                # Extract the standardized structure from the cached wrapper
                if 'content' in data:
                    return data['content']
                else:
                    # Fallback to the data itself if no content wrapper
                    return data
        except Exception as e:
            self.logger.error(f"Failed to load cached document {processed_path}: {e}")
            raise RuntimeError(f"Failed to load cached document {processed_path}: {e}")
    
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
        """Create a node for a specific agent that only updates its own output."""
        async def agent_node(state: ReviewState) -> Dict[str, Any]:
            if not state.documents_processed:
                self.logger.error("Documents not processed, skipping agent review")
                return {}
            if state.processing_error:
                self.logger.error(f"Document processing failed: {state.processing_error}")
                return {}
            self.logger.info(f"Running {agent_id} review")
            try:
                agent = self.agents[agent_id]
                if agent_id == "panel_scorer":
                    output = await agent.review(
                        state.proposal_text,
                        state.supporting_docs,
                        state.criteria,
                        state.solicitation_md,
                        state.output_dir
                    )
                else:
                    output = await agent.review(
                        state.proposal_text,
                        state.supporting_docs,
                        state.criteria,
                        state.solicitation_md
                    )
                self.logger.info(f"{agent_id} review completed")
                return {"agent_outputs": {agent_id: output.dict()}}
            except Exception as e:
                self.logger.error(f"{agent_id} review failed: {e}")
                error_output = {
                    "agent_name": agent_id,
                    "feedback": f"Error in {agent_id} review: {str(e)}",
                    "scores": {},
                    "action_items": [],
                    "confidence": 0.0
                }
                return {"agent_outputs": {agent_id: error_output}}
        return agent_node

    def _join_agents_node(self, state: ReviewState) -> ReviewState:
        """Wait until all agent outputs are present, then proceed."""
        if set(self.agent_config).issubset(set(state.agent_outputs.keys())):
            self.logger.info("All agent reviews complete. Proceeding to aggregation.")
            return state
        else:
            self.logger.info("Waiting for all agent reviews to complete...")
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

        # Add a prominent reviewer scores table
        summary += "## Reviewer Scores Overview\n\n"
        summary += "| Agent | Criterion | Score |\n|---|---|---|\n"
        for output in agent_outputs:
            agent_name = output.get("agent_name", "Unknown").replace('_', ' ').title()
            scores = output.get("scores", {})
            if scores:
                for criterion, score in scores.items():
                    summary += f"| {agent_name} | {criterion} | {score} |\n"
        summary += "\n"

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
        
        # Handle the case where LangGraph returns a dict instead of ReviewState
        if isinstance(final_state, dict):
            self.logger.info("Converting dict to ReviewState object")
            # Convert dict back to ReviewState
            try:
                # Extract the state from the dict (LangGraph wraps it)
                if 'state' in final_state:
                    state_dict = final_state['state']
                else:
                    state_dict = final_state
                
                # Create a new ReviewState from the dict
                review_state = ReviewState(**state_dict)
                self.logger.info("Successfully converted dict to ReviewState")
                return review_state
            except Exception as e:
                self.logger.error(f"Failed to convert dict to ReviewState: {e}")
                # Fallback: create a minimal ReviewState
                return ReviewState(output_dir=output_dir)
        elif hasattr(final_state, '__dict__'):
            self.logger.info(f"Final state attributes: {list(final_state.__dict__.keys())}")
            return final_state
        else:
            self.logger.info(f"Final state is not an object!")
            # Fallback: create a minimal ReviewState
            return ReviewState(output_dir=output_dir)
        
        self.logger.info("Review workflow completed")
        return final_state
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about available agents."""
        return self.agent_factory.get_available_agents() 

def create_workflow_visualization(agents: list = None, output_dir: Path = Path("output")):
    """Create and save a workflow graph visualization as a PNG. Returns the PNG file path or None."""
    import json
    from pathlib import Path
    from langchain_openai import ChatOpenAI

    if agents is None:
        config_path = Path("config/system_config.json")
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            agents = config.get("default_agents", [])
        else:
            agents = ["tech_lead", "business_strategist", "detail_checker", "panel_scorer", "storyteller"]

    mock_client = ChatOpenAI(api_key="mock-key", model="gpt-4o")
    workflow = ReviewWorkflow(
        mock_client,
        agents,
        proposal_dir=Path("documents/proposal"),
        supporting_dir=Path("documents/proposal/supporting_docs"),
        solicitation_dir=Path("documents/solicitation")
    )
    app = workflow.graph
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        png_file = output_dir / "workflow.png"
        png_data = app.get_graph().draw_mermaid_png()
        with open(png_file, "wb") as f:
            f.write(png_data)
        return str(png_file)
    except Exception as e:
        print(f"Error generating workflow visualization: {e}")
        return None 