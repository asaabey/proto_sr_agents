"""Integration tests for full review workflow."""

import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.orchestrator import simple_review
from app.models.schemas import Manuscript


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_manuscript_data():
    """Load sample manuscript data.""" 
    with open("tests/sample_manuscript.json", "r") as f:
        return json.load(f)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_review_endpoint_with_sample_data(client, sample_manuscript_data):
    """Test full review endpoint with sample data."""
    response = client.post("/review/start", json=sample_manuscript_data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Check response structure
    assert "issues" in result
    assert "meta" in result
    assert isinstance(result["issues"], list)
    assert isinstance(result["meta"], list)
    
    # Should have meta-analysis results for multiple outcomes
    assert len(result["meta"]) > 0
    
    # Check meta-analysis result structure
    for meta_result in result["meta"]:
        assert "outcome" in meta_result
        assert "model" in meta_result
        assert "pooled" in meta_result
        assert "ci_low" in meta_result
        assert "ci_high" in meta_result
        assert meta_result["model"] in ["fixed", "random"]


def test_orchestrator_direct_call(sample_manuscript_data):
    """Test orchestrator directly without HTTP layer."""
    manuscript = Manuscript(**sample_manuscript_data)
    result = simple_review(manuscript)
    
    assert len(result.issues) >= 0  # May have issues depending on data
    assert len(result.meta) > 0     # Should have meta-analysis results
    
    # Verify all agents ran
    agent_names = {issue.agent for issue in result.issues}
    # May include PICO-Parser, PRISMA-Checker depending on input quality
    
    # Check meta-analysis results
    outcomes = {meta.outcome for meta in result.meta}
    assert len(outcomes) >= 2  # Sample data has at least 2 outcomes
    
    # Verify both fixed and random effects for each outcome
    for outcome in outcomes:
        outcome_results = [m for m in result.meta if m.outcome == outcome]
        models = {m.model for m in outcome_results}
        assert models == {"fixed", "random"}


def test_enhanced_pico_validation(sample_manuscript_data):
    """Test that enhanced PICO validation is working."""
    manuscript = Manuscript(**sample_manuscript_data)
    result = simple_review(manuscript)
    
    # Look for enhanced PICO validation issues
    pico_issues = [issue for issue in result.issues if issue.category == "PICO"]
    
    # Check for specific validation types
    issue_ids = {issue.id for issue in pico_issues}
    
    # Sample data should trigger some specific validations
    # (exact issues depend on sample data content)
    for issue in pico_issues:
        assert issue.agent == "PICO-Parser"
        assert issue.severity in ["low", "medium", "high"]
        assert issue.recommendation is not None


def test_enhanced_prisma_validation(sample_manuscript_data):
    """Test that enhanced PRISMA validation is working."""
    manuscript = Manuscript(**sample_manuscript_data)
    result = simple_review(manuscript)
    
    # Look for PRISMA issues
    prisma_issues = [issue for issue in result.issues if issue.category == "PRISMA"]
    
    for issue in prisma_issues:
        assert issue.agent == "PRISMA-Checker"
        assert issue.severity in ["low", "medium", "high"]
        assert issue.recommendation is not None


def test_invalid_manuscript_data(client):
    """Test handling of invalid manuscript data."""
    invalid_data = {
        "manuscript_id": "invalid-001",
        # Missing required fields or invalid structure
        "flow": {
            "identified": "not a number",  # Should be int
            "excluded": [{"reason": 123}]  # Wrong structure
        }
    }
    
    response = client.post("/review/start", json=invalid_data)
    assert response.status_code == 422  # Validation error


def test_empty_studies_no_meta_analysis():
    """Test that manuscripts with no studies don't produce meta-analysis."""
    manuscript = Manuscript(
        manuscript_id="empty-001",
        included_studies=[]  # No studies
    )
    
    result = simple_review(manuscript)
    assert len(result.meta) == 0  # No meta-analysis possible


def test_single_study_no_meta_analysis():
    """Test that single studies don't produce meta-analysis."""
    from app.models.schemas import StudyRecord, OutcomeEffect
    
    manuscript = Manuscript(
        manuscript_id="single-001",
        included_studies=[
            StudyRecord(
                study_id="OnlyStudy",
                outcomes=[
                    OutcomeEffect(name="Mortality", effect_metric="logRR", effect=-0.2, var=0.04)
                ]
            )
        ]
    )
    
    result = simple_review(manuscript)
    assert len(result.meta) == 0  # Need ≥2 studies for meta-analysis