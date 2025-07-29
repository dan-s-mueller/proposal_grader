"""
Output formatters for saving review results to files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List


class OutputFormatter:
    """Handles formatting and saving review outputs."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def save_role_feedback(self, role_outputs: List[Dict[str, Any]], output_dir: Path):
        """
        Save individual role feedback to markdown files.
        """
        feedback_dir = output_dir / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        
        for output in role_outputs:
            role_name = output.get("role_name", "unknown")
            feedback = output.get("feedback", "")
            
            # Create markdown file
            filename = f"{role_name.lower()}.md"
            filepath = feedback_dir / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {role_name} Review\n\n")
                f.write(feedback)
            
            self.logger.info(f"Saved {role_name} feedback to {filepath}")
    
    def save_agent_feedback(self, agent_output: Dict[str, Any], output_dir: Path):
        """
        Save individual agent feedback to markdown files.
        """
        feedback_dir = output_dir / "feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)
        
        agent_name = agent_output.get("agent_name", "unknown")
        feedback = agent_output.get("feedback", "")
        scores = agent_output.get("scores", {})
        action_items = agent_output.get("action_items", [])
        
        # Create markdown file
        filename = f"{agent_name.lower()}.md"
        filepath = feedback_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {agent_name.replace('_', ' ').title()} Review\n\n")
            f.write(feedback)
            
            # Add scores if available
            if scores:
                f.write("\n## Scores\n\n")
                for criterion, score in scores.items():
                    f.write(f"- **{criterion}**: {score}\n")
            
            # Add action items if available
            if action_items:
                f.write("\n## Action Items\n\n")
                for i, item in enumerate(action_items, 1):
                    f.write(f"{i}. {item}\n")
        
        self.logger.info(f"Saved {agent_name} feedback to {filepath}")
    
    def save_scorecard(self, consolidated_scores: Dict[str, float], output_dir: Path):
        """
        Save consolidated scores to JSON file.
        """
        scorecard_path = output_dir / "scorecard.json"
        
        with open(scorecard_path, "w", encoding="utf-8") as f:
            json.dump(consolidated_scores, f, indent=2)
        
        self.logger.info(f"Saved scorecard to {scorecard_path}")
    
    def save_summary(self, summary: str, output_dir: Path):
        """
        Save consolidated summary to markdown file.
        """
        summary_path = output_dir / "summary.md"
        
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
        
        self.logger.info(f"Saved summary to {summary_path}")
    
    def save_action_items(self, action_items: List[str], output_dir: Path):
        """
        Save action items to markdown file.
        """
        action_items_path = output_dir / "action_items.md"
        
        with open(action_items_path, "w", encoding="utf-8") as f:
            f.write("# Action Items\n\n")
            for i, item in enumerate(action_items, 1):
                f.write(f"{i}. {item}\n")
        
        self.logger.info(f"Saved action items to {action_items_path}")
    
    def save_all_outputs(self, review_state: Any):
        """
        Save all review outputs to files.
        """
        output_dir = review_state.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save role feedback
        self.save_role_feedback(review_state.all_role_outputs, output_dir)
        
        # Save scorecard
        self.save_scorecard(review_state.consolidated_scores, output_dir)
        
        # Save summary
        self.save_summary(review_state.summary, output_dir)
        
        # Save action items
        self.save_action_items(review_state.action_items, output_dir)
        
        self.logger.info(f"All outputs saved to {output_dir}")
    
    def create_review_report(self, review_state: Any) -> str:
        """
        Create a comprehensive review report.
        """
        report = "# Proposal Review Report\n\n"
        
        # Add summary
        if review_state.summary:
            report += review_state.summary + "\n\n"
        
        # Add scores
        if review_state.consolidated_scores:
            report += "## Detailed Scores\n\n"
            for criterion, score in review_state.consolidated_scores.items():
                report += f"- **{criterion}**: {score}\n"
            report += "\n"
        
        # Add action items
        if review_state.action_items:
            report += "## Action Items\n\n"
            for i, item in enumerate(review_state.action_items, 1):
                report += f"{i}. {item}\n"
        
        return report 