
# Proposal Development User's Manual

Goal: ingest solicitation docs, review one main proposal doc plus supporting PDFs with independent LLM "agents," return actionable feedback and 1.0–4.0 scores (0.5 steps).

---

## 0. Prerequisites

| Item | Why | How |
|------|-----|-----|
| Poetry | Dependency and script runner | `curl -sSL https://install.python-poetry.org | python3 -` |
| Python 3.11+ | Runtime | Use pyenv or system package manager |
| OpenAI key | LLM access | `export OPENAI_API_KEY=...` |

Project layout (baseline):
```
project_root/
  documents/proposal/main_proposal.docx (or .pdf)
  documents/proposal/supporting_docs/
  documents/solicitation/
  output/
  src/agents/templates/
  pyproject.toml
```

---

## 1. Required Inputs (start here)

### 1.1 Main documents
| File | Required? | Notes |
|------|-----------|-------|
| `documents/proposal/main_proposal.docx` or `.pdf` | Yes | DOCX preferred for heading parsing. PDF supported as fallback. |
| `documents/proposal/supporting_docs/*.pdf` or `*.docx` | As needed | Letters of support, contractor quotes, resumes, prior work references. Supports sub-folders. |
| `documents/solicitation/*.pdf`, `*.csv`, `*.md` | Yes | Main solicitation, Q&A addenda, FAQs, evaluation criteria. Supports sub-folders. |

### 1.2 Supported File Formats

**Proposal Documents:**
- **Main Proposal**: DOCX (preferred) or PDF
- **Supporting Documents**: PDF or DOCX

**Solicitation Documents:**
- **PDF**: Main solicitation documents, Q&A addenda
- **CSV**: Evaluation criteria, scoring rubrics, structured data
- **MD**: Technical descriptions, FAQs, guidance documents

**Folder Organization:**
- All document types support sub-folder organization
- Files are discovered recursively in all sub-directories
- Maintains original folder structure in processing

### 1.3 Agent set (personas + LLM roles)

| Agent ID | Person | Focus | Hates | Output form |
|----------|--------|-------|-------|-------------|
| tech_lead | Eric Roulo | Feasibility, trades, elegance | Hand wavy physics, hidden assumptions | Bulleted risks, missing equations, unclear interfaces |
| business_strategist | Gerardo | Market, ROI, partners | Vague TAM, weak pricing | One page gap list (market story, pricing table, IP plan) |
| detail_checker | Assign | Solicitation checklist, format | Missing bullets, bad acronyms | Table: Criterion → Found? → Where → Fix |
| panel_scorer | Assign | Scores per criterion | Off criterion text | Table or JSON: Criterion → Score → ≤75 word why |
| storyteller | Assign (optional) | Narrative flow, clarity | Jargon walls | Marked up markdown with rewrite suggestions |

(Agent templates are stored in `src/agents/templates/` and can be customized.)

---

## 2. Snapshot the solicitation

```bash
poetry run ingest-solicitation
```

Defaults:
- Reads all PDF, CSV, and MD files in `documents/solicitation/` (including sub-folders)
- Writes to `output/`:
  - `criteria.json` (evaluation bullets)
  - `solicitation.md` (Markdown snapshot)

Review and trim if necessary. Keep exact criterion wording.

---

## 3. Prepare proposal and support docs

1. Confirm `documents/proposal/main_proposal.docx` uses proper headings (H1, H2) for best results. PDF is supported but DOCX preferred.
2. Place all supporting PDFs and DOCXs in `documents/proposal/supporting_docs/` (supports sub-folders).
3. The system automatically processes all documents and runs concurrent reviews.

---

## 4. Run the asynchronous multi agent review

### 4.1 Default run (all agents)
```bash
poetry run review
```
Uses:
- `documents/proposal/main_proposal.docx` (or .pdf)
- `documents/proposal/supporting_docs/` (PDF and DOCX)
- `output/criteria.json`
- Agents: tech_lead,business_strategist,detail_checker,panel_scorer,storyteller
- Output folder: `output/`

### 4.2 Custom agent configuration
```bash
poetry run review --agents tech_lead,business_strategist,panel_scorer
```

### 4.3 Override defaults (optional)
```bash
poetry run review   --proposal-dir documents/proposal   --supporting-dir documents/proposal/supporting_docs   --solicitation-dir documents/solicitation   --agents tech_lead,business_strategist
```

### 4.4 List available agents
```bash
poetry run list-agents
```

### 4.5 Visualize workflow structure
```bash
poetry run visualize-workflow
```

What happens:
- Documents are processed (DOCX with heading structure, PDFs to markdown, CSV to text).
- Each agent gets a tailored prompt from its template.
- Agents run concurrently using LangGraph workflow.
- Files are written as each agent finishes.

---

## 5. Outputs

All outputs are saved to the `output/` folder:

| File | Purpose |
|------|---------|
| `output/feedback/{agent_id}.md` | Agent-specific feedback and scores |
| `output/scorecard.json` | Consolidated scores and criteria mapping |
| `output/summary.md` | Executive summary with key findings |
| `output/action_items.md` | Prioritized action items for improvement |
| `output/criteria.json` | Extracted evaluation criteria from solicitation |
| `output/solicitation.md` | Solicitation markdown snapshot |
| `output/workflow.png` | Workflow visualization diagram |

---

## 6. File Format Support

### 6.1 Proposal Documents

