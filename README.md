# NASA SBIR Ignite Proposal Grading Pipeline

## Overview
This system automates the grading of NASA SBIR Ignite proposals using a rubric defined in JSON files. It checks for required proposal documents, evaluates proposal content using AI, and outputs a CSV summary with scores and recommendations on a 1–4 scale (unsatisfactory, marginal, satisfactory, superior).

## How it Works
- **Rubric and File Config Loading**: Loads the evaluation rubric and required/optional file configuration from JSON files.
- **File Detection**: Recursively searches the proposal directory for all required and optional files, using flexible filename patterns. Only truly required files cause errors if missing.
- **Proposal Text Extraction**: Extracts and aggregates text from all required PDF proposal files. (Other file types are currently ignored.)
- **LLM Grading**: For each rubric sub-category, the system constructs a prompt (rubric + proposal text) and uses OpenAI to evaluate and assign a 1–4 score, with rationale.
- **CSV Output**: Writes a CSV summary (`output/evaluation_summary.csv`) with detailed scores, weights, and recommendations. No Markdown output is produced.

## LLM Integration & Structured Output
- The pipeline uses **LangChain** and **OpenAI** to call the LLM for each rubric sub-category.
- A **Pydantic model** (`RubricScore`) defines the expected structure of the LLM's response (score, evidence, reasoning, improvements).
- **LangChain's `PydanticOutputParser`** is used to generate format instructions for the LLM and to validate/parse the LLM's output into a Python object.
- The prompt sent to the LLM includes both the rubric instructions and the full proposal text, ensuring the model has all necessary context for evaluation.
- This approach enforces robust, structured, and reliable grading, minimizing formatting errors and making downstream processing easy.

## File & Directory Structure
```
project_root/
├── main.py
├── csv_rubric_parser.py
├── config/
│   └── proposal_files.json
├── documents/
│   ├── solicitations/
│   │   ├── eval_criteria_description.csv
│   │   └── eval_rubric.csv
│   └── proposal/
│       └── [your proposal files and folders]
├── rubrics/
│   ├── phase1_technical.json
│   └── phase1_commercial.json
├── prompts/
│   └── [auto-generated prompt templates]
├── output/
│   └── evaluation_summary.csv
├── pyproject.toml
└── ...
```

## How to Run
1. **Install dependencies** (with Poetry):
   ```sh
   poetry install
   ```
2. **Set your OpenAI API key** in a `.env` file:
   ```env
   OPENAI_API_KEY=your_openai_key_here
   ```
3. **Run the pipeline:**
   ```sh
   poetry run python main.py
   ```
   - By default, this will parse the rubric, grade the proposal in `documents/proposal/`, and write results to `output/evaluation_summary.csv`.

## Scoring & Aggregation
- **Each sub-category** is scored 1–4 (1=unsatisfactory, 2=marginal, 3=satisfactory, 4=superior).
- **Category weights** are split equally among sub-categories.
- **Section weights**: Technical = 70%, Commercial = 30% (configurable).
- **Overall score**: Weighted average on the 1–4 scale.
- **Recommendation**:
  - 1.0–1.9: unsatisfactory
  - 2.0–2.9: marginal
  - 3.0–3.4: satisfactory
  - 3.5–4.0: superior

## Configuring Required/Optional Files
- Edit `config/proposal_files.json` to specify required and optional files.
- Use wildcards (e.g., `*technical*.pdf`) to allow flexible naming.
- The system searches all subfolders in the proposal directory.

## Environment Variables
- `OPENAI_API_KEY` (required): Your OpenAI API key.
- Optional: `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS` (see `.env` for details).

## Output CSV
- Located at `output/evaluation_summary.csv`.
- Columns:
  - section, category, sub_category, score, weight, weighted_score, rationale
  - Section totals and overall score/recommendation are included at the end.

## Notes
- All proposal files can be organized in subfolders; the system will find them.
- Only the 1–4 scale is used for scoring and reporting.
- The pipeline is fully automated and robust to file naming variations.

---
For questions or issues, see the code or contact the maintainer. 