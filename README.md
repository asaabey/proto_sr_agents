# Systematic Revie├── .gitignore                 # Git ignore rules
├── Makefile                  # Development workflow automation
├── pyproject.toml            # Project configuration (uv compatible)
├── .env.llm                  # LLM API configuration (not committed)
├── README.md                 # Main project documentation
├── requirements.txt          # Python dependencies (legacy support)ditor — Enhanced Multi‑Agent Platform

This is a **comprehensive multi‑agent platform** that audits systematic review manuscripts with advanced validation and statistical analysis capabilities. It provides a robust FastAPI service with three enhanced agents:

- **Enhanced PICO Parser**: validates question framing, outcome quality, population specificity, and composite outcome definitions
- **Comprehensive PRISMA Checker**: validates search strategies, protocol registration, study selection reporting, and flow diagram consistency  
- **Advanced Meta-Analysis**: performs fixed/random-effects analysis with heterogeneity assessment, forest plots, and funnel plots

> **Status**: Production-ready core functionality (~75% complete) with extensible architecture for additional agents.

## Project Structure

```
proto_sr_agents/
├── .claude/                    # Claude Code configuration and agents
│   ├── CLAUDE.md              # Development guidance for Claude Code
│   ├── PRD.MD                 # Product requirements document
│   └── agents/                # Custom Claude agents
├── .gitignore                 # Git ignore rules
├── .env.llm                   # LLM API configuration (not committed)
├── README.md                  # Main project documentation
├── requirements.txt           # Python dependencies
├── app/                       # Main application code
│   ├── main.py               # FastAPI application entry point
│   ├── orchestrator.py       # Agent coordination logic
│   ├── agents/               # Individual agent implementations
│   ├── models/               # Pydantic data models
│   ├── services/             # LLM clients, utilities, templates
│   └── utils/                # Helper functions and utilities
├── config/                    # Configuration templates
│   └── .env.llm.example      # Environment configuration template
├── docs/                      # Project documentation
│   ├── ANALYSIS_METADATA_INTEGRATION.md
│   ├── PHASE1_COMPLETE.md
│   └── README_LLM_INTEGRATION.md
├── tests/                     # Test suites
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── fixtures/             # Test data and fixtures
├── artifacts/                 # Generated outputs (plots, reports)
└── manuscripts/              # Test manuscript files (gitignored)
```

## Quickstart

### 1) Python env with uv
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Using Docker (Recommended for Production)
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run manually
docker build -t proto-sr-agents .
docker run -p 8000:8000 proto-sr-agents

# For development with hot reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Using Makefile (Convenient)
```bash
# Setup everything
make setup

# Run the application
make run

# Run tests
make test

# Format code
make format
```

### 3) Try it
From a separate terminal:
```bash
curl -s -X POST http://127.0.0.1:8000/review/start   -H "Content-Type: application/json"   -d @tests/sample_manuscript.json | jq
```

Or open Swagger UI: http://127.0.0.1:8000/docs

---

## What's inside

```
app/
  main.py             # FastAPI entrypoint with health check and review endpoints
  orchestrator.py     # Synchronous orchestrator coordinating all agents
  agents/
    pico_parser.py    # Enhanced PICO validation with outcome quality checks
    prisma_checker.py # Comprehensive PRISMA validation with protocol checks
    meta_analysis.py  # Statistical analysis with forest/funnel plot generation
  models/
    schemas.py        # Complete Pydantic models with evidence tracking
  utils/
    pdf_ingest.py     # PDF/Word ingestion architecture (structured placeholder)
tests/
  unit/               # Unit tests for individual agents
  integration/        # Full workflow integration tests
  sample_manuscript.json
artifacts/            # Generated plots and visualizations
requirements.txt      # Including matplotlib, seaborn, pytest
claude/
  CLAUDE.md          # Development guidance for Claude Code instances
```

---

## Current Implementation Status

