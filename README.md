# Proposal Grader

This project provides a minimal command line tool for grading NASA SBIR Phase I proposals. It parses proposal PDFs and budget spreadsheets, checks basic compliance rules and then queries the OpenAI API using markdown prompt templates to assign rubric scores.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```
python main.py --bundle documents/proposal --openai_key sk-...
```

Place your proposal files in `documents/proposal`. Required files can be listed with:

```
python main.py --list_required
```
Results are written to `results.json` in the proposal folder.

### Extracting rubrics from a solicitation PDF

You can generate a Markdown rubric from a solicitation by running:

```bash
python extract_rubric_md.py documents/solicitations/SOLICITATION.pdf rubrics/phase1.md
python md_to_json.py rubrics/phase1.md 2025_P1 rubrics/phase1_combined.json
```
