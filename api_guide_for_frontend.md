# Systematic Review Auditor API Guide for Frontend Development

This guide provides comprehensive documentation for integrating with the Systematic Review Auditor API, designed for use with frontend frameworks and platforms like lovable.dev.

## Base URL and Environment

```bash
# Development
API_BASE=http://127.0.0.1:8000/

# Production  
API_BASE=https://proto-sr-agents-api.docpockets.com/
```

## Core API Endpoints

### 1. Health Check
```http
GET /health
```
Simple health check endpoint.

**Response:**
```json
{ "status": "ok" }
```

### 2. Upload Information
```http
GET /upload/info
```
Get supported file formats and extraction requirements.

**Response:**
```json
{
  "supported_formats": [".docx", ".doc"],
  "requirements": {
    "document_structure": "Should contain systematic review sections",
    "pico_elements": "Population, Intervention, Comparator, Outcomes should be clearly stated",
    "search_strategy": "Database search details with dates and terms",
    "prisma_flow": "Flow diagram with study selection numbers",
    "study_tables": "Tables with study characteristics and outcome data"
  },
  "extraction_capabilities": {
    "pico_extraction": "Automatic PICO element identification using NLP",
    "search_parsing": "Database and search strategy extraction",
    "flow_extraction": "PRISMA flow diagram number extraction",
    "table_parsing": "Study characteristics and results from tables"
  }
}
```

### 3. LLM Status and Models
```http
GET /llm/status
GET /llm/models
```
Check LLM integration status and available models for enhanced analysis.

## Review Workflows

### Workflow 1: Document Upload + Parse Only
Use this for quick document validation before running full analysis.

```http
POST /review/parse
Content-Type: multipart/form-data
Body: FormData with 'file' field
```

**Response:** `Manuscript` object (see Data Models section)

### Workflow 2: Document Upload + Full Review (Non-streaming)
```http
POST /review/upload
Content-Type: multipart/form-data
Body: FormData with 'file' field
```

**Response:** `ReviewResult` object with embedded `manuscript` data

### Workflow 3: JSON Manuscript Review (Non-streaming)
```http
POST /review/start
Content-Type: application/json
Body: Manuscript JSON object
```

**Response:** `ReviewResult` object

### Workflow 4: Enhanced Review with LLM
```http
POST /review/enhanced?use_llm=true
Content-Type: application/json  
Body: Manuscript JSON object
```

**Response:** `ReviewResult` object with enhanced LLM analysis

## Streaming Endpoints (Recommended)

### Document Upload + Streaming Review
```http
POST /review/upload/stream
Content-Type: multipart/form-data
Body: FormData with 'file' field
```

### JSON Manuscript + Streaming Review  
```http
POST /review/start/stream
Content-Type: application/json
Body: Manuscript JSON object
```

**Response:** Server-Sent Events (SSE) stream

## Streaming Integration

### Server-Sent Events Format
All streaming endpoints return `text/event-stream` with the following headers:
```
Cache-Control: no-cache
Connection: keep-alive  
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: Cache-Control
```

### Event Structure
Each event follows this format:
```
data: {"event_type": "...", "message": "...", "data": {...}, "sequence": N}

```

### Event Types

#### 1. `extraction_complete` (Upload streams only)
Sent after document parsing completes.
```json
{
  "event_type": "extraction_complete",
  "sequence": 0,
  "message": "Document extracted successfully", 
  "data": {
    "source_file": "manuscript.docx",
    "manuscript_id": "ms_abc123",
    "extracted_elements": {
      "title": true,
      "pico": true, 
      "search_strategies": 3,
      "flow_counts": true,
      "studies": 15
    }
  }
}
```

#### 2. `agent_start`
Agent begins processing.
```json
{
  "event_type": "agent_start",
  "agent": "pico_parser",
  "message": "Starting PICO analysis...",
  "sequence": 1
}
```

#### 3. `agent_complete` 
Agent finishes processing.
```json
{
  "event_type": "agent_complete", 
  "agent": "pico_parser",
  "message": "PICO analysis complete",
  "data": {
    "issues_found": 2,
    "analysis_method": "llm-enhanced"
  },
  "sequence": 5
}
```

