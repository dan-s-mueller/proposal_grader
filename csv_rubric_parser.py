#!/usr/bin/env python3
"""
CSV Rubric Parser

This script parses evaluation criteria and rubric CSV files to generate structured JSON rubrics
for the proposal grading system.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Any


def parse_eval_criteria(csv_path: Path) -> Dict[str, Dict]:
    """
    Parse the evaluation criteria description CSV file.
    
    Returns a dictionary mapping (Type, Category, Sub-Category) to description.
    """
    criteria = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['Type'], row['Category'], row['Sub-Category'])
            criteria[key] = {
                'type': row['Type'],
                'category': row['Category'],
                'sub_category': row['Sub-Category'],
                'weight': float(row['Weight']),
                'definition': row['Definition'].strip()
            }
    
    return criteria


def parse_eval_rubric(csv_path: Path) -> List[Dict]:
    """
    Parse the evaluation rubric CSV file.
    
    Returns a list of rubric entries with scoring criteria.
    """
    rubric_entries = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry = {
                'type': row['Type'],
                'type_weight': float(row['Type Weight']),
                'category': row['Category'],
                'sub_category': row['Sub-Category'],
                'category_weight': float(row['Category Weight']),
                'scoring': {
                    'unsatisfactory': row['Unsatisfactory'].strip(),
                    'marginal': row['Marginal'].strip(),
                    'satisfactory': row['Satisfactory'].strip(),
                    'superior': row['Superior'].strip()
                }
            }
            rubric_entries.append(entry)
    
    return rubric_entries


def merge_criteria_and_rubric(criteria: Dict, rubric_entries: List[Dict]) -> Dict[str, Any]:
    """
    Merge the criteria descriptions with the rubric scoring to create a complete rubric structure.
    For each category, split the category weight equally among its sub-categories.
    """
    # Group by type (Commercial/Technical)
    rubric_structure = {
        'metadata': {
            'version': '1.0',
            'description': 'NASA SBIR Ignite Evaluation Rubric',
            'total_weight': 100
        },
        'types': {}
    }

    # First, collect all sub-categories for each (type, category)
    subcat_map = {}
    for entry in rubric_entries:
        type_name = entry['type']
        category_name = entry['category']
        subcat_map.setdefault((type_name, category_name), set()).add(entry['sub_category'])

    # Now, process each rubric entry
    for entry in rubric_entries:
        type_name = entry['type']
        category_name = entry['category']
        sub_category_name = entry['sub_category']

        # Initialize type if not exists
        if type_name not in rubric_structure['types']:
            rubric_structure['types'][type_name] = {
                'weight': entry['type_weight'],
                'categories': {}
            }

        # Initialize category if not exists
        if category_name not in rubric_structure['types'][type_name]['categories']:
            rubric_structure['types'][type_name]['categories'][category_name] = {
                'weight': entry['category_weight'],
                'sub_categories': {}
            }

        # Calculate sub-category weight (split equally)
        n_subcats = len(subcat_map[(type_name, category_name)])
        subcat_weight = entry['category_weight'] / n_subcats if n_subcats > 0 else entry['category_weight']

        # Get description from criteria
        criteria_key = (type_name, category_name, sub_category_name)
        description = criteria.get(criteria_key, {}).get('definition', '')

        # Add sub-category
        rubric_structure['types'][type_name]['categories'][category_name]['sub_categories'][sub_category_name] = {
            'description': description,
            'scoring': entry['scoring'],
            'weight': subcat_weight
        }

    return rubric_structure


def create_individual_rubrics(rubric_structure: Dict) -> Dict[str, Dict]:
    """
    Create individual JSON files for each type (Commercial/Technical).
    """
    individual_rubrics = {}

    for type_name, type_data in rubric_structure['types'].items():
        # Create rubric for this type
        rubric = {
            'rubric_id': f"{type_name.upper()}_EVALUATION",
            'weight': type_data['weight'] / 100.0,  # Convert to decimal
            'dimensions': []
        }

        # Process each category and sub-category
        for category_name, category_data in type_data['categories'].items():
            for sub_category_name, sub_category_data in category_data['sub_categories'].items():
                # Create dimension entry
                dimension = {
                    'name': f"{category_name} - {sub_category_name}",
                    'code': f"{category_name.upper().replace(' ', '_').replace('/', '_')}_{sub_category_name.upper().replace(' ', '_').replace('/', '_')}",
                    'weight': sub_category_data['weight'] / 100.0,  # Use sub-category weight
                    'description': sub_category_data['description'],
                    'scoring_criteria': sub_category_data['scoring']
                }
                rubric['dimensions'].append(dimension)

        individual_rubrics[type_name.lower()] = rubric

    return individual_rubrics


def create_prompt_templates(rubric_structure: Dict) -> Dict[str, str]:
    """
    Create prompt templates for each sub-category using 1-4 scoring.
    """
    templates = {}

    for type_name, type_data in rubric_structure['types'].items():
        for category_name, category_data in type_data['categories'].items():
            for sub_category_name, sub_category_data in category_data['sub_categories'].items():
                # Create code for this sub-category
                code = f"{category_name.upper().replace(' ', '_').replace('/', '_')}_{sub_category_name.upper().replace(' ', '_').replace('/', '_')}"

                # Create prompt template (1-4 scale)
                template = f"""# {category_name} - {sub_category_name} Evaluation\n\n**Weight**: {sub_category_data['weight']:.2f}%\n\n**Description**: {sub_category_data['description']}\n\n**Scoring Criteria (1-4 scale):**\n\n**1 (Unsatisfactory)**: {sub_category_data['scoring']['unsatisfactory']}\n\n**2 (Marginal)**: {sub_category_data['scoring']['marginal']}\n\n**3 (Satisfactory)**: {sub_category_data['scoring']['satisfactory']}\n\n**4 (Superior)**: {sub_category_data['scoring']['superior']}\n\n**Instructions**: Evaluate the proposal's {sub_category_name.lower()} based on the above criteria.\n\n**Proposal Text**:\n{{section_text}}\n\n**Evaluation**:\nPlease provide a JSON response with:\n- \"score\": integer score (1-4, in 0.5 increments only) \n- \"evidence\": list of specific evidence from the proposal text\n- \"reasoning\": brief explanation of the score based on the scoring criteria\n\n**Response**:"""

                templates[code] = template

    return templates


