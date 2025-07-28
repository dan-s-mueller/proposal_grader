"""
Utility for visualizing LangGraph workflows.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple
from openai import OpenAI

from ..workflow.review_graph import ReviewWorkflow


def visualize_workflow_graph(agents: Optional[List[str]] = None, 
                           output_dir: Path = Path(".")) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate a visual graph of the LangGraph workflow.
    
    Args:
        agents: List of agent IDs to include in workflow. If None, uses default from config.
        output_dir: Directory to save the output files.
    
    Returns:
        Tuple of (png_file_path, svg_file_path) or (None, None) if failed.
    """
    # Load default agents if not provided
    if agents is None:
        config_path = Path("config/system_config.json")
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
            agents = config.get("default_agents", [])
        else:
            agents = ["tech_lead", "business_strategist", "detail_checker", "panel_scorer", "storyteller"]
    
    print(f"Creating workflow graph with agents: {', '.join(agents)}")
    
    # Create a mock OpenAI client (we don't need real API calls for visualization)
    mock_client = OpenAI(api_key="mock-key")
    
    # Create the workflow with mock paths
    workflow = ReviewWorkflow(
        mock_client, 
        agents,
        proposal_dir=Path("documents/proposal"),
        supporting_dir=Path("documents/proposal/supporting_docs"),
        solicitation_dir=Path("documents/solicitation")
    )
    
    # Get the compiled graph
    app = workflow.graph
    
    # Generate the visualization using LangGraph's built-in method
    try:
        print("Generating workflow visualization...")
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get the graph and generate PNG
        graph = app.get_graph()
        png_data = graph.draw_mermaid_png()
        
        # Save as PNG
        png_file = output_dir / "workflow.png"
        with open(png_file, "wb") as f:
            f.write(png_data)
        print(f"✅ Workflow graph saved as: {png_file}")
        
        # Also save as SVG if available
        try:
            svg_data = graph.draw_mermaid_svg()
            svg_file = output_dir / "workflow.svg"
            with open(svg_file, "wb") as f:
                f.write(svg_data)
            print(f"✅ Workflow graph saved as: {svg_file}")
            return str(png_file), str(svg_file)
        except Exception:
            # SVG not available, just return PNG
            return str(png_file), None
        
    except Exception as e:
        print(f"❌ Error generating graph: {e}")
        return None, None


def create_workflow_visualization(agents: Optional[List[str]] = None, 
                                output_dir: Path = Path("output")) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a visualization of the workflow graph.
    
    Args:
        agents: List of agent IDs to include in workflow
        output_dir: Directory to save the output files (defaults to output/)
    
    Returns:
        Tuple of (png_file_path, svg_file_path) or (None, None) if failed
    """
    print("=== Workflow Visualization ===")
    
    # Always use output/ folder
    output_dir = Path("output")
    
    # Generate visualization
    png_file, svg_file = visualize_workflow_graph(agents, output_dir)
    
    if png_file:
        print(f"✅ Workflow graph saved as: {png_file}")
    
    if svg_file:
        print(f"✅ Workflow graph saved as: {svg_file}")
    
    print("\n📊 Workflow visualization complete!")
    if png_file:
        print(f"   PNG: {png_file}")
    if svg_file:
        print(f"   SVG: {svg_file}")
    
    print(f"\nOpen {output_dir}/workflow.png to view the workflow.")
    
    return png_file, svg_file 