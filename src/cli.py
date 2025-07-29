"""
CLI interface for the multi-agent proposal review system.
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from .core.document_processor import DocumentProcessor
from .core.file_discovery import FileDiscovery
from .workflow.review_graph import ReviewWorkflow, create_workflow_visualization
from .utils.output_formatters import OutputFormatter


def validate_environment():
    """Validate required environment variables."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set in environment.")
        sys.exit(1)
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    return api_key, model


async def run_review_command(args):
    """Run the multi-agent review workflow."""
    print("=== Multi-Agent Proposal Review ===")
    api_key, model = validate_environment()
    from langchain_openai import ChatOpenAI
    client = ChatOpenAI(api_key=api_key, model=model)
    proposal_dir = Path(args.proposal_dir)
    supporting_dir = Path(args.supporting_dir)
    solicitation_dir = Path(args.solicitation_dir)
    output_dir = Path("output")
    print(f"Proposal directory: {proposal_dir}")
    print(f"Supporting docs directory: {supporting_dir}")
    print(f"Solicitation directory: {solicitation_dir}")
    print(f"Output directory: {output_dir}")
    agent_config = args.agents.split(',') if args.agents else None
    print(f"Agent configuration: {agent_config}")
    print(f"Document processing flag: {args.process_docs}")
    workflow = ReviewWorkflow(
        client,
        agent_config,
        proposal_dir=proposal_dir,
        supporting_dir=supporting_dir,
        solicitation_dir=solicitation_dir,
        should_process_docs=args.process_docs
    )
    # Generate workflow visualization BEFORE running the review
    print("Generating workflow visualization...")
    try:
        png_file = create_workflow_visualization(workflow.agent_config, output_dir)
        if png_file:
            print(f"Workflow visualization saved: {png_file}")
        else:
            print("Workflow visualization failed")
    except Exception as e:
        print(f"Workflow visualization failed: {e}")
    print("Starting review workflow...")
    try:
        print("Starting workflow execution")
        final_state = await workflow.run_review(output_dir)
        if not hasattr(final_state, 'documents_processed'):
            print(f"Review workflow failed: Workflow returned unexpected result type")
            sys.exit(1)
        if final_state.processing_error:
            print(f"Review workflow failed: {final_state.processing_error}")
            sys.exit(1)
        output_formatter = OutputFormatter()
        for agent_id in workflow.agent_config:
            agent_output = final_state.agent_outputs.get(agent_id, None)
            if agent_output:
                output_formatter.save_agent_feedback(agent_output, output_dir)
        if final_state.consolidated_scores:
            output_formatter.save_scorecard(final_state.consolidated_scores, output_dir)
        if final_state.summary:
            output_formatter.save_summary(final_state.summary, output_dir)
        if final_state.action_items:
            output_formatter.save_action_items(final_state.action_items, output_dir)
        print("Multi-agent review completed successfully")
        print(f"  - Output directory: {output_dir}")
        print(f"  - Agents used: {', '.join(workflow.agent_config)}")
        print(f"  - Document processing: {'Enabled' if args.process_docs else 'Skipped'}")
    except Exception as e:
        print(f"Review workflow failed: {e}", exc_info=True)
        print(f"\u2717 Review workflow failed: {e}")
        sys.exit(1)


def main():
    """Minimal CLI entry point for multi-agent proposal review."""
    parser = argparse.ArgumentParser(
        description="Multi-agent proposal review system (minimal CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  poetry run review                                    # Run with all agents
  poetry run review --agents tech_lead,panel_scorer   # Run with specific agents
  poetry run review --no-process-docs                 # Skip document processing
        """
    )
    parser.add_argument("--proposal-dir", default="documents/proposal", help="Directory containing main proposal PDF")
    parser.add_argument("--supporting-dir", default="documents/proposal/supporting_docs", help="Directory containing supporting documents (PDF, CSV, MD)")
    parser.add_argument("--solicitation-dir", default="documents/solicitation", help="Directory containing solicitation documents (PDF, CSV, MD)")
    parser.add_argument("--agents", help="Comma-separated list of agents to use (e.g., tech_lead,business_strategist)")
    parser.add_argument("--process-docs", action="store_true", default=True, help="Process documents (default: True)")
    parser.add_argument("--no-process-docs", dest="process_docs", action="store_false", help="Skip document processing (use cached processed documents)")
    args = parser.parse_args()
    import asyncio
    asyncio.run(run_review_command(args))

if __name__ == "__main__":
    main() 