def save_rubric_files(individual_rubrics: Dict, output_dir: Path):
    """Save individual rubric JSON files."""
    output_dir.mkdir(exist_ok=True)
    
    for type_name, rubric in individual_rubrics.items():
        filename = f"phase1_{type_name}.json"
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


def save_complete_rubric(rubric_structure: Dict, output_path: Path):
    """Save the complete rubric structure."""
    with open(output_path, 'w') as f:
        json.dump(rubric_structure, f, indent=2)
    
    print(f"Saved complete rubric: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Parse CSV evaluation criteria and rubric files")
    parser.add_argument(
        "--criteria", 
        default="documents/solicitations/eval_criteria_description.csv",
        type=Path,
        help="Path to evaluation criteria CSV file"
    )
    parser.add_argument(
        "--rubric",
        default="documents/solicitations/eval_rubric.csv", 
        type=Path,
        help="Path to evaluation rubric CSV file"
    )
    parser.add_argument(
        "--output-dir",
        default="rubrics",
        type=Path,
        help="Output directory for individual rubric files"
    )
    parser.add_argument(
        "--prompts-dir",
        default="prompts",
        type=Path,
        help="Output directory for prompt templates"
    )
    parser.add_argument(
        "--complete-rubric",
        default="output/complete_rubric.json",
        type=Path,
        help="Output path for complete rubric structure"
    )
    
    args = parser.parse_args()
    
    # Check if input files exist
    if not args.criteria.exists():
        print(f"Error: Criteria file not found: {args.criteria}")
        return 1
    
    if not args.rubric.exists():
        print(f"Error: Rubric file not found: {args.rubric}")
        return 1
    
    print("Parsing evaluation criteria...")
    criteria = parse_eval_criteria(args.criteria)
    
    print("Parsing evaluation rubric...")
    rubric_entries = parse_eval_rubric(args.rubric)
    
    print("Merging criteria and rubric...")
    rubric_structure = merge_criteria_and_rubric(criteria, rubric_entries)
    
    print("Creating individual rubrics...")
    individual_rubrics = create_individual_rubrics(rubric_structure)
    
    print("Creating prompt templates...")
    templates = create_prompt_templates(rubric_structure)
    
    # Save files
    print("Saving files...")
    save_rubric_files(individual_rubrics, args.output_dir)
    save_prompt_templates(templates, args.prompts_dir)
    save_complete_rubric(rubric_structure, args.complete_rubric)
    
    print("Conversion complete!")
    print(f"Found {len(individual_rubrics)} rubric types")
    print(f"Created {len(templates)} prompt templates")
    
    return 0


if __name__ == "__main__":
    exit(main()) 