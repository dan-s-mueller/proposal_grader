import os
import json
import csv
import sys
from pathlib import Path
from typing import Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv
import logging

# --- CONFIGURATION ---
RUBRIC_PATH = Path("output/complete_rubric.json")
PROMPTS_DIR = Path("prompts")
FILE_CONFIG_PATH = Path("config/proposal_files.json")
PROPOSAL_DIR = Path("documents/proposal")
CSV_OUTPUT = Path("output/evaluation_summary.csv")
LOG_FILE = Path("output/grading.log")

# Ensure output directory exists
CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler()
    ]
)

# --- UTILS ---
def load_json(path: Path) -> Any:
    with open(path, "r") as f:
        return json.load(f)

def load_prompt(code: str) -> str:
    prompt_path = PROMPTS_DIR / f"{code.lower()}.md"
    with open(prompt_path, "r") as f:
        return f.read()

def extract_pdf_text(pdf_path: Path) -> str:
    import PyPDF2
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def find_files_by_patterns(root: Path, patterns: List[str]) -> List[Path]:
    import fnmatch
    found = []
    for pattern in patterns:
        for file_path in root.rglob("*"):
            if file_path.is_file() and fnmatch.fnmatch(file_path.name.lower(), pattern.lower()):
                found.append(file_path)
    return found

def map_score_to_label(score: float) -> str:
    if score < 2.0:
        return "unsatisfactory"
    elif score < 3.0:
        return "marginal"
    elif score < 3.5:
        return "satisfactory"
    else:
        return "superior"

# --- MAIN PIPELINE ---
def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")
    if not api_key:
        logging.error("OPENAI_API_KEY not set in environment.")
        sys.exit(1)
    if not model:
        logging.error("OPENAI_MODEL not set in environment.")
        sys.exit(1)
    client = OpenAI(api_key=api_key)

    # 1. Load rubric and file config
    rubric = load_json(RUBRIC_PATH)
    file_config = load_json(FILE_CONFIG_PATH)

    # 2. Check for required and optional files
    found_files = {}
    missing_required = []
    # Check required_files
    for file_spec in file_config["required_files"]:
        matches = find_files_by_patterns(PROPOSAL_DIR, file_spec["file_patterns"])
        if file_spec.get("required", True):
            if not matches:
                logging.error(f"Missing required file: {file_spec['name']} (patterns: {file_spec['file_patterns']})")
                sys.exit(1)
            found_files[file_spec["name"]] = matches[0]
        else:
            if matches:
                found_files[file_spec["name"]] = matches[0]
    # Check optional_files
    for file_spec in file_config.get("optional_files", []):
        matches = find_files_by_patterns(PROPOSAL_DIR, file_spec["file_patterns"])
        if matches:
            found_files[file_spec["name"]] = matches[0]

    # 3. Aggregate all proposal text from required PDFs
    proposal_text = ""
    for file in found_files.values():
        if file.suffix.lower() == ".pdf":
            proposal_text += extract_pdf_text(file) + "\n"

    # 6. Output CSV report (write header at start)
    with open(CSV_OUTPUT, "w", newline="") as csvfile:
        fieldnames = ["section", "category", "sub_category", "score", "weight", "weighted_score", "rationale"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    # 4. For each rubric sub-category, use the corresponding prompt to ask the LLM for a grade (1-4) and rationale
    results = []
    section_scores = {}
    section_weights = {}
    for section_name, section in rubric["types"].items():
        section_total = 0.0
        section_weight = section["weight"] / 100.0
        section_weights[section_name] = section_weight
        subcat_weight_sum = 0.0
        subcat_results = []
        for category_name, category in section["categories"].items():
            for subcat_name, subcat in category["sub_categories"].items():
                code = f"{category_name.upper().replace(' ', '_').replace('/', '_')}_{subcat_name.upper().replace(' ', '_').replace('/', '_')}"
                logging.info(f"Grading: Section='{section_name}', Category='{category_name}', Sub-category='{subcat_name}'...")
                prompt_template = load_prompt(code)
                prompt = prompt_template.format(section_text=proposal_text)
                # Call OpenAI (new API)
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
                        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500"))
                    )
                    content = response.choices[0].message.content
                except Exception as e:
                    logging.error(f"LLM call failed for {code}: {e}")
                    content = ""
                # Parse response (expecting JSON)
                try:
                    data = json.loads(content)
                    score = int(data.get("score", 1))
                    rationale = data.get("reasoning", "")
                except Exception:
                    import re
                    m = re.search(r'([1-4])', content)
                    score = int(m.group(1)) if m else 1
                    rationale = content
                weight = subcat["weight"] / 100.0
                weighted_score = score * weight
                row = {
                    "section": section_name,
                    "category": category_name,
                    "sub_category": subcat_name,
                    "score": score,
                    "weight": weight,
                    "weighted_score": weighted_score,
                    "rationale": rationale
                }
                subcat_results.append(row)
                section_total += weighted_score
                subcat_weight_sum += weight
                # Write this row to CSV immediately
                with open(CSV_OUTPUT, "a", newline="") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow(row)
                logging.info(f"Completed: {code} | Score: {score} | Weighted: {weighted_score:.3f}")
        section_score = section_total / subcat_weight_sum if subcat_weight_sum else 0.0
        section_scores[section_name] = section_score
        results.extend(subcat_results)

    overall = 0.0
    total_weight = 0.0
    for section_name, section_score in section_scores.items():
        w = section_weights[section_name]
        overall += section_score * w
        total_weight += w
    overall_score = overall / total_weight if total_weight else 0.0
    recommendation = map_score_to_label(overall_score)

    with open(CSV_OUTPUT, "a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow({})
        for section_name, section_score in section_scores.items():
            writer.writerow({
                "section": section_name,
                "score": f"{section_score:.2f}",
                "weight": f"{section_weights[section_name]:.2f}"
            })
        writer.writerow({})
        writer.writerow({
            "section": "OVERALL",
            "score": f"{overall_score:.2f}",
            "weight": "1.00",
            "sub_category": recommendation
        })
    logging.info(f"CSV report saved to {CSV_OUTPUT}")

    # Write Markdown report
    md_output = CSV_OUTPUT.with_suffix('.md')
    with open(md_output, "w") as mdfile:
        mdfile.write("# Proposal Evaluation Summary\n\n")
        mdfile.write("| Section | Category | Sub-category | Score | Weight | Weighted Score | Rationale |\n")
        mdfile.write("|---------|----------|--------------|-------|--------|---------------|-----------|\n")
        for row in results:
            mdfile.write(f"| {row['section']} | {row['category']} | {row['sub_category']} | {row['score']} | {row['weight']:.2f} | {row['weighted_score']:.2f} | {row['rationale'].replace('|', ' ')} |\n")
        mdfile.write("|  |  |  |  |  |  |  |\n")
        for section_name, section_score in section_scores.items():
            mdfile.write(f"| **{section_name}** |  |  | **{section_score:.2f}** | **{section_weights[section_name]:.2f}** |  |  |\n")
        mdfile.write("|  |  |  |  |  |  |  |\n")
        mdfile.write(f"| **OVERALL** |  |  | **{overall_score:.2f}** | **1.00** |  | **{recommendation.upper()}** |\n")
    logging.info(f"Markdown report saved to {md_output}")

if __name__ == "__main__":
    main() 