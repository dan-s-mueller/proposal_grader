# Proposal Grader

An AI-powered system for automated evaluation of SBIR/STTR proposals. This system parses solicitation documents, extracts evaluation criteria, and grades proposals using natural language processing.

## Features

- **Solicitation Parser**: Extracts evaluation criteria from PDF solicitation documents
- **Rubric Generator**: Converts evaluation criteria to structured JSON rubrics
- **AI-Powered Grading**: Uses OpenAI's GPT models to evaluate proposals
- **Comprehensive Reporting**: Generates detailed evaluation reports with evidence and reasoning
- **Compliance Checking**: Validates proposal compliance with requirements
- **Budget Analysis**: Extracts and analyzes budget information

## Quick Start

### 1. Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Dependencies

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Set OpenAI API Key

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 4. Run Complete Pipeline

```bash
# Using Poetry
poetry run python run_grading_pipeline.py

# Or activate the virtual environment
poetry shell
python run_grading_pipeline.py
```

This will:
- Parse the solicitation PDF
- Generate evaluation rubrics
- Create dummy files for testing
- Grade the proposal
- Generate detailed reports

## System Architecture

### Core Components

1. **`solicitation_parser.py`**: Extracts evaluation criteria from solicitation PDFs
2. **`md_to_rubric_json.py`**: Converts markdown rubrics to JSON format
3. **`proposal_grader.py`**: Main grading engine with AI evaluation
4. **`create_dummy_files.py`**: Generates test files for development
5. **`run_grading_pipeline.py`**: Orchestrates the complete workflow

### File Structure

```
proposal_grader/
├── documents/
│   ├── solicitations/
│   │   └── solicitation.pdf          # Input solicitation document
│   └── proposal/
│       ├── tech_proposal.pdf         # Technical proposal
│       ├── commercial_proposal.pdf   # Commercial proposal
│       ├── team_bios.pdf            # Team biographies
│       ├── past_performance.pdf     # Past performance
│       └── budget.xlsx              # Budget spreadsheet
├── rubrics/                         # Generated evaluation rubrics
├── prompts/                         # AI prompt templates
├── config/                          # Configuration files
├── output/                          # Generated reports and results
└── scripts/                         # Individual processing scripts
```

## Usage

### Poetry Commands

The project includes Poetry scripts for easy access to main functions:

```bash
# Run the complete grading pipeline
poetry run grading-pipeline

# Parse solicitation document
poetry run solicitation-parser documents/solicitations/solicitation.pdf output/rubric.md

# Convert markdown to JSON rubric
poetry run rubric-converter output/rubric.md --output-dir rubrics --prompts-dir prompts

# Create dummy files
poetry run dummy-files --output-dir documents/proposal --overwrite

# Grade proposal
poetry run proposal-grader --bundle documents/proposal --output results.json --report report.md
```

### Individual Scripts

#### Parse Solicitation
```bash
poetry run python solicitation_parser.py documents/solicitations/solicitation.pdf output/rubric.md
```

#### Convert to JSON Rubric
```bash
poetry run python md_to_rubric_json.py output/rubric.md --output-dir rubrics --prompts-dir prompts
```

#### Create Dummy Files
```bash
poetry run python create_dummy_files.py --output-dir documents/proposal --overwrite
```

#### Grade Proposal
```bash
poetry run python proposal_grader.py --bundle documents/proposal --output results.json --report report.md
```

### Pipeline Options

#### Skip Dummy File Creation
```bash
poetry run python run_grading_pipeline.py --skip-dummy-files
```

#### Use Existing Rubrics
```bash
poetry run python run_grading_pipeline.py --skip-solicitation-parse
```

#### Custom Output Directory
```bash
poetry run python run_grading_pipeline.py --output-dir my_results
```

## Required Files

The system expects the following files in the proposal directory:

1. **`tech_proposal.pdf`**: Technical proposal document
2. **`commercial_proposal.pdf`**: Commercial proposal document
3. **`team_bios.pdf`**: Team member biographies
4. **`past_performance.pdf`**: Past performance documentation
5. **`budget.xlsx`**: Budget spreadsheet with specific cell references

## Evaluation Criteria

The system automatically extracts and evaluates:

### Technical Criteria (70% weight)
- Technical Approach
- Innovation
- Risk Assessment
- Implementation Plan
- Team Qualifications
- Writing Quality

### Commercial Criteria (30% weight)
- Market Knowledge
- Customer Understanding
- Value Proposition
- Competitive Analysis
- Transition Strategy
- Writing Quality

## Output Files

### Results JSON
Contains structured evaluation data with scores, weights, evidence, and reasoning.

### Evaluation Report
Markdown report with:
- Overall score
- Section breakdowns
- Detailed dimension scores
- Evidence and reasoning
- Budget summary

## Configuration

Edit `config/2025.yaml` to modify:
- Proposal page limits
- Maximum budget amounts
- Performance period months

## Development

### Adding New Evaluation Criteria

1. Update the solicitation parser patterns in `solicitation_parser.py`
2. Modify the markdown parser in `md_to_rubric_json.py`
3. Create corresponding prompt templates in `prompts/`

### Customizing AI Prompts

Edit the prompt templates in the `prompts/` directory to modify how the AI evaluates each criterion.

### Extending Budget Analysis

Modify the `extract_budget_xlsx` function in `parser.py` to handle different budget formats.

## Troubleshooting

### Common Issues

1. **Missing OpenAI API Key**: Set the `OPENAI_API_KEY` environment variable
2. **PDF Parsing Errors**: Ensure PDFs are text-based, not scanned images
3. **Budget Cell Errors**: Verify Excel file has expected cell structure
4. **Missing Files**: Use `--list-required` to see required files

### Debug Mode

Add `--verbose` flags to individual scripts for detailed output.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
