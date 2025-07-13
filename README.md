# Proposal Grader

This project provides a minimal command line tool for grading NASA SBIR Phase I proposals. It parses proposal PDFs and budget spreadsheets, checks basic compliance rules and then queries the OpenAI API using markdown prompt templates to assign rubric scores.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```
python main.py --bundle PATH/TO/BUNDLE --openai_key sk-...
```

The bundle directory should contain `tech_proposal.pdf` and `budget.xlsx`. Results are written to `results.json` in the same folder.

### Extracting rubrics from a solicitation PDF

You can generate a JSON rubric from a solicitation by running:

```bash
python extract_rubric.py SOLICITATION.pdf 2025_P1_Technical 0.70 rubrics/phase1_technical.json
```
