# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup with uv
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Alternative: Using pyproject.toml (Recommended)
```bash
# Install with uv using pyproject.toml
uv sync

# Run the application
uv run uvicorn app.main:app --reload
```

### Traditional pip setup (if uv not available)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Running the Application
```bash
uvicorn app.main:app --reload
```

### Testing the API
```bash
# Test with sample data
curl -s -X POST http://127.0.0.1:8000/review/start -H "Content-Type: application/json" -d @tests/sample_manuscript.json | jq

# Access Swagger UI
open http://127.0.0.1:8000/docs
```

## Architecture

This is a **multi-agent systematic review auditing platform** built with FastAPI and LangGraph. The system uses a sophisticated multi-agent orchestrator that coordinates four specialized agents to audit systematic review manuscripts with full LLM integration.

### Core Components

- **FastAPI App** (`app/main.py`): Single endpoint `/review/start` that accepts a Manuscript and returns ReviewResult
- **LangGraph Orchestrator** (`app/langraph_orchestrator.py`): Multi-agent state machine with supervisor pattern coordinating: PICO → PRISMA → RoB → Meta-analysis
- **LLM Integration** (`app/services/`): OpenRouter-based LLM client with specialized prompts for each agent
- **Data Models** (`app/models/schemas.py`): Pydantic models for structured data including Manuscript, StudyRecord, Issue, and MetaResult

### Agent Architecture

Located in `app/agents/` - **All agents now use LLM-enhanced analysis**:
- **Enhanced PICO Parser** (`pico_parser_enhanced.py`): LLM-powered research question validation and PICO extraction
- **Enhanced PRISMA Checker** (`prisma_checker.py`): LLM-enhanced PRISMA compliance assessment with detailed recommendations
- **Enhanced RoB Assessor** (`rob_assessor.py`): LLM-powered risk of bias evaluation using RoB 2/ROBINS-I frameworks
- **Enhanced Meta-Analysis** (`meta_analysis.py`): Statistical analysis with LLM interpretation and clinical significance assessment

### LLM Integration

- **Provider**: OpenRouter (supports Claude, GPT-4, and other models)
- **Configuration**: Environment-based setup in `.env.llm`
- **Prompt Templates**: Specialized prompts for each agent type (`app/services/prompt_templates.py`)
- **Fallback Logic**: Graceful degradation to rule-based analysis if LLM fails

### Data Flow

1. Manuscript JSON → FastAPI endpoint
2. LangGraph orchestrator initializes multi-agent state
3. Supervisor agent routes to specialized agents sequentially
4. Each agent runs LLM-enhanced analysis, collecting Issues and metadata
5. Meta-analysis agent produces statistical results with LLM interpretation
6. Returns ReviewResult with comprehensive analysis metadata

### Key Data Structures

- **Manuscript**: Contains PICO question, search descriptors, flow counts, and included studies with effects
- **Issue**: Structured feedback with severity, category (PICO/PRISMA/STATS/DATA/OTHER), evidence, and recommendations
- **MetaResult**: Statistical results including pooled effects, confidence intervals, heterogeneity measures (Q, I², τ²)
- **AnalysisMetadata**: Tracks LLM usage, agent methods, and analysis completeness

### Current Capabilities

✅ **LangGraph Multi-Agent Orchestration**
✅ **Full LLM Integration Across All Agents**
✅ **OpenRouter LLM Provider Support**
✅ **Enhanced PICO Analysis with LLM Extraction**
✅ **LLM-Powered PRISMA Compliance Assessment**
✅ **Risk of Bias Assessment with LLM**
✅ **Meta-Analysis with LLM Interpretation**
✅ **Comprehensive Test Suite**

### Expected Input Format

The system expects manuscripts with **pre-extracted study effects** as OutcomeEffect objects containing effect sizes, variances, and metric types (MD/SMD/OR/RR/HR with log variants).

### Testing

```bash
# Test the multi-agent system
python test_langraph.py

# Test individual agents
python -m pytest tests/unit/ -v
```

### Future Enhancements

- Human-in-the-loop approval gates
- Additional specialized agents (GRADE evaluation, citation integrity)
- Web-based UI for manuscript upload and review
- Batch processing capabilities
- Integration with systematic review databases

### Notes for running terminal commands
- always activate venv
- never run uvicorn and curl in the same terminal as this will interrupt uvicorn