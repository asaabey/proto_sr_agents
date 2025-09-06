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

This is a **prototype multi-agent systematic review auditing platform** built with FastAPI. The system uses a simple synchronous orchestrator that coordinates three specialized agents to audit systematic review manuscripts.

### Core Components

- **FastAPI App** (`app/main.py`): Single endpoint `/review/start` that accepts a Manuscript and returns ReviewResult
- **Orchestrator** (`app/orchestrator.py`): Sequential coordinator that runs agents in order: PICO → PRISMA → Meta-analysis
- **Data Models** (`app/models/schemas.py`): Pydantic models for structured data including Manuscript, StudyRecord, Issue, and MetaResult

### Agent Architecture

Located in `app/agents/`:
- **PICO Parser** (`pico_parser.py`): Validates research question framing and normalizes outcomes
- **PRISMA Checker** (`prisma_checker.py`): Checks basic reporting completeness against PRISMA guidelines
- **Meta-Analysis** (`meta_analysis.py`): Recomputes fixed/random-effects meta-analysis from provided study effects

### Data Flow

1. Manuscript JSON → FastAPI endpoint
2. Orchestrator runs agents sequentially, collecting Issues
3. Meta-analysis agent produces MetaResults for outcomes
4. Returns ReviewResult containing all issues and meta-analysis results

### Key Data Structures

- **Manuscript**: Contains PICO question, search descriptors, flow counts, and included studies with effects
- **Issue**: Structured feedback with severity, category (PICO/PRISMA/STATS/DATA/OTHER), evidence, and recommendations
- **MetaResult**: Statistical results including pooled effects, confidence intervals, heterogeneity measures (Q, I², τ²)

### Expected Input Format

The system expects manuscripts with **pre-extracted study effects** as OutcomeEffect objects containing effect sizes, variances, and metric types (MD/SMD/OR/RR/HR with log variants).

### Future Architecture Notes

The current synchronous orchestrator is designed to be replaced with **LangGraph** for:
- State machine workflow with retry/branching logic
- Human-in-the-loop approval gates  
- Additional agents for RoB assessment, GRADE evaluation, citation integrity checking