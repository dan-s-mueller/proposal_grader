import argparse
import json
import re
from pathlib import Path
from typing import Dict, List


def parse_markdown_rubric(md_content: str) -> Dict:
    """Parse markdown rubric and convert to JSON structure."""
    lines = md_content.split('\n')
    
    rubrics = {
        "technical": {
            "rubric_id": "Technical_Evaluation",
            "weight": 0.70,
            "dimensions": []
        },
        "commercial": {
            "rubric_id": "Commercial_Evaluation", 
            "weight": 0.30,
            "dimensions": []
        }
    }
    
    current_section = None
    current_criterion = None
    
    for line in lines:
        line = line.strip()
        
        # Section headers
        if line.startswith('## Technical Evaluation Criteria'):
            current_section = "technical"
        elif line.startswith('## Commercial Evaluation Criteria'):
            current_section = "commercial"
        
        # Criterion headers
        elif line.startswith('### ') and current_section:
            # Extract criterion name and weight
            match = re.search(r'### (.+?) \((\d+)%\)', line)
            if match:
                name = match.group(1).strip()
                weight = int(match.group(2)) / 100.0
                
                # Create code from name
                code = re.sub(r'[^A-Za-z0-9\s]', '', name)
                code = re.sub(r'\s+', '_', code).upper()
                
                current_criterion = {
                    "name": name,
                    "code": code,
                    "weight": weight,
                    "description": ""
                }
                rubrics[current_section]["dimensions"].append(current_criterion)
        
        # Description text
        elif current_criterion and line and not line.startswith('#'):
            if current_criterion["description"]:
                current_criterion["description"] += " " + line
            else:
                current_criterion["description"] = line
    
    return rubrics


def create_prompt_templates(rubrics: Dict) -> Dict[str, str]:
    """Create prompt templates for each criterion."""
    templates = {}
    
    for section, rubric in rubrics.items():
        for dimension in rubric["dimensions"]:
            code = dimension["code"]
            name = dimension["name"]
            description = dimension["description"]
            
            template = f"""# {name} Evaluation

**Weight**: {dimension['weight']*100:.0f}%

**Description**: {description}

**Instructions**: Evaluate the proposal's {name.lower()} based on the following criteria:

- **Excellent (90-100%)**: Outstanding demonstration of {name.lower()}
- **Good (70-89%)**: Strong demonstration with minor areas for improvement
- **Fair (50-69%)**: Adequate demonstration with notable gaps
- **Poor (0-49%)**: Weak or missing demonstration

**Proposal Text**:
{{section_text}}

**Evaluation**:
Please provide a JSON response with:
- "score": numerical score (0-100)
- "evidence": list of specific evidence from the proposal text
- "reasoning": brief explanation of the score

**Response**:"""
            
            templates[code] = template
    
    return templates


def save_rubric_files(rubrics: Dict, output_dir: Path):
    """Save individual rubric JSON files."""
    output_dir.mkdir(exist_ok=True)
    
    for section, rubric in rubrics.items():
        filename = f"phase1_{section}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(rubric, f, indent=2)
        
        print(f"Saved {filename}")


def save_prompt_templates(templates: Dict, output_dir: Path):
    """Save prompt template files."""
    output_dir.mkdir(exist_ok=True)
    
    for code, template in templates.items():
        filename = f"{code.lower()}.md"
        filepath = output_dir / filename
        
        with open(filepath, 'w') as f:
            f.write(template)
        
        print(f"Saved prompt template: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Convert markdown rubric to JSON format")
    parser.add_argument("md_path", type=Path, help="Path to markdown rubric file")
    parser.add_argument("--output-dir", type=Path, default=Path("rubrics"), help="Output directory for JSON files")
    parser.add_argument("--prompts-dir", type=Path, default=Path("prompts"), help="Output directory for prompt templates")
    args = parser.parse_args()
    
    # Read markdown file
    with open(args.md_path, 'r') as f:
        md_content = f.read()
    
    # Parse markdown to JSON structure
    print("Parsing markdown rubric...")
    rubrics = parse_markdown_rubric(md_content)
    
    # Save rubric files
    print("Saving rubric JSON files...")
    save_rubric_files(rubrics, args.output_dir)
    
    # Create and save prompt templates
    print("Creating prompt templates...")
    templates = create_prompt_templates(rubrics)
    save_prompt_templates(templates, args.prompts_dir)
    
    print("Conversion complete!")


if __name__ == "__main__":
    main() 