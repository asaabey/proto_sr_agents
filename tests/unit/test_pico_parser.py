"""Unit tests for PICO parser agent."""

import pytest
from app.agents.pico_parser import run
from app.models.schemas import Manuscript, PICO


def test_missing_pico_question():
    """Test detection of completely missing PICO question."""
    manuscript = Manuscript(manuscript_id="test-001")
    issues = run(manuscript)
    
    assert len(issues) == 1
    assert issues[0].id == "PICO-001"
    assert issues[0].severity == "high"
    assert "population" in issues[0].evidence["missing"]
    assert "intervention" in issues[0].evidence["missing"]


def test_incomplete_pico_elements():
    """Test detection of incomplete PICO elements."""
    pico = PICO(
        framework="PICO",
        population="Adults with CKD",
        intervention=None,  # Missing
        comparator="Placebo",
        outcomes=[]  # Missing
    )
    manuscript = Manuscript(manuscript_id="test-002", question=pico)
    issues = run(manuscript)
    
    assert len(issues) >= 1
    pico_issues = [i for i in issues if i.id == "PICO-001"]
    assert len(pico_issues) == 1
    assert "intervention" in pico_issues[0].evidence["missing"]
    assert "outcomes" in pico_issues[0].evidence["missing"]


def test_outcomes_without_timepoints():
    """Test detection of outcomes lacking timepoints."""
    pico = PICO(
        framework="PICO",
        population="Adults with CKD stages 2-4",
        intervention="ACE inhibitor",
        comparator="Placebo",
        outcomes=["Mortality", "Kidney function decline"]  # No timepoints
    )
    manuscript = Manuscript(manuscript_id="test-003", question=pico)
    issues = run(manuscript)
    
    timepoint_issues = [i for i in issues if i.id == "PICO-002"]
    assert len(timepoint_issues) == 1
    assert timepoint_issues[0].severity == "low"


def test_composite_outcomes():
    """Test detection of composite outcomes needing definition."""
    pico = PICO(
        framework="PICO",
        population="Adults with CKD stages 2-4",
        intervention="ACE inhibitor",
        comparator="Placebo", 
        outcomes=["Major adverse events composite", "1-year mortality"]
    )
    manuscript = Manuscript(manuscript_id="test-004", question=pico)
    issues = run(manuscript)
    
    composite_issues = [i for i in issues if i.id == "PICO-003"]
    assert len(composite_issues) == 1
    assert "Major adverse events composite" in composite_issues[0].evidence["composite_outcomes"]


def test_population_age_specification():
    """Test detection of missing age specification in population."""
    pico = PICO(
        framework="PICO",
        population="Patients with heart failure",  # No age specified
        intervention="ACE inhibitor",
        comparator="Placebo",
        outcomes=["6-month mortality"]
    )
    manuscript = Manuscript(manuscript_id="test-005", question=pico)
    issues = run(manuscript)
    
    age_issues = [i for i in issues if i.id == "PICO-004"]
    assert len(age_issues) == 1
    assert age_issues[0].severity == "low"


def test_complete_pico_with_good_outcomes():
    """Test that well-specified PICO generates minimal issues."""
    pico = PICO(
        framework="PICO",
        population="Adults aged 18-75 years with stage 3-4 CKD",
        intervention="ACE inhibitor therapy",
        comparator="Placebo or usual care",
        outcomes=["6-month all-cause mortality", "1-year eGFR decline ≥40%"]
    )
    manuscript = Manuscript(manuscript_id="test-006", question=pico)
    issues = run(manuscript)
    
    # Should have minimal issues - maybe only severity specification
    severity_issues = [i for i in issues if i.id == "PICO-005"]
    assert len(severity_issues) == 1  # Population lacks severity/stage info
    
    # Should NOT have completeness, timepoint, or age issues
    assert not any(i.id == "PICO-001" for i in issues)  # No missing elements
    assert not any(i.id == "PICO-002" for i in issues)  # Timepoints present
    assert not any(i.id == "PICO-004" for i in issues)  # Age specified