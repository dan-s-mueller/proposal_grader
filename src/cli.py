"""
CLI interface for the multi-agent proposal review system.
"""

import asyncio
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from openai import OpenAI
from langsmith import traceable

from .core.document_processor import DocumentProcessor
from .core.file_discovery import FileDiscovery
from .core.solicitation_ingester import SolicitationIngester
from .workflow.review_graph import ReviewWorkflow
from .utils.output_formatters import OutputFormatter
from .agents.agent_factory import AgentFactory
from .utils.config_loader import ConfigLoader
from .utils.workflow_visualizer import create_workflow_visualization


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )


def validate_environment():
    """Validate required environment variables."""
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set in environment.")
        sys.exit(1)
    
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    return api_key, model


async def ingest_solicitation_command(args):
    """Command to ingest solicitation documents."""
    print("=== Solicitation Ingestion ===")
    
    # Validate environment
    api_key, model = validate_environment()
    client = OpenAI(api_key=api_key)
    
    # Setup paths
    solicitation_dir = Path(args.solicitation_dir)
    output_dir = Path(args.output_dir)
    
    # Create ingester and process
    ingester = SolicitationIngester(client)
    
    try:
        result = ingester.ingest_solicitation(solicitation_dir, output_dir)
        print(f"✓ Solicitation ingested successfully")
        print(f"  - Criteria: {len(result['criteria_data'].get('evaluation_criteria', []))} criteria extracted")
        print(f"  - Output: {output_dir}")
    except Exception as e:
        print(f"✗ Solicitation ingestion failed: {e}")
        sys.exit(1)


async def run_review_command(args):
    """Command to run the multi-agent review."""
    print("=== Multi-Agent Proposal Review ===")
    
    # Validate environment
    api_key, model = validate_environment()
    client = OpenAI(api_key=api_key)
    
    # Setup paths
    proposal_dir = Path(args.proposal_dir)
    supporting_dir = Path(args.supporting_dir)
    solicitation_dir = Path(args.solicitation_dir)
    output_dir = Path("output")  # Always use output/ folder
    
    # Parse agent configuration
    agent_config = args.agents.split(',') if args.agents else None
    
    # Create workflow with document paths and processing flag
    workflow = ReviewWorkflow(
        client, 
        agent_config, 
        proposal_dir=proposal_dir,
        supporting_dir=supporting_dir,
        solicitation_dir=solicitation_dir,
        should_process_docs=args.process_docs
    )
    
    # Run the review workflow
    try:
        final_state = await workflow.run_review(output_dir)
        
        if final_state.processing_error:
            print(f"✗ Document processing failed: {final_state.processing_error}")
            sys.exit(1)
        
        # Save outputs
        output_formatter = OutputFormatter()
        
        # Save individual agent feedback
        for agent_id in workflow.agent_config:
            agent_output = final_state.agent_outputs.get(agent_id, None)
            if agent_output:
                output_formatter.save_agent_feedback(agent_output, output_dir)
        
        # Save consolidated results
        if final_state.consolidated_scores:
            output_formatter.save_scorecard(final_state.consolidated_scores, output_dir)
        
        if final_state.summary:
            output_formatter.save_summary(final_state.summary, output_dir)
        
        if final_state.action_items:
            output_formatter.save_action_items(final_state.action_items, output_dir)
        
        print("✓ Multi-agent review completed successfully")
        print(f"  - Output directory: {output_dir}")
        print(f"  - Agents used: {', '.join(workflow.agent_config)}")
        print(f"  - Document processing: {'Enabled' if args.process_docs else 'Skipped'}")
        
    except Exception as e:
        print(f"✗ Review workflow failed: {e}")
        sys.exit(1)


async def list_agents_command(args):
    """Command to list available agents."""
    print("=== Available Agents ===")
    
    # Validate environment
    api_key, model = validate_environment()
    client = OpenAI(api_key=api_key)
    
    # Create agent factory and get available agents
    agent_factory = AgentFactory(client)
    available_agents = agent_factory.get_available_agents()
    
    if not available_agents:
        print("No agents found.")
        return
    
    print(f"Found {len(available_agents)} agents:\n")
    
    for agent_id, agent_info in available_agents.items():
        print(f"Agent ID: {agent_id}")
        print(f"  Name: {agent_info.get('name', 'N/A')}")
        print(f"  Focus: {agent_info.get('focus', 'N/A')}")
        print()


async def visualize_workflow_command(args):
    """Command to visualize the workflow structure."""
    try:
        # Parse agent configuration
        agent_config = args.agents.split(',') if args.agents else None
        
        # Create visualization (always saves to output/)
        png_file, svg_file = create_workflow_visualization(agent_config)
        
        if png_file or svg_file:
            print("✅ Workflow visualization completed successfully")
        else:
            print("❌ Failed to create workflow visualization")
            
    except Exception as e:
        print(f"❌ Workflow visualization failed: {e}")
        sys.exit(1)


