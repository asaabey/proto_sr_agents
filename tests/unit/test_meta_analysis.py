"""Unit tests for meta-analysis agent."""

import pytest
import math
from pathlib import Path
from app.agents.meta_analysis import run, _fixed_effect, _random_effect
from app.models.schemas import Manuscript, StudyRecord, OutcomeEffect


@pytest.fixture
def sample_studies():
    """Create sample studies with effect sizes."""
    return [
        StudyRecord(
            study_id="Study1",
            design="RCT",
            n_total=200,
            outcomes=[
                OutcomeEffect(name="Mortality", effect_metric="logRR", effect=-0.2, var=0.04),
                OutcomeEffect(name="Kidney function", effect_metric="logRR", effect=-0.1, var=0.03)
            ]
        ),
        StudyRecord(
            study_id="Study2", 
            design="RCT",
            n_total=150,
            outcomes=[
                OutcomeEffect(name="Mortality", effect_metric="logRR", effect=-0.15, var=0.05),
                OutcomeEffect(name="Kidney function", effect_metric="logRR", effect=-0.05, var=0.035)
            ]
        ),
        StudyRecord(
            study_id="Study3",
            design="RCT", 
            n_total=180,
            outcomes=[
                OutcomeEffect(name="Mortality", effect_metric="logRR", effect=-0.1, var=0.045)
            ]
        )
    ]


def test_fixed_effect_calculation():
    """Test fixed-effects meta-analysis calculation."""
    effects = [
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.2, var=0.04),
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.1, var=0.05),
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.15, var=0.03)
    ]
    
    result = _fixed_effect(effects)
    
    assert result.k == 3
    assert result.model == "fixed"
    assert abs(result.pooled - (-0.155)) < 0.01  # Approximate weighted average
    assert result.se > 0
    assert result.ci_low < result.pooled < result.ci_high
    assert result.Q >= 0
    assert result.I2 >= 0


def test_random_effect_calculation():
    """Test random-effects meta-analysis calculation.""" 
    effects = [
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.2, var=0.04),
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.1, var=0.05),
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.15, var=0.03)
    ]
    
    result = _random_effect(effects)
    
    assert result.k == 3
    assert result.model == "random"
    assert result.se > 0
    assert result.ci_low < result.pooled < result.ci_high
    assert result.Q >= 0
    assert result.I2 >= 0
    assert result.tau2 >= 0


def test_single_study_excluded():
    """Test that single studies are excluded from meta-analysis."""
    studies = [
        StudyRecord(
            study_id="OnlyStudy",
            outcomes=[
                OutcomeEffect(name="Rare outcome", effect_metric="logRR", effect=-0.3, var=0.1)
            ]
        )
    ]
    
    manuscript = Manuscript(manuscript_id="test-single", included_studies=studies)
    results = run(manuscript)
    
    # Should be empty since we need ≥2 studies
    assert len(results) == 0


def test_multiple_outcomes_grouped(sample_studies):
    """Test that outcomes are properly grouped by name."""
    manuscript = Manuscript(manuscript_id="test-multi", included_studies=sample_studies)
    results = run(manuscript)
    
    # Should have 2 outcomes × 2 models = 4 results
    assert len(results) == 4
    
    mortality_results = [r for r in results if r.outcome == "Mortality"]
    kidney_results = [r for r in results if r.outcome == "Kidney function"]
    
    assert len(mortality_results) == 2  # Fixed + Random
    assert len(kidney_results) == 2    # Fixed + Random
    
    # Check that we have both model types for each outcome
    mortality_models = {r.model for r in mortality_results}
    assert mortality_models == {"fixed", "random"}


def test_forest_plot_generation(sample_studies, tmp_path):
    """Test that forest plots are generated and referenced."""
    # Change to temp directory for test artifacts
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        
        manuscript = Manuscript(manuscript_id="test-plots", included_studies=sample_studies)
        results = run(manuscript)
        
        # Check that evidence contains plot paths
        mortality_results = [r for r in results if r.outcome == "Mortality"]
        
        for result in mortality_results:
            if result.evidence and "forest_plot" in result.evidence:
                forest_path = Path(result.evidence["forest_plot"])
                assert forest_path.exists()
                assert forest_path.suffix == ".png"
                
    finally:
        os.chdir(original_cwd)


def test_heterogeneity_calculation():
    """Test I² calculation for heterogeneous studies.""" 
    # Create studies with more heterogeneous effects
    heterogeneous_effects = [
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.5, var=0.04),  # Large effect
        OutcomeEffect(name="Test", effect_metric="logRR", effect=0.2, var=0.04),   # Opposite effect
        OutcomeEffect(name="Test", effect_metric="logRR", effect=-0.1, var=0.04)   # Small effect
    ]
    
    fe_result = _fixed_effect(heterogeneous_effects)
    re_result = _random_effect(heterogeneous_effects)
    
    # Should detect heterogeneity
    assert fe_result.I2 > 50  # High heterogeneity
    assert re_result.tau2 > 0  # Between-study variance present
    assert re_result.se > fe_result.se  # Random effects should have wider CI