**Main Proposal:**
- **DOCX** (preferred): Full heading structure preserved, best for analysis
- **PDF**: Converted to text, basic structure maintained

**Supporting Documents:**
- **PDF**: Converted to markdown text
- **DOCX**: Extracted as plain text with paragraph structure

### 6.2 Solicitation Documents

**PDF Files:**
- Main solicitation documents
- Q&A addenda
- Technical specifications
- Converted to markdown for processing

**CSV Files:**
- Evaluation criteria tables
- Scoring rubrics
- Structured data
- Converted to readable text format

**MD Files:**
- Technical descriptions
- FAQs and guidance
- Pre-formatted markdown content
- Used directly as-is

### 6.3 Folder Organization

The system supports flexible folder organization:

```
documents/
├── proposal/
│   ├── main_proposal.docx
│   └── supporting_docs/
│       ├── letters/
│       │   ├── support_letter_1.pdf
│       │   └── support_letter_2.docx
│       ├── resumes/
│       │   └── team_bios.pdf
│       └── technical/
│           └── technical_details.pdf
└── solicitation/
    ├── main_solicitation.pdf
    ├── criteria/
    │   ├── evaluation_criteria.csv
    │   └── scoring_rubric.csv
    ├── guidance/
    │   ├── technical_description.md
    │   └── faq.md
    └── addenda/
        └── qa_addendum.pdf
```

All files are discovered recursively and processed appropriately based on their format.

---

## 7. Troubleshooting

### 7.1 File Discovery Issues

**Problem**: "Main proposal not found"
**Solution**: 
- Ensure main proposal is named `main_proposal.docx` or `main_proposal.pdf`
- Check file is in `documents/proposal/` directory
- Verify file extension is correct

**Problem**: "No supporting documents found"
**Solution**:
- Check files are in `documents/proposal/supporting_docs/`
- Ensure files are PDF or DOCX format
- Verify files are not corrupted

**Problem**: "No solicitation documents found"
**Solution**:
- Check files are in `documents/solicitation/`
- Ensure files are PDF, CSV, or MD format
- Verify files are not corrupted

### 7.2 Processing Issues

**Problem**: "Failed to process PDF"
**Solution**:
- Check PDF is not password protected
- Verify PDF is not corrupted
- Try converting to DOCX if possible

**Problem**: "Failed to process CSV"
**Solution**:
- Check CSV encoding (should be UTF-8)
- Verify CSV has proper headers
- Ensure CSV is not corrupted

**Problem**: "Failed to process DOCX"
**Solution**:
- Check DOCX is not password protected
- Verify DOCX is not corrupted
- Try saving as DOCX format (not DOC)

---

## 8. Advanced Configuration

### 8.1 Custom File Patterns

The system uses these patterns to find files:

**Main Proposal:**
- `main_proposal.docx` (preferred)
- `*proposal*.docx`
- `*main*.docx`
- `main_proposal.pdf`
- `*proposal*.pdf`
- `*main*.pdf`

**Supporting Documents:**
- `*.pdf` (any PDF file)
- `*.docx` (any DOCX file)

**Solicitation Documents:**
- `*.pdf` (any PDF file)
- `*.csv` (any CSV file)
- `*.md` (any markdown file)

### 8.2 Sub-folder Support

All document types support sub-folder organization:

- Files are discovered recursively using `rglob()`
- Original folder structure is preserved in processing
- No depth limit on sub-folders
- Maintains file paths in output for reference

---

## 9. Performance Considerations

### 9.1 File Size Limits

- **PDF**: No artificial limits, natural LLM limits apply
- **DOCX**: No artificial limits, natural LLM limits apply
- **CSV**: No artificial limits, natural LLM limits apply
- **MD**: No artificial limits, natural LLM limits apply

### 9.2 Processing Speed

- **PDF**: Slower due to conversion process
- **DOCX**: Fastest processing
- **CSV**: Very fast processing
- **MD**: Instant processing

### 9.3 Memory Usage

- Large PDFs may use significant memory during conversion
- Consider splitting very large documents if needed
- System will encounter natural LLM limits rather than artificial truncation

---

## 10. Agent Templates

Agent behavior is defined by templates in `src/agents/templates/`:

### Template Structure
Each agent template contains:
- **Agent Identity**: Name, role, focus, hates
- **Expertise Areas**: Key areas of expertise
- **Critical Focus Areas**: What to be critical of
- **Output Format**: How to structure feedback
- **Scoring Criteria**: How to score (1.0-4.0 scale)
- **Review Style**: Tone and approach

### Customizing Agents
To modify agent behavior:
1. Edit the template file in `src/agents/templates/<agent_id>.md`
2. Restart the review process
3. The new template will be used automatically

### Adding New Agents
1. Create new template file: `src/agents/templates/new_agent.md`
2. Follow the template structure above
3. Use the agent: `poetry run review --agents new_agent`

---

## 11. System Architecture

The new system uses:
- **LangGraph**: Concurrent workflow orchestration
- **OpenAI**: Direct API calls with LangSmith tracing
- **Agent Templates**: Configurable agent behavior
- **python-docx**: Word document processing with heading structure
- **marker-pdf**: PDF to markdown conversion
- **csv**: CSV to text conversion
- **Pydantic**: Type-safe state management

Key improvements:
- Template-based agent configuration
- Concurrent agent execution
- Better error handling and recovery
- Structured output formats
- Modular agent system for easy extension
- LangSmith integration for observability
- Multi-format document support
- Sub-folder organization support
