from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pathlib import Path
import tempfile
import shutil
import json
import time
import logging
import uuid
from app.models.schemas import Manuscript, ReviewResult, StreamingEvent
from app.langraph_orchestrator import (
    run_multi_agent_review,
    run_enhanced_multi_agent_review,
    run_multi_agent_review_streaming,
)
from app.logstream import (
    ensure_handler_installed,
    register_listener,
    unregister_listener,
)
from app.utils.pdf_ingest import extract_manuscript_from_file

app = FastAPI(title="Systematic Review Auditor — Enhanced Platform")

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("sr_review")
if not logger.handlers:
    # Basic configuration only if not already configured by hosting env (e.g., uvicorn)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
logger.setLevel(logging.INFO)


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
        seq = 0
        ensure_handler_installed()
        log_queue, callback = register_listener()
        try:
            for event in run_multi_agent_review_streaming(manuscript):
                # Drain pending logs first
                while not log_queue.empty():
                    log_line = log_queue.get()
                    seq += 1
                    yield f"data: {json.dumps({'event_type':'log','sequence': seq,'message': log_line})}\n\n"
                data = {
                    "event_type": event.event_type,
                    "agent": event.agent,
                    "message": event.message,
                    "data": event.data,
                    "timestamp": event.timestamp,
                    "sequence": seq,
                }
                yield f"data: {json.dumps(data)}\n\n"
                seq += 1
            # Final drain
            while not log_queue.empty():
                log_line = log_queue.get()
                seq += 1
                yield f"data: {json.dumps({'event_type':'log','sequence': seq,'message': log_line})}\n\n"
        except Exception as e:
            error_data = {
                "event_type": "error",
                "message": f"Streaming failed: {str(e)}",
                "timestamp": "now",
                "sequence": seq,
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            unregister_listener(callback)

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
    request_id = uuid.uuid4().hex[:8]
    t_request_start = time.perf_counter()

    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        logger.warning(
            f"{request_id} | upload_and_review | invalid_file_type filename={file.filename}"
        )
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

    file_size = tmp_path.stat().st_size if tmp_path.exists() else -1
    logger.info(
        f"{request_id} | upload_and_review | file_saved name={file.filename} size_bytes={file_size}"
    )

    try:
        # Extract manuscript from file
        t_ext_start = time.perf_counter()
        logger.info(f"{request_id} | upload_and_review | extraction_start")
        manuscript = extract_manuscript_from_file(tmp_path)
        t_ext_end = time.perf_counter()
        logger.info(
            f"{request_id} | upload_and_review | extraction_done duration_ms={(t_ext_end - t_ext_start)*1000:.1f} title_present={manuscript.title is not None if manuscript else False} studies={len(manuscript.included_studies) if manuscript and manuscript.included_studies else 0}"
        )

        if manuscript is None:
            logger.error(
                f"{request_id} | upload_and_review | extraction_failed null_manuscript"
            )
            raise HTTPException(
                status_code=422,
                detail="Failed to extract manuscript data from uploaded file. "
                "Please ensure the document contains systematic review content with "
                "clear PICO elements, search strategies, and study data.",
            )

        # Run the review
        t_review_start = time.perf_counter()
        logger.info(f"{request_id} | upload_and_review | review_start")
        result = run_multi_agent_review(manuscript)
        t_review_end = time.perf_counter()
        logger.info(
            f"{request_id} | upload_and_review | review_done duration_ms={(t_review_end - t_review_start)*1000:.1f}"
        )
        # attach original manuscript structure for frontend editing/use
        result.manuscript = manuscript

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
        t_request_end = time.perf_counter()
        logger.info(
            f"{request_id} | upload_and_review | success total_duration_ms={(t_request_end - t_request_start)*1000:.1f}"
        )
        return result

    except HTTPException:
        # already logged above; just re-raise
        t_request_end = time.perf_counter()
        logger.exception(
            f"{request_id} | upload_and_review | http_exception total_duration_ms={(t_request_end - t_request_start)*1000:.1f}"
        )
        raise
    except Exception as e:
        t_request_end = time.perf_counter()
        logger.exception(
            f"{request_id} | upload_and_review | unexpected_error total_duration_ms={(t_request_end - t_request_start)*1000:.1f} error={e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing uploaded file: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/review/parse", response_model=Manuscript)
async def parse_manuscript(file: UploadFile = File(...)):
    """Parse a DOCX/DOC manuscript and return structured Manuscript without running analysis.

    This is a lightweight endpoint for the frontend to quickly obtain parsed JSON
    before initiating the heavier multi-agent review. Avoids user-facing stall during
    full analysis when they only expect parsing feedback.
    """
    request_id = uuid.uuid4().hex[:8]
    t_req_start = time.perf_counter()
    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        logger.warning(
            f"{request_id} | parse_manuscript | invalid_file_type filename={file.filename}"
        )
        raise HTTPException(
            status_code=400, detail="Only Word documents (.docx, .doc) are supported"
        )

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(file.filename).suffix
    ) as tmp_file:
        shutil.copyfileobj(file.file, tmp_file)
        tmp_path = Path(tmp_file.name)

    file_size = tmp_path.stat().st_size if tmp_path.exists() else -1
    logger.info(
        f"{request_id} | parse_manuscript | file_saved name={file.filename} size_bytes={file_size}"
    )

    try:
        t_ext_start = time.perf_counter()
        logger.info(f"{request_id} | parse_manuscript | extraction_start")
        manuscript = extract_manuscript_from_file(tmp_path)
        t_ext_end = time.perf_counter()
        logger.info(
            f"{request_id} | parse_manuscript | extraction_done duration_ms={(t_ext_end - t_ext_start)*1000:.1f} title_present={manuscript.title is not None if manuscript else False} studies={len(manuscript.included_studies) if manuscript and manuscript.included_studies else 0}"
        )
        if manuscript is None:
            logger.error(
                f"{request_id} | parse_manuscript | extraction_failed null_manuscript"
            )
            raise HTTPException(
                status_code=422,
                detail="Failed to extract manuscript data. Ensure document contains systematic review sections.",
            )
        t_req_end = time.perf_counter()
        logger.info(
            f"{request_id} | parse_manuscript | success total_duration_ms={(t_req_end - t_req_start)*1000:.1f}"
        )
        return manuscript
    except HTTPException:
        t_req_end = time.perf_counter()
        logger.exception(
            f"{request_id} | parse_manuscript | http_exception total_duration_ms={(t_req_end - t_req_start)*1000:.1f}"
        )
        raise
    except Exception as e:
        t_req_end = time.perf_counter()
        logger.exception(
            f"{request_id} | parse_manuscript | unexpected_error total_duration_ms={(t_req_end - t_req_start)*1000:.1f} error={e}"
        )
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@app.post("/review/upload/stream")
async def upload_and_review_streaming(file: UploadFile = File(...)):
    """Upload and review a manuscript from DOCX file with streaming progress."""

    request_id = uuid.uuid4().hex[:8]
    t_req_start = time.perf_counter()
    # Validate file type
    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        logger.warning(
            f"{request_id} | upload_and_review_streaming | invalid_file_type filename={file.filename}"
        )
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

    file_size = tmp_path.stat().st_size if tmp_path.exists() else -1
    logger.info(
        f"{request_id} | upload_and_review_streaming | file_saved name={file.filename} size_bytes={file_size}"
    )

    try:
        # Extract manuscript from file
        t_ext_start = time.perf_counter()
        logger.info(f"{request_id} | upload_and_review_streaming | extraction_start")
        manuscript = extract_manuscript_from_file(tmp_path)
        t_ext_end = time.perf_counter()
        logger.info(
            f"{request_id} | upload_and_review_streaming | extraction_done duration_ms={(t_ext_end - t_ext_start)*1000:.1f} title_present={manuscript.title is not None if manuscript else False} studies={len(manuscript.included_studies) if manuscript and manuscript.included_studies else 0}"
        )

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
            seq = 0
            try:
                logger.info(
                    f"{request_id} | upload_and_review_streaming | streaming_start"
                )
                # Yield extraction event first
                yield f"data: {json.dumps({'event_type': 'extraction_complete', 'sequence': seq, 'message': 'Document extracted successfully', 'data': extraction_info})}\n\n"
                seq += 1
                # Register log listener
                ensure_handler_installed()
                log_queue, callback = register_listener()
                try:
                    # Then stream the analysis events
                    for event in run_multi_agent_review_streaming(manuscript):
                        # Drain log queue before each event
                        while not log_queue.empty():
                            log_line = log_queue.get()
                            seq += 1
                            yield f"data: {json.dumps({'event_type':'log','sequence': seq,'message': log_line})}\n\n"
                        data = {
                            "event_type": event.event_type,
                            "agent": event.agent,
                            "message": event.message,
                            "data": event.data,
                            "timestamp": event.timestamp,
                            "sequence": seq,
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        seq += 1
                    # Final drain
                    while not log_queue.empty():
                        log_line = log_queue.get()
                        seq += 1
                        yield f"data: {json.dumps({'event_type':'log','sequence': seq,'message': log_line})}\n\n"
                finally:
                    unregister_listener(callback)
                # final manuscript payload event (not part of result schema but helpful for client)
                yield f"data: {json.dumps({'event_type':'manuscript','sequence': seq, 'message':'Original manuscript attached','data': {'manuscript': manuscript.dict()}})}\n\n"
                logger.info(
                    f"{request_id} | upload_and_review_streaming | streaming_complete total_events={seq+1}"
                )
            except Exception as e:
                error_data = {
                    "event_type": "error",
                    "message": f"Streaming failed: {str(e)}",
                    "timestamp": "now",
                }
                logger.exception(
                    f"{request_id} | upload_and_review_streaming | streaming_error error={e}"
                )
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

    except HTTPException:
        t_req_end = time.perf_counter()
        logger.exception(
            f"{request_id} | upload_and_review_streaming | http_exception total_duration_ms={(t_req_end - t_req_start)*1000:.1f}"
        )
        raise
    except Exception as e:
        t_req_end = time.perf_counter()
        logger.exception(
            f"{request_id} | upload_and_review_streaming | unexpected_error total_duration_ms={(t_req_end - t_req_start)*1000:.1f} error={e}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing uploaded file: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if tmp_path.exists():
            tmp_path.unlink()
        else:
            logger.warning(
                f"{request_id} | upload_and_review_streaming | tmp_file_missing_for_cleanup"
            )


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
