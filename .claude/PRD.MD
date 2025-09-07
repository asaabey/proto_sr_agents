# Product Requirements Document (PRD)
Web UI for Multi‑Agent Systematic Review Auditing Platform

## 1. Objective
Provide a lightweight, modern web application for uploading systematic review manuscripts (DOCX or JSON), initiating an automated multi‑agent audit, and visualizing progress, agent outputs, issues, and meta‑analysis results (including plots) in near real time via streaming events.

## 2. Primary Users
1. Evidence Synthesis Researchers
2. Journal / Peer Review Editors
3. Internal QA / Audit Analysts

## 3. Core Value Proposition
Turn an uploaded manuscript (or structured JSON) into:
- Transparent multi‑agent audit trace (PICO → PRISMA → RoB → Meta-analysis)
- Categorized, severity-ranked issues with remediation suggestions
- Statistical synthesis, heterogeneity, and interpretation
- Downloadable structured review report (JSON / PDF in future phase)

## 4. In-Scope (Phase 1 MVP UI)
- Auth-less single-user UI (no login yet)
- Manuscript ingestion:
	- Upload DOCX (backend already extracts → JSON path assumed) OR paste raw JSON
	- Basic client validation (schema subset)

## 5. Future (Out-of-Scope Phase 1)
- User authentication & roles
- Persistent storage / database
- Multi-project dashboard
- PDF report generation
- GRADE / citation integrity additional agents
- Batch processing / queue management
- Editable agent prompts

## 6. Success Metrics (MVP)
- Time from upload to visible first event < 3s (SSE connect time)
- 100% of backend streamed events rendered without client errors
- Page Lighthouse performance score ≥ 85 (desktop)
- Zero blocking network calls after initial load (stream excluded)

## 7. UX Overview
Pages / Routes (client-side only):
- / (Dashboard / Single Flow)
	1. Upload & Input Panel (left/top)
	2. Live Stream Console (scrolling, tail pinned option)
	3. Agent Status Grid
	4. Tabs: Issues | Meta-analysis | Metadata | Raw JSON

Key Interactions:
1. User uploads file → client sends to `/review/upload` (NEW endpoint to implement) → returns parsed Manuscript JSON
2. User edits/validates JSON (optional) → Start Review
3. Client opens EventSource to `/review/start/stream` (POST emulation via signed init request or fallback to fetch-init endpoint returning job id then GET stream). If POST-only backend, implement lightweight `/review/start/init` returning job token used in `GET /review/stream/{job_id}`.
4. Events update UI progressively; final event exposes full ReviewResult.

## 8. Data Contracts (Frontend Expectations)
Existing (assumed) streaming event shape (SSE):
```
{
	"event_type": "agent_start|agent_progress|agent_complete|issue|meta_result|done|error",
	"message": "string",
	"agent": "PICO|PRISMA|ROB|META"?,
	"data": { ... }?
}
```
ReviewResult (condensed):
```
{
	manuscript_id: string,
	issues: Issue[],
	meta_result: { effect: float, ci_lower: float, ci_upper: float, model: string, i2: float, q: float, tau2: float }?,
	analysis_metadata: { llm: { model: string, tokens_used?: int }, agents: { name: string, status: string, method: string }[] }
}
```
Issue:
```
{ id: string, category: 'PICO'|'PRISMA'|'STATS'|'DATA'|'OTHER', severity: 'LOW'|'MEDIUM'|'HIGH', title: string, evidence: string, recommendation: string }
```

## 9. Technical Stack
Frontend:
- Vite + React + TypeScript
- Tailwind CSS + shadcn/ui (Radix primitives)
- React Query (server state + retries)
- Zod (schema validation for Manuscript subset)
- EventSource (native) or fetch ReadableStream fallback
- Zustand (lightweight client state) OR React Context (limited)
- ESLint + Prettier + Type checking (tsc --noEmit)

Backend Additions:
- `/review/upload` (multipart DOCX → parsed Manuscript JSON)
- Optional: `/review/start/init` returning { job_id } for GET-based SSE (if we refactor streaming contract)

## 10. State Model (Client)
```
AppState {
	manuscript: Manuscript | null,
	reviewStatus: 'idle'|'starting'|'running'|'completed'|'error',
	agentStates: Record<AgentName, { status: string; startedAt?: string; endedAt?: string; issues: Issue[] }>,
	streamEvents: StreamEvent[],
	finalResult?: ReviewResult,
	error?: string
}
```

