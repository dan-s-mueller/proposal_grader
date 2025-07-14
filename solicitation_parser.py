import argparse
import re
from pathlib import Path
from pdfminer.high_level import extract_text
from typing import Dict, List, Tuple


def extract_evaluation_criteria(text: str) -> Dict[str, List[Dict]]:
    """
    Extract evaluation criteria from solicitation text.
    Looks for tables and structured content that defines scoring criteria.
    """
    criteria = {
        "technical": [],
        "commercial": []
    }
    
    # Split text into sections
    sections = text.split('\n\n')
    
    # Look for evaluation criteria sections
    for section in sections:
        section_lower = section.lower()
        
        # Technical criteria patterns
        if any(keyword in section_lower for keyword in ['technical', 'technology', 'innovation', 'approach']):
            criteria["technical"].extend(parse_criteria_section(section))
        
        # Commercial criteria patterns  
        if any(keyword in section_lower for keyword in ['commercial', 'market', 'business', 'economic']):
            criteria["commercial"].extend(parse_criteria_section(section))
    
    return criteria


def parse_criteria_section(section: str) -> List[Dict]:
    """Parse a section to extract individual criteria with weights."""
    criteria = []
    
    # Look for patterns like "Criterion Name: XX%" or "Criterion Name (XX%)"
    patterns = [
        r'([A-Za-z\s\-/]+):\s*(\d+)%',
        r'([A-Za-z\s\-/]+)\s*\((\d+)%\)',
        r'([A-Za-z\s\-/]+)\s+(\d+)\s*%'
    ]
    
    lines = section.split('\n')
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line.strip())
            if match:
                name = match.group(1).strip()
                weight = int(match.group(2)) / 100.0
                
                # Clean up the name
                code = re.sub(r'[^A-Za-z0-9\s]', '', name)
                code = re.sub(r'\s+', '_', code).upper()
                
                criteria.append({
                    "name": name,
                    "code": code,
                    "weight": weight,
                    "description": extract_criterion_description(section, name)
                })
                break
    
    return criteria


def extract_criterion_description(section: str, criterion_name: str) -> str:
    """Extract description for a specific criterion."""
    lines = section.split('\n')
    description_lines = []
    found_criterion = False
    
    for line in lines:
        if criterion_name.lower() in line.lower():
            found_criterion = True
            continue
        
        if found_criterion:
            # Stop at next criterion or empty line
            if re.match(r'^[A-Za-z\s\-/]+:\s*\d+%', line) or line.strip() == '':
                break
            description_lines.append(line.strip())
    
    return ' '.join(description_lines).strip()


def create_markdown_rubric(criteria: Dict[str, List[Dict]]) -> str:
    """Convert extracted criteria to markdown format."""
    md_content = "# Proposal Evaluation Rubric\n\n"
    
    # Technical Section
    md_content += "## Technical Evaluation Criteria (70%)\n\n"
    for criterion in criteria["technical"]:
        md_content += f"### {criterion['name']} ({criterion['weight']*100:.0f}%)\n"
        if criterion['description']:
            md_content += f"{criterion['description']}\n\n"
        else:
            md_content += f"Evaluation of {criterion['name'].lower()}.\n\n"
    
    # Commercial Section
    md_content += "## Commercial Evaluation Criteria (30%)\n\n"
    for criterion in criteria["commercial"]:
        md_content += f"### {criterion['name']} ({criterion['weight']*100:.0f}%)\n"
        if criterion['description']:
            md_content += f"{criterion['description']}\n\n"
        else:
            md_content += f"Evaluation of {criterion['name'].lower()}.\n\n"
    
    return md_content


def main():
    parser = argparse.ArgumentParser(description="Parse solicitation PDF and extract evaluation criteria")
    parser.add_argument("pdf_path", type=Path, help="Path to solicitation PDF")
    parser.add_argument("output_path", type=Path, help="Output markdown file path")
    args = parser.parse_args()
    
    # Extract text from PDF
    print(f"Extracting text from {args.pdf_path}...")
    text = extract_text(str(args.pdf_path))
    
    # Extract evaluation criteria
    print("Extracting evaluation criteria...")
    criteria = extract_evaluation_criteria(text)
    
    # Create markdown rubric
    print("Creating markdown rubric...")
    md_rubric = create_markdown_rubric(criteria)
    
    # Write to file
    with open(args.output_path, 'w') as f:
        f.write(md_rubric)
    
    print(f"Markdown rubric saved to {args.output_path}")
    print(f"Found {len(criteria['technical'])} technical criteria and {len(criteria['commercial'])} commercial criteria")


if __name__ == "__main__":
    main() 