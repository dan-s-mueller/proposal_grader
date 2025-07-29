# Multi-Agent Proposal Review System

A modern, concurrent AI-powered system for evaluating SBIR/STTR proposals using multiple specialized agent personas with template-driven behavior.

## 🚀 Key Features

- **Template-Based Agents**: Configurable agent behavior via markdown templates
- **Concurrent Multi-Agent Review**: Specialized AI agents run simultaneously
- **LangGraph Workflow**: Robust orchestration with built-in error handling
- **PDF Document Support**: Native PDF processing with OCR and LLM enhancement
- **Comprehensive Logging**: Persistent logging to `output/review.log` for debugging
- **Modular Architecture**: Easy to add new agent types
- **Structured Outputs**: Agent-specific feedback + consolidated scores
- **Exception-Based Error Handling**: Clear error messages instead of fallback content

## 🏗️ Architecture

```
src/
├── agents/                   # Agent system
│   ├── templates/           # Agent behavior templates
│   │   ├── tech_lead.md
│   │   ├── business_strategist.md
│   │   ├── detail_checker.md
│   │   ├── panel_scorer.md
│   │   └── storyteller.md
│   ├── base_agent.py       # Generic agent class
│   └── agent_factory.py    # Agent creation and management
├── core/                    # Document processing
│   ├── document_processor.py
│   └── file_discovery.py
├── workflow/                # LangGraph orchestration
│   ├── review_graph.py
│   └── state_models.py
├── utils/                   # Output formatting
│   └── output_formatters.py
└── cli.py                   # Command interface
```

## 🎯 Agent System

| Agent ID | Persona | Focus | Output |
|----------|---------|-------|--------|
| **tech_lead** | Eric Roulo | Technical feasibility, elegance | Technical risks, missing equations |
| **business_strategist** | Gerardo Barrera | Market, ROI, partnerships | Market gaps, pricing analysis |
| **detail_checker** | Compliance Nerd | Solicitation checklist | Criterion → Found? → Where → Fix |
| **panel_scorer** | Panel Member | Criterion-based scoring | Score, Evidence, Reasoning, Improvements |
| **storyteller** | Narrative Expert | Flow, clarity | Markdown with rewrite suggestions |

## 📁 File Structure

```
proposal_grader/
├── documents/
│   ├── proposal/
│   │   ├── supporting_docs/      # Supporting PDFs, CSVs, and MDs (supports sub-folders)
│   │   ├── main_proposal.pdf     # Main proposal (PDF only)
│   |   └── processed/            # Cached processed documents
│   └── solicitation/             # Solicitation documents
│       ├── supporting_docs/      # Supporting solicitation docs (PDF, CSV, MD)
│       ├── criteria.json         # Static evaluation criteria (required)
│       └── processed/            # Cached processed documents
├── output/                       # All outputs
│   ├── feedback/
│   │   ├── tech_lead.md
│   │   ├── business_strategist.md
│   │   └── ...
│   ├── summary.md
│   ├── action_items.md
│   └── workflow.png
└── src/                         # Source code
└── src/agents/templates/         # Agent behavior templates
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies
poetry install

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key"
```