#### 4. `progress`
General progress updates.
```json
{
  "event_type": "progress",
  "message": "Analyzing study quality...",
  "sequence": 8
}
```

#### 5. `complete`
Final results available.
```json
{
  "event_type": "complete",
  "message": "Review complete",
  "data": {
    "result": {
      "issues": [...],
      "meta": [...],
      "analysis_metadata": {...},
      "manuscript": {...}
    }
  },
  "sequence": 20
}
```

#### 6. `log`
Backend log messages for debugging.
```json
{
  "event_type": "log", 
  "message": "INFO | Processing meta-analysis for outcome: mortality",
  "sequence": 12
}
```

#### 7. `error`
Error occurred during processing.
```json
{
  "event_type": "error",
  "message": "Analysis failed: Invalid study data format",
  "sequence": 15
}
```

### JavaScript/TypeScript Integration

#### Basic SSE Client
```javascript
async function startReviewStream(manuscript, onEvent, onError) {
    try {
        const response = await fetch('/review/start/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(manuscript)
        });
        
        if (!response.ok || !response.body) {
            throw new Error(`Stream failed: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // Process complete events
            let eventEnd;
            while ((eventEnd = buffer.indexOf('\n\n')) !== -1) {
                const rawEvent = buffer.slice(0, eventEnd).trim();
                buffer = buffer.slice(eventEnd + 2);
                
                const dataLine = rawEvent.split('\n')
                    .find(line => line.startsWith('data: '));
                
                if (dataLine) {
                    try {
                        const event = JSON.parse(dataLine.slice(6));
                        onEvent(event);
                    } catch (e) {
                        console.warn('Invalid event JSON:', e);
                    }
                }
            }
        }
    } catch (error) {
        onError(error);
    }
}
```

#### React Hook Example
```typescript
function useReviewStream() {
    const [events, setEvents] = useState<StreamEvent[]>([]);
    const [status, setStatus] = useState<'idle' | 'running' | 'complete' | 'error'>('idle');
    const [result, setResult] = useState<ReviewResult | null>(null);
    
    const startReview = useCallback(async (manuscript: Manuscript) => {
        setStatus('running');
        setEvents([]);
        
        await startReviewStream(
            manuscript,
            (event) => {
                setEvents(prev => [...prev, event]);
                
                if (event.event_type === 'complete' && event.data?.result) {
                    setResult(event.data.result);
                    setStatus('complete');
                } else if (event.event_type === 'error') {
                    setStatus('error');
                }
            },
            (error) => {
                console.error('Stream error:', error);
                setStatus('error');
            }
        );
    }, []);
    
    return { events, status, result, startReview };
}
```

## Data Models

### Manuscript Input Format
```typescript
interface Manuscript {
    manuscript_id: string;
    title?: string;
    journal?: string;
    submission_date?: string;
    question?: {
        framework: "PICO" | "PECO" | "PS" | "Other";
        population?: string;
        intervention?: string;
        comparator?: string;
        outcomes: string[];
    };
    protocol?: Record<string, any>;
    search: Array<{
        db: string;
        platform?: string;
        dates?: string;
        strategy?: string;
        limits: string[];
    }>;
    flow?: {
        identified?: number;
        deduplicated?: number;
        screened?: number;
        fulltext?: number;
        included?: number;
        excluded?: Array<{
            reason: string;
            n: number;
        }>;
    };
    included_studies: Array<{
        study_id: string;
        design?: string;
        n_total?: number;
        outcomes: Array<{
            name: string;
            effect_metric: "MD" | "SMD" | "OR" | "RR" | "HR" | "logOR" | "logRR" | "logHR";
            effect: number;  // log effect if log scale
            var: number;     // variance (SE²)
        }>;
    }>;
}
```

### Review Result Format
```typescript
interface ReviewResult {
    issues: Array<{
        id: string;
        severity: "low" | "medium" | "high";
        category: "PICO" | "PRISMA" | "STATS" | "DATA" | "OTHER";
        item: string;
        evidence?: Record<string, any>;
        recommendation?: string;
        agent?: string;
    }>;
    meta: Array<{
        outcome: string;
        k: number;  // number of studies
        model: "fixed" | "random";
        pooled: number;    // pooled effect
        se: number;        // standard error
        ci_low: number;    // 95% CI lower
        ci_high: number;   // 95% CI upper
        Q?: number;        // heterogeneity Q
        I2?: number;       // I² statistic  
        tau2?: number;     // τ² (tau-squared)
        evidence?: Record<string, any>;
    }>;
    extraction_info?: {
        source_file: string;
        manuscript_id: string;
        extracted_elements: Record<string, boolean | number>;
    };
    analysis_metadata?: {
        analysis_methods: Array<{
            agent: string;
            method: "rule-based" | "llm-enhanced" | "hybrid";
            llm_model?: string;
            llm_provider?: string;
            fallback_reason?: string;
        }>;
        llm_available: boolean;
        total_llm_calls: number;
        total_tokens_used?: number;
        estimated_cost?: number;
    };
    manuscript?: Manuscript;  // Embedded manuscript for editing
}
```

## Existing Frontend Components

The current React frontend includes these components that can serve as reference:

### Core Components
- **`ReviewController`** - Handles review initiation with streaming (`frontend/src/components/ReviewController.tsx`)
- **`ManuscriptUploader`** - File upload with drag-and-drop
- **`AgentStatusBoard`** - Real-time agent progress tracking  
- **`StreamConsole`** - Log message display
- **`IssuesPanel`** - Issue visualization and filtering
- **`MetaPanel`** - Meta-analysis results display

### State Management
The existing frontend uses a global state pattern:
```typescript
// frontend/src/state.ts
const { 
    manuscript, 
    reviewStatus, 
    issues, 
    metaResults,
    startReview, 
    updateFromEvent, 
    setError 
} = useAppState();
```

### API Integration  
Existing API client functions (`frontend/src/lib/api.ts`):
- `startStream()` - JSON manuscript streaming
- `uploadAndStream()` - File upload streaming  
- `uploadDocx()` - Parse-only upload
- `runFullUploadReview()` - Non-streaming upload + review

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Invalid file format or request
- `422` - Document parsing/extraction failed
- `500` - Internal server error

### Error Response Format
```json
{
    "detail": "Error message describing the issue"
}
```

### Streaming Error Events
```json
{
    "event_type": "error",
    "message": "Streaming failed: Connection timeout",
    "timestamp": "now",
    "sequence": 10
}
```

## CORS Configuration

The API includes CORS headers for frontend integration:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: Cache-Control
```

