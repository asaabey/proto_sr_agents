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

### 1) Local Python env with uv (backend only)
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2) Using Docker (Recommended)

The repository now ships with a multi‑stage Docker build that compiles the React/Vite frontend and serves it via FastAPI as static assets.

Production / integrated image:
```bash
docker compose up --build
# App available: http://localhost:8000/ (serves frontend index) 
# API docs:      http://localhost:8000/docs
```

Manual build (optional):
```bash
docker build -t proto-sr-agents .
docker run -p 8000:8000 proto-sr-agents
```

Hot reload frontend + live backend (two containers):
```bash
docker compose up frontend-dev app
# Frontend dev server: http://localhost:5173
# Backend API:         http://localhost:8000
```

Rebuild after frontend code changes for production image:
```bash
docker compose build app
```

Key directories inside container:
- `/app/app/static` – compiled frontend (`frontend/dist` copied during build)
- Root route `/` serves `index.html` when present; assets under `/static/*`

Environment variables of interest:
- `VITE_API_BASE` (frontend) – defaults to `/`; set to full backend URL in dev container

Endpoint summary (when using integrated image):
- UI: `GET /`
- Static assets: `GET /static/<asset>`
- Health: `GET /health`
- Streaming review: `POST /review/start/stream`, `POST /review/upload/stream`

### 3) Using Makefile (Convenient)
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

### 4) Try it
From a separate terminal:
```bash
curl -s -X POST http://127.0.0.1:8000/review/start   -H "Content-Type: application/json"   -d @tests/sample_manuscript.json | jq
```

Or open Swagger UI: http://127.0.0.1:8000/docs

---

## Frontend (Web UI)

React + Vite + TypeScript + Tailwind UI in `frontend/` provides:
- DOCX upload + parse flow
- Live streaming (SSE) of multi‑agent progress, logs, completion
- Issue & meta‑analysis panels + raw JSON debug view

Development modes:
1. Integrated (served by FastAPI): build via Docker multi‑stage (no live reload).
2. Separate dev server: run `frontend-dev` compose service for HMR.

Local dev without Docker:
```bash
cd frontend
npm install   # or pnpm / yarn
npm run dev   # http://localhost:5173
```
Ensure backend running on :8000 (uvicorn or docker). Override API base if needed:
```bash
VITE_API_BASE=http://localhost:8000/ npm run dev
```

Build (outputs to `frontend/dist`):
```bash
npm run build
```

The Dockerfile copies `frontend/dist` to `app/app/static`. Root FastAPI route serves `index.html` when that directory exists.

SSE Event Types currently handled by UI store:
`agent_start`, `agent_complete`, `progress`, `log`, `extraction_complete`, `manuscript`, `complete`, `error`.

If extending backend events, also update `frontend/src/state.ts` and types.

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

### Streaming API for Live Updates

The platform now supports **Server-Sent Events (SSE)** for real-time progress updates during analysis:

#### Streaming Endpoints
- `POST /review/start/stream` - Stream analysis from JSON manuscript data
- `POST /review/upload/stream` - Stream analysis from uploaded DOCX file

#### Event Types (core)
- `agent_start` – Agent begins
- `agent_complete` – Agent finishes (includes running counts)
- `progress` – Generic progress note
- `log` – Backend log line (injected server-side)
- `extraction_complete` – Upload pipeline extracted manuscript
- `manuscript` – Final original manuscript echo (upload streaming path)
- `complete` – Final result payload (contains `data.result`)
- `error` – Error encountered

#### JavaScript Client Example
```javascript
// Connect to streaming analysis
const client = new StreamingReviewClient();

client.onEvent = (event) => {
    switch (event.event_type) {
        case 'agent_start':
            console.log(`🚀 Starting ${event.agent}`);
            break;
        case 'agent_complete':
            console.log(`✅ ${event.agent} found ${event.data.issues_found} issues`);
            break;
        case 'complete':
            console.log(`🎉 Complete! Total issues: ${event.data.total_issues}`);
            break;
    }
};

// Start streaming analysis
await client.streamFileAnalysis(fileInput.files[0]);
```

#### HTML Demo
Open `streaming_demo.html` in your browser for a complete UI example that shows:
- Live progress bar updates
- Real-time log streaming
- Agent-by-agent status updates
- Final results display

### API Documentation
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Notes

- **DOCX Support**: Word ingestion with PICO extraction, search parsing, table processing
- **JSON Input**: Pre‑structured data accepted for immediate streaming review
- **Static Frontend**: Built assets served at `/` + `/static/*` inside container
- **Optional Dependencies**: matplotlib/seaborn (plots), python-docx (ingestion), spacy (future NLP)
- **Structured Issues**: Severity, category, evidence, recommendation
- **Multi‑Stage Build**: Single image delivers API + UI; dev split available via compose

---

### Troubleshooting
| Symptom | Cause | Fix |
|---------|-------|-----|
| Frontend 404 on `/` | Static build missing | Run `docker compose build` or `npm run build` before image build |
| SSE stops early | Network/proxy buffering | Ensure no reverse proxy buffering SSE (disable gzip, enable flush) |
| No final result in UI | Missing `complete` event | Check backend logs; ensure `/review/*/stream` endpoint used |
| CORS issues in dev | Wrong `VITE_API_BASE` | Set `VITE_API_BASE=http://localhost:8000/` |