async def show_config_command(args):
    """Command to show system configuration."""
    print("=== System Configuration ===")
    
    try:
        config_loader = ConfigLoader()
        
        print("\nLLM Configurations:")
        for context in ["agent_reviews", "solicitation_processing", "default"]:
            try:
                config = config_loader.get_llm_config(context)
                print(f"  {context}:")
                print(f"    Model: {config.get('model', 'N/A')}")
                print(f"    Temperature: {config.get('temperature', 'N/A')}")
            except Exception as e:
                print(f"  {context}: Error - {e}")
        
        print("\nOutput Configuration:")
        output_config = config_loader.get_output_config()
        for key, value in output_config.items():
            print(f"  {key}: {value}")
        
        print("\nDefault Agents:")
        default_agents = config_loader.get_default_agents()
        print(f"  {', '.join(default_agents)}")
        
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)


def run_review():
    """Wrapper function for poetry run review."""
    import asyncio
    import sys
    
    # Create a mock args object with review command
    class MockArgs:
        def __init__(self):
            self.command = "review"
            self.proposal_dir = "documents/proposal"
            self.supporting_dir = "documents/proposal/supporting_docs"
            self.solicitation_dir = "documents/solicitation"
            self.agents = None
            self.process_docs = True
    
    args = MockArgs()
    asyncio.run(run_review_command(args))

def run_list_agents():
    """Wrapper function for poetry run list-agents."""
    import asyncio
    import sys
    
    class MockArgs:
        def __init__(self):
            self.command = "list-agents"
    
    args = MockArgs()
    asyncio.run(list_agents_command(args))

def run_show_config():
    """Wrapper function for poetry run show-config."""
    import asyncio
    import sys
    
    class MockArgs:
        def __init__(self):
            self.command = "show-config"
    
    args = MockArgs()
    asyncio.run(show_config_command(args))

def run_visualize_workflow():
    """Wrapper function for poetry run visualize-workflow."""
    import asyncio
    import sys
    
    class MockArgs:
        def __init__(self):
            self.command = "visualize-workflow"
            self.agents = None
    
    args = MockArgs()
    asyncio.run(visualize_workflow_command(args))

def main():
    """Main CLI entry point."""
    # Get the script name to determine which command to run
    script_name = sys.argv[0].split('/')[-1] if '/' in sys.argv[0] else sys.argv[0]
    
    # Map script names to commands
    script_to_command = {
        'review': 'review',
        'list-agents': 'list-agents', 
        'show-config': 'show-config',
        'visualize-workflow': 'visualize-workflow',
        'ingest-solicitation': 'ingest-solicitation'
    }
    
    # If we're running as a script, set the command
    if script_name in script_to_command:
        command = script_to_command[script_name]
        # Insert the command as the first argument
        sys.argv.insert(1, command)
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Multi-Agent Proposal Review System")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Ingest solicitation command
    ingest_parser = subparsers.add_parser("ingest-solicitation", help="Ingest solicitation documents")
    ingest_parser.add_argument("--solicitation-dir", default="documents/solicitation", 
                              help="Directory containing solicitation documents")
    ingest_parser.add_argument("--output-dir", default="solicitation_md", 
                              help="Output directory for extracted criteria")
    
    # Review command
    review_parser = subparsers.add_parser("review", help="Run multi-agent proposal review")
    review_parser.add_argument("--proposal-dir", default="documents/proposal", 
                              help="Directory containing main proposal")
    review_parser.add_argument("--supporting-dir", default="documents/proposal/supporting_docs", 
                              help="Directory containing supporting documents")
    review_parser.add_argument("--solicitation-dir", default="documents/solicitation", 
                              help="Directory containing solicitation documents")
    review_parser.add_argument("--agents", 
                              help="Comma-separated list of agents to use (e.g., tech_lead,business_strategist)")
    review_parser.add_argument("--process-docs", action="store_true", default=True,
                              help="Process documents (default: True)")
    review_parser.add_argument("--no-process-docs", dest="process_docs", action="store_false",
                              help="Skip document processing (use cached processed documents)")
    
    # List agents command
    list_parser = subparsers.add_parser("list-agents", help="List available agents")
    
    # Visualize workflow command
    visualize_parser = subparsers.add_parser("visualize-workflow", help="Visualize the workflow structure")
    visualize_parser.add_argument("--agents", 
                                 help="Comma-separated list of agents to include")
    
    # Show config command
    config_parser = subparsers.add_parser("show-config", help="Show system configuration")
    
    args = parser.parse_args()
    
    # Run the appropriate command
    if args.command == "review":
        asyncio.run(run_review_command(args))
    elif args.command == "list-agents":
        list_agents_command(args)
    elif args.command == "show-config":
        show_config_command(args)
    elif args.command == "visualize-workflow":
        asyncio.run(visualize_workflow_command(args))
    elif args.command == "ingest-solicitation":
        ingest_solicitation_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main() 