## 11. Component Map
- ManuscriptUploader (file + JSON editor)
- ReviewController (Start / Cancel in future)
- StreamConsole (virtualized list)
- AgentStatusBoard (cards with progress indicators)
- IssuesPanel (filters, list)
- MetaAnalysisPanel (stats table + images; polling until artifacts ready)
- MetadataPanel (LLM + timings)
- JsonViewer (final raw output)
- ThemeToggle

## 12. Streaming Handling
Algorithm:
1. Open EventSource
2. On message parse JSON → dispatch to reducers:
	 - agent_start → set agent status Running
	 - issue → append to relevant agent issues
	 - meta_result → store meta_result
	 - agent_complete → set status Done
	 - error → set reviewStatus error & close
	 - done → attach final payload; close stream
3. Auto-scroll if user not scrolled up (threshold)

Edge Cases:
- Network drop → show reconnect banner (no auto-retry for MVP)
- Malformed JSON line → log + continue
- Duplicate issues (id collision) → de-dupe by id

## 13. Error Handling UX
- Toast + red banner for global errors
- Inline card states for any agent failure; allow viewing partial results

## 14. Accessibility & UI Guidelines
- WCAG AA color contrast
- Keyboard navigable tabs & filter controls (Radix + shadcn)
- ARIA live region for streaming log (polite)

## 15. Security / Privacy (MVP)
- No persistence; data ephemeral in browser
- CORS restricted via env ALLOWED_ORIGINS
- File size limit (e.g., 10MB) enforced client + server
- Reject scripts in JSON (sanitize displayed evidence/recommendation)

## 16. Performance Considerations
- Lazy load heavy panels (meta-analysis images) after first meta_result event
- Virtualize stream events if > 500
- Debounce issue filter input

## 17. Docker & Deployment (Planned)
Multi-stage build:
1. frontend-builder: node:20-alpine → build static assets to /app/dist
2. backend: python (slim) + uv (or requirements) → copy dist into /app/static
3. Serve: FastAPI + Uvicorn for API + StaticFile mount `/app` (index.html fallback)
Environment Variables:
- FRONTEND_PUBLIC_API_BASE (injected at build or runtime via small /config.json pattern)

## 18. Logging & Observability
- Client: console.warn on recoverable; structured event logging behind dev flag
- Backend: tag streamed events with monotonic sequence id (to assist ordering)

## 19. Phase 1 Delivery Checklist
Backend:
- [ ] Add `/review/upload` endpoint
- [ ] Ensure SSE endpoint stable contract
- [ ] Add sequence field to events
 - [ ] Return parsed Manuscript JSON structure consistent with existing schema (used by frontend after DOCX upload)
Frontend:
- [ ] Project scaffold (Vite + TS + Tailwind + shadcn init)
- [ ] Global theme + layout shell
- [ ] Manuscript upload & JSON editor (monaco or textarea MVP)
- [ ] Start Review flow (EventSource)
- [ ] Stream console
- [ ] Agent status board
- [ ] Issues panel w/ filters
- [ ] Meta-analysis panel (tables + images)
- [ ] Metadata panel
- [ ] Download JSON button
- [ ] Error & empty states
- [ ] Basic tests (component + stream reducer)
DevOps:
- [ ] Docker multi-stage build
- [ ] Makefile targets (dev, build, run)
- [ ] README update (UI usage)

## 20. Risks & Mitigations
- SSE behind proxies → Mitigate with proper headers (Cache-Control: no-transform)
- Large manuscripts → Add client size guard + streaming partial parse (future)
- Plot generation latency → Show skeleton loader + poll artifact endpoints

## 21. Open Questions
1. Will DOCX parsing endpoint exist already elsewhere? (Need spec)
2. Do we require cancellation of a running review? (Future WebSocket upgrade?)
3. Should we store past sessions locally (localStorage)? (Deferred)

## 22. Glossary
SSE: Server-Sent Events streaming unidirectional messages.
Agent: Autonomous analysis module (PICO / PRISMA / RoB / Meta-analysis).

---
Version: 0.1 (Initial Draft)
Owner: Platform Team
Next Review: +2 weeks after adoption

