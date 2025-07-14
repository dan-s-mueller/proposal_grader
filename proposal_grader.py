import argparse
import json
import os
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Any
import openai
from parser import extract_pdf, extract_budget_xlsx
import compliance


class ProposalGrader:
    def __init__(self, openai_key: str):
        self.openai_key = openai_key
        openai.api_key = openai_key
        self.required_files = [
            "tech_proposal.pdf",
            "budget.xlsx", 
            "commercial_proposal.pdf",
            "team_bios.pdf",
            "past_performance.pdf"
        ]
        
    def check_required_files(self, bundle: Path) -> List[str]:
        """Check for missing required files."""
        missing = []
        for file in self.required_files:
            if not (bundle / file).exists():
                missing.append(file)
        return missing
    
    def load_rubrics(self) -> List[Dict]:
        """Load all rubric files."""
        rubrics = []
        for p in Path("rubrics").glob("*.json"):
            with open(p) as f:
                rubrics.append(json.load(f))
        return rubrics
    
    def load_prompts(self) -> Dict[str, str]:
        """Load all prompt templates."""
        prompts = {}
        for p in Path("prompts").glob("*.md"):
            code = p.stem.upper()
            with open(p) as f:
                prompts[code] = f.read()
        return prompts
    
    def render_prompt(self, template: str, **kwargs) -> str:
        """Render a prompt template with variables."""
        return template.format(**kwargs)
    
    def llm_score(self, prompt: str) -> Tuple[float, List[str], str]:
        """Get score from LLM with evidence and reasoning."""
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            content = resp.choices[0].message.content
            
            # Try to parse JSON response
            try:
                data = json.loads(content)
                score = float(data.get("score", 0))
                evidence = data.get("evidence", [])
                reasoning = data.get("reasoning", "")
                return score, evidence, reasoning
            except json.JSONDecodeError:
                # Fallback: try to extract score from text
                import re
                score_match = re.search(r'(\d+(?:\.\d+)?)', content)
                score = float(score_match.group(1)) if score_match else 0.0
                return score, [content], "Score extracted from text response"
                
        except Exception as e:
            print(f"Error in LLM scoring: {e}")
            return 0.0, [], f"Error: {str(e)}"
    
    def extract_proposal_text(self, bundle: Path) -> Dict[str, str]:
        """Extract text from all proposal documents."""
        texts = {}
        
        # Technical proposal
        if (bundle / "tech_proposal.pdf").exists():
            text, _ = extract_pdf(str(bundle / "tech_proposal.pdf"))
            texts["technical"] = text
        
        # Commercial proposal
        if (bundle / "commercial_proposal.pdf").exists():
            text, _ = extract_pdf(str(bundle / "commercial_proposal.pdf"))
            texts["commercial"] = text
        
        # Team bios
        if (bundle / "team_bios.pdf").exists():
            text, _ = extract_pdf(str(bundle / "team_bios.pdf"))
            texts["team"] = text
        
        # Past performance
        if (bundle / "past_performance.pdf").exists():
            text, _ = extract_pdf(str(bundle / "past_performance.pdf"))
            texts["past_performance"] = text
        
        return texts
    
    def grade_proposal(self, bundle: Path) -> Dict[str, Any]:
        """Grade a complete proposal."""
        print(f"Grading proposal in {bundle}")
        
        # Check for missing files
        missing = self.check_required_files(bundle)
        if missing:
            print(f"Warning: Missing files: {', '.join(missing)}")
        
        # Load configuration
        config = yaml.safe_load(open("config/2025.yaml"))
        
        # Check compliance
        try:
            compliance.check(bundle, config)
            print("Compliance check passed")
        except Exception as e:
            print(f"Compliance warning: {e}")
        
        # Load rubrics and prompts
        rubrics = self.load_rubrics()
        prompts = self.load_prompts()
        
        # Extract proposal texts
        texts = self.extract_proposal_text(bundle)
        
        # Initialize results
        results = {
            "dimensions": {},
            "sections": {},
            "overall": 0.0,
            "compliance": {},
            "budget": {}
        }
        
        # Grade each rubric
        for rubric in rubrics:
            section_name = rubric["rubric_id"].lower().replace("_evaluation", "")
            section_score = 0.0
            section_results = {}
            
            print(f"\nGrading {section_name} section...")
            
            for dimension in rubric["dimensions"]:
                code = dimension["code"]
                if code not in prompts:
                    print(f"Warning: No prompt template for {code}")
                    continue
                
                # Get relevant text for this dimension
                if section_name == "technical":
                    section_text = texts.get("technical", "")[:3000]
                elif section_name == "commercial":
                    section_text = texts.get("commercial", "")[:3000]
                else:
                    section_text = texts.get("technical", "")[:3000]
                
                # Render prompt
                prompt = self.render_prompt(
                    prompts[code],
                    section_text=section_text,
                    weight=dimension["weight"]
                )
                
                # Get score
                print(f"  Evaluating {code}...")
                score, evidence, reasoning = self.llm_score(prompt)
                
                # Calculate weighted score
                weighted_score = score * dimension["weight"] * rubric["weight"] * 5
                
                # Store results
                dimension_result = {
                    "score": score,
                    "weight": dimension["weight"],
                    "evidence": evidence,
                    "reasoning": reasoning,
                    "weighted": weighted_score
                }
                
                section_results[code] = dimension_result
                section_score += weighted_score
                results["dimensions"][code] = dimension_result
            
            results["sections"][section_name] = {
                "score": section_score,
                "weight": rubric["weight"],
                "dimensions": section_results
            }
        
        # Calculate overall score
        results["overall"] = sum(section["score"] for section in results["sections"].values())
        
        # Extract budget information if available
        if (bundle / "budget.xlsx").exists():
            try:
                budget_data = extract_budget_xlsx(str(bundle / "budget.xlsx"))
                results["budget"] = budget_data
            except Exception as e:
                print(f"Error extracting budget: {e}")
        
        return results
    
    def generate_report(self, results: Dict[str, Any], output_path: Path):
        """Generate a detailed evaluation report."""
        report = []
        report.append("# Proposal Evaluation Report\n")
        
        # Overall score
        report.append(f"## Overall Score: {results['overall']:.1f}/100\n")
        
        # Section scores
        report.append("## Section Scores\n")
        for section_name, section_data in results["sections"].items():
            report.append(f"### {section_name.title()}: {section_data['score']:.1f}/100\n")
        
        # Detailed dimension scores
        report.append("## Detailed Evaluation\n")
        for code, dimension in results["dimensions"].items():
            report.append(f"### {code}\n")
            report.append(f"- **Score**: {dimension['score']:.1f}/100\n")
            report.append(f"- **Weight**: {dimension['weight']*100:.0f}%\n")
            report.append(f"- **Weighted Score**: {dimension['weighted']:.1f}\n")
            if dimension['reasoning']:
                report.append(f"- **Reasoning**: {dimension['reasoning']}\n")
            if dimension['evidence']:
                report.append("- **Evidence**:\n")
                for evidence in dimension['evidence']:
                    report.append(f"  - {evidence}\n")
            report.append("\n")
        
        # Budget summary
        if results["budget"]:
            report.append("## Budget Summary\n")
            report.append(f"- **Total Budget**: ${results['budget'].get('total', 0):,.2f}\n")
            report.append(f"- **TABA**: ${results['budget'].get('taba', 0):,.2f}\n")
            report.append(f"- **Subcontract Total**: ${results['budget'].get('subcontract_total', 0):,.2f}\n")
        
        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report))
        
        print(f"Detailed report saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Grade proposal documents")
    parser.add_argument("--bundle", default="documents/proposal", type=Path, help="Path to proposal bundle")
    parser.add_argument("--openai-key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--list-required", action="store_true", help="List required files and exit")
    parser.add_argument("--output", default="results.json", type=Path, help="Output file for results")
    parser.add_argument("--report", default="evaluation_report.md", type=Path, help="Output file for detailed report")
    
    args = parser.parse_args()
    
    if args.list_required:
        grader = ProposalGrader("dummy_key")
        print("Required files:")
        for file in grader.required_files:
            print(f"  - {file}")
        return
    
    if not args.openai_key:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --openai-key")
        return
    
    # Create grader and grade proposal
    grader = ProposalGrader(args.openai_key)
    
    # Check for missing files
    missing = grader.check_required_files(args.bundle)
    if missing:
        print(f"Warning: Missing required files: {', '.join(missing)}")
        print("Consider creating dummy files for testing.")
    
    # Grade the proposal
    results = grader.grade_proposal(args.bundle)
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {args.output}")
    print(f"Overall score: {results['overall']:.1f}/100")
    
    # Generate detailed report
    grader.generate_report(results, args.report)


if __name__ == "__main__":
    main() 