### 2. Prepare Documents
* documents/proposal/main_proposal.pdf (main proposal - PDF only)
* documents/proposal/supporting_docs/*.pdf, *.csv, *.md (supporting docs - supports sub-folders)
* documents/solicitation/main_solicitation.pdf (main solicitation PDF)
* documents/solicitation/criteria.json (static evaluation criteria - required)
* documents/solicitation/supporting_docs/*.pdf, *.csv, *.md (supporting solicitation docs)

### 3. Run Review

```bash
# Run with all agents (default)
poetry run review

# Run with specific agents
poetry run review --agents tech_lead,business_strategist,panel_scorer

# Skip document processing (use cached processed documents)
poetry run review --no-process-docs
```

## 📄 Supported File Formats

### Proposal Documents
- **Main Proposal**: PDF only - converted to markdown with OCR and LLM enhancement
- **Supporting Documents**: PDF, CSV, MD - converted to markdown with LLM enhancement

### Solicitation Documents  
- **PDF**: Main solicitation documents, Q&A addenda, technical specifications - converted to markdown with OCR and LLM enhancement
- **CSV**: Evaluation criteria tables, scoring rubrics, structured data - converted to readable text with LLM enhancement
- **MD**: Technical descriptions, FAQs, guidance documents - enhanced with LLM processing

### Document Processing Features
- **Unified Processing**: All documents processed using Marker with LLM enhancement
- **OCR Support**: Automatic OCR for PDF documents with text layout preservation
- **LLM Enhancement**: Uses GPT-4o for intelligent document analysis and conversion
- **Consistent Output**: All documents converted to structured markdown format
- **Exception-Based Error Handling**: Clear error messages when processing fails

### Folder Organization
- All document types support sub-folder organization
- Files are discovered recursively in all sub-directories
- No depth limit on sub-folders
- Maintains original folder structure in processing

## 📊 Outputs

All outputs are saved to the `output/` folder:

### Agent-Specific Feedback
- `output/feedback/tech_lead.md` - Technical feasibility review
- `output/feedback/business_strategist.md` - Business strategy review
- `output/feedback/detail_checker.md` - Compliance checklist
- `output/feedback/panel_scorer.md` - Criterion scores
- `output/feedback/storyteller.md` - Narrative feedback

### Consolidated Results
- `output/scorecard.json` - All scores (1.0-4.0 scale)
- `output/summary.md` - Executive summary
- `output/action_items.md` - Prioritized action items

### Logging and Debugging
- `output/review.log` - Persistent logging of all CLI commands and processing

### Workflow Visualization
- Only PNG output is supported: `output/workflow.png`

## 🔧 Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_MODEL="gpt-4o"  # Optional, defaults to gpt-4o
```

### Logging

All CLI commands automatically log to `output/review.log`:
- Command execution with timestamps
- Document processing status
- Agent execution progress
- Error messages and debugging information
- Workflow completion status

The log file is appended to on each run, providing a complete history of all system activity.

### Agent Configuration
```bash
# Run with specific agents
poetry run review --agents tech_lead,business_strategist

# Custom paths and agents
poetry run review \
  --proposal-dir custom/proposal \
  --agents tech_lead,panel_scorer \
  --output-dir custom/output
```

## 🎨 Agent Templates

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

## 🧪 Testing

Run the system test:
```bash
python test_system.py
```

## 📊 Workflow Visualization

Generate visual diagrams of the LangGraph workflow:

```bash
# Visualize default workflow
poetry run visualize

# Visualize with specific agents
poetry run visualize --agents tech_lead,business_strategist

# Custom output directory
poetry run visualize --output-dir workflow_diagrams
```

This generates:
- `workflow.png` - PNG diagram of the workflow
- `workflow.svg` - SVG diagram (better quality)

The visualization shows:
- Document processing as the initial step
- Agent nodes and their connections
- Concurrent execution paths
- Data flow through the system
- State transitions

## 🔄 Iterative Workflow

1. **Prepare**: Add proposal and supporting documents
2. **Review**: Run multi-agent review
3. **Analyze**: Check scores and action items
4. **Iterate**: Edit proposal based on feedback
5. **Repeat**: Re-run review until scores improve

## 🛠️ Development

### Adding New Agents

1. Create new template file in `src/agents/templates/`
2. Follow the template structure
3. Use the agent via CLI: `poetry run review --agents new_agent`

### Custom Scoring

Modify the scoring criteria in agent templates or override `extract_scores_from_feedback()` in `BaseAgent`.

## 📈 Performance

- **Concurrent Execution**: All agents run simultaneously
- **Template-Driven**: Agent behavior defined in markdown files
- **Error Recovery**: LangGraph handles agent failures gracefully
- **LangSmith Tracing**: Full observability of agent interactions

## 🔍 Monitoring

The system provides:
- Real-time progress indicators
- Agent completion status
- Comprehensive logging to `output/review.log`
- Error messages with context
- Performance metrics

## 🎯 Scoring Scale

| Score | Meaning |
|-------|---------|
| 4.0 | Outstanding, no significant weaknesses |
| 3.5 | Very strong, minor issues |
| 3.0 | Strong, some moderate issues |
| 2.5 | Adequate, several issues limit impact |
| 2.0 | Weak, major gaps |
| 1.5 | Very weak |
| 1.0 | Not responsive or fails criterion |

## 📝 Migration from Legacy System

The new system replaces the old single-role rubric-based system:

- **Old**: Sequential processing with LangChain
- **New**: Concurrent processing with LangGraph
- **Old**: Hard-coded role classes
- **New**: Template-driven agent system
- **Old**: CSV output only
- **New**: Markdown + JSON outputs
- **Old**: PDF-only processing
- **New**: PDF processing with OCR and LLM enhancement
- **Old**: No observability
- **New**: Comprehensive logging and error handling

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details. 

## 🧑‍💻 Structured Output for Scoring (Panel Scorer)

The panel scorer agent now uses **Pydantic structured output** with OpenAI function calling. This guarantees that all criterion scores are returned as valid JSON objects, parsed and validated by Pydantic. No more JSON decode errors or fragile regex parsing!

**Example output schema:**
```python
class CriterionScore(BaseModel):
    score: float
    evidence: str
    reasoning: str
    improvements: str
```

Each criterion is scored and returned as a validated object, ensuring robust and reliable downstream processing. 