### ✅ **Completed Features**
- **Enhanced PICO Validation**: Outcome timepoint checking, population specificity, composite outcome detection
- **Comprehensive PRISMA Auditing**: Protocol registration, search comprehensiveness, study selection reporting  
- **Statistical Meta-Analysis**: Fixed/random effects with DerSimonian-Laird, heterogeneity measures (Q, I², τ²)
- **Visualization Generation**: Forest plots and funnel plots (when matplotlib available)
- **DOCX Document Ingestion**: Automatic extraction from Word documents with NLP-enhanced PICO parsing
- **Structured Issue Reporting**: Severity levels, evidence tracking, actionable recommendations
- **File Upload API**: FastAPI endpoints for both structured JSON and DOCX file upload

### 🔄 **Next Steps (Roadmap)**
- Replace `orchestrator.simple_review()` with **LangGraph** state machine:
  - Nodes: Ingest → PICO → PRISMA → Extraction → Stats → RoB → GRADE → Reporter  
  - Edges: retry/branching; human approval gates
- Expand **Document Ingestion**:
  - **PDF Support**: GROBID for structure extraction, pdfplumber for tables
  - **Enhanced NLP**: spaCy for medical entity recognition and section classification
  - **Table Intelligence**: Advanced parsing for complex study characteristic tables
- Add specialized agents:
  - **Risk of Bias (RoB 2 / ROBINS‑I)** assessment
  - **GRADE** certainty evaluation per outcome
  - **Citations/Integrity** checking (Crossref, PubMed, retractions)
  - **PRISMA‑S** search strategy detailed auditing
- Enhanced analytics:
  - Leave-one-out sensitivity analysis
  - Automated reviewer reports (Markdown → PDF)
  - Advanced publication bias assessment (Egger's test, trim-and-fill)

---

## Key Features

### **Advanced Validation Engine**
- **PICO Quality Assessment**: Detects missing timepoints, vague populations, composite outcomes needing definition
- **PRISMA Compliance Checking**: Validates protocol registration, database diversity, search strategy completeness  
- **Study Characteristic Validation**: Ensures design reporting, sample size documentation, outcome consistency

### **Statistical Analysis**
- **Meta-Analysis**: Fixed and random-effects models with proper heterogeneity assessment
- **Publication Bias**: Funnel plot generation and asymmetry detection
- **Effect Size Visualization**: Professional forest plots with confidence intervals and study weights
- **Sensitivity Analysis**: Framework for leave-one-out and subgroup analyses

### **Document Processing & API**  
- **Multi-Format Support**: DOCX upload with automatic content extraction, JSON input for structured data
- **Intelligent Parsing**: Pattern matching + NLP for PICO elements, search strategies, flow diagrams
- **Table Extraction**: Study characteristics and outcome data from Word document tables
- **REST API**: FastAPI with file upload (`/review/upload`) and JSON endpoints (`/review/start`)
- **Comprehensive Validation**: File type checking, content validation, structured error responses

## Usage

### Command Line with uv
```bash
# Setup and run with uv
uv sync
uv run uvicorn app.main:app --reload

# Test with sample data
uv run curl -X POST http://127.0.0.1:8000/review/start -H "Content-Type: application/json" -d @tests/sample_manuscript.json
```

### File Upload
```bash
# Upload DOCX file for automatic extraction and review
curl -X POST http://127.0.0.1:8000/review/upload -F "file=@systematic_review.docx"

# Get upload requirements and capabilities
curl http://127.0.0.1:8000/upload/info
```

### API Documentation
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Notes

- **DOCX Support**: Full Word document ingestion with PICO extraction, search parsing, and table processing
- **JSON Input**: Pre-structured data with effect sizes and variances for immediate analysis
- **Optional Dependencies**: matplotlib/seaborn for plots, python-docx for file upload, spacy for enhanced NLP
- All outputs include structured **Issue** objects with severity levels, categories, evidence, and actionable recommendations.