## Performance Recommendations

1. **Use streaming endpoints** for better UX during long-running analysis
2. **Parse documents first** (`/review/parse`) before full review to validate input
3. **Handle sequence numbers** to ensure event ordering in concurrent scenarios
4. **Implement reconnection logic** for network interruptions during streaming
5. **Cache LLM status** (`/llm/status`) to avoid repeated calls

## Integration Examples

### File Upload Flow
```javascript
// 1. Check supported formats
const uploadInfo = await fetch('/upload/info').then(r => r.json());

// 2. Parse document first (optional validation step)
const formData = new FormData();
formData.append('file', file);
const manuscript = await fetch('/review/parse', {
    method: 'POST', 
    body: formData
}).then(r => r.json());

// 3. Start streaming review
await startStreamingReview(manuscript, handleEvent, handleError);
```

### Progress Tracking
```javascript
function handleStreamEvent(event) {
    switch (event.event_type) {
        case 'agent_start':
            setProgress(prev => ({ ...prev, currentAgent: event.agent }));
            break;
        case 'agent_complete':
            setProgress(prev => ({ 
                ...prev, 
                completedAgents: [...prev.completedAgents, event.agent]
            }));
            break;
        case 'complete':
            setResult(event.data.result);
            setProgress({ status: 'complete' });
            break;
    }
}
```

This API provides a robust foundation for building systematic review auditing interfaces with real-time progress tracking and comprehensive analysis results.