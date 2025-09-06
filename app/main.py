from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pathlib import Path
import tempfile
import shutil
import json
from app.models.schemas import Manuscript, ReviewResult, StreamingEvent
from app.langraph_orchestrator import (
    run_multi_agent_review,
    run_enhanced_multi_agent_review,
    run_multi_agent_review_streaming,
)
from app.utils.pdf_ingest import extract_manuscript_from_file

app = FastAPI(title="Systematic Review Auditor — Enhanced Platform")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/review/start", response_model=ReviewResult)
def start_review(manuscript: Manuscript):
    """Review a manuscript from structured JSON data."""
    return run_multi_agent_review(manuscript)


@app.post("/review/start/stream")
def start_review_streaming(manuscript: Manuscript):
    """Review a manuscript with streaming progress updates via Server-Sent Events."""

    def generate_events():
        try:
            for event in run_multi_agent_review_streaming(manuscript):
                # Format as Server-Sent Event
                data = {
                    "event_type": event.event_type,
                    "agent": event.agent,
                    "message": event.message,
                    "data": event.data,
                    "timestamp": event.timestamp,
                }
                yield f"data: {json.dumps(data)}\n\n"
        except Exception as e:
            error_data = {
                "event_type": "error",
                "message": f"Streaming failed: {str(e)}",
                "timestamp": "now",
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@app.post("/review/enhanced", response_model=ReviewResult)
def start_enhanced_review(manuscript: Manuscript, use_llm: bool = True):
    """Enhanced review with LLM-powered analysis when available."""
    return run_enhanced_multi_agent_review(manuscript, use_llm=use_llm)


@app.post("/review/upload", response_model=ReviewResult)
async def upload_and_review(file: UploadFile = File(...)):
    """Upload and review a manuscript from DOCX file."""

    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail="Only Word documents (.docx, .doc) are currently supported",
        )

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(file.filename).suffix
    ) as tmp_file:
        # Copy uploaded content to temporary file
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        # Extract manuscript from file
        manuscript = extract_manuscript_from_file(tmp_path)

        if manuscript is None:
            raise HTTPException(
                status_code=422,
                detail="Failed to extract manuscript data from uploaded file. "
                "Please ensure the document contains systematic review content with "
                "clear PICO elements, search strategies, and study data.",
            )

        # Run the review
        result = run_multi_agent_review(manuscript)

        # Add extraction info to response
        result.extraction_info = {
            "source_file": file.filename,
            "manuscript_id": manuscript.manuscript_id,
            "extracted_elements": {
                "title": manuscript.title is not None,
                "pico": manuscript.question is not None,
                "search_strategies": len(manuscript.search) if manuscript.search else 0,
                "flow_counts": manuscript.flow is not None,
                "studies": (
                    len(manuscript.included_studies)
                    if manuscript.included_studies
                    else 0
                ),
            },
        }

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing uploaded file: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/review/upload/stream")
async def upload_and_review_streaming(file: UploadFile = File(...)):
    """Upload and review a manuscript from DOCX file with streaming progress."""

    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        raise HTTPException(
            status_code=400,
            detail="Only Word documents (.docx, .doc) are currently supported",
        )

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(file.filename).suffix
    ) as tmp_file:
        # Copy uploaded content to temporary file
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = Path(tmp_file.name)

    try:
        # Extract manuscript from file
        manuscript = extract_manuscript_from_file(tmp_path)

        if manuscript is None:
            raise HTTPException(
                status_code=422,
                detail="Failed to extract manuscript data from uploaded file. "
                "Please ensure the document contains systematic review content with "
                "clear PICO elements, search strategies, and study data.",
            )

        # Add extraction info to streaming data
        extraction_info = {
            "source_file": file.filename,
            "manuscript_id": manuscript.manuscript_id,
            "extracted_elements": {
                "title": manuscript.title is not None,
                "pico": manuscript.question is not None,
                "search_strategies": len(manuscript.search) if manuscript.search else 0,
                "flow_counts": manuscript.flow is not None,
                "studies": (
                    len(manuscript.included_studies)
                    if manuscript.included_studies
                    else 0
                ),
            },
        }

        def generate_events():
            try:
                # Yield extraction event first
                yield f"data: {json.dumps({'event_type': 'extraction_complete', 'message': 'Document extracted successfully', 'data': extraction_info})}\n\n"

                # Then stream the analysis events
                for event in run_multi_agent_review_streaming(manuscript):
                    data = {
                        "event_type": event.event_type,
                        "agent": event.agent,
                        "message": event.message,
                        "data": event.data,
                        "timestamp": event.timestamp,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                error_data = {
                    "event_type": "error",
                    "message": f"Streaming failed: {str(e)}",
                    "timestamp": "now",
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            generate_events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing uploaded file: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if tmp_path.exists():
            tmp_path.unlink()


@app.get("/upload/info")
def upload_info():
    """Get information about supported upload formats and requirements."""
    return {
        "supported_formats": [".docx", ".doc"],
        "requirements": {
            "document_structure": "Should contain systematic review sections",
            "pico_elements": "Population, Intervention, Comparator, Outcomes should be clearly stated",
            "search_strategy": "Database search details with dates and terms",
            "prisma_flow": "Flow diagram with study selection numbers",
            "study_tables": "Tables with study characteristics and outcome data",
        },
        "extraction_capabilities": {
            "pico_extraction": "Automatic PICO element identification using NLP",
            "search_parsing": "Database and search strategy extraction",
            "flow_extraction": "PRISMA flow diagram number extraction",
            "table_parsing": "Study characteristics and results from tables",
        },
        "note": "PDF support coming soon. For now, convert PDFs to Word format for optimal extraction.",
    }


@app.get("/llm/status")
def llm_status():
    """Get LLM integration status and available models."""
    try:
        from app.services.llm_config import get_llm_environment

        env = get_llm_environment()
        status = env.validate_setup()
        return {
            "llm_available": status["configured"],
            "providers": status["providers"],
            "warnings": status["warnings"],
            "recommendations": status["recommendations"],
            "default_provider": env.settings.default_provider,
            "default_model": env.settings.default_model,
        }
    except Exception as e:
        return {
            "llm_available": False,
            "error": str(e),
            "message": "LLM integration not available",
        }


@app.get("/llm/models")
def llm_models():
    """Get available LLM models and their recommended use cases."""
    try:
        from app.services.llm_config import get_llm_environment

        env = get_llm_environment()
        models = {}
        for model_id, config in env.settings.models.items():
            models[model_id] = {
                "name": config.name,
                "provider": config.provider,
                "cost_per_1k_tokens": config.cost_per_1k_tokens,
                "recommended_use": config.recommended_use,
                "max_tokens": config.max_tokens,
            }
        return {"available_models": models, "default_model": env.settings.default_model}
    except Exception as e:
        return {"error": str(e), "message": "Could not load model configurations"}
