from typing import List
import re
import logging
from app.models.schemas import Manuscript, Issue

logger = logging.getLogger("agents.pico_parser")

def _validate_outcome_quality(outcomes: List[str]) -> List[Issue]:
    """Validate outcome specification quality"""
    issues = []
    
    # Check for time-specific outcomes
    time_keywords = ["week", "month", "year", "day", "follow-up", "endpoint"]
    outcomes_with_time = [o for o in outcomes if any(kw in o.lower() for kw in time_keywords)]
    
    if len(outcomes_with_time) < len(outcomes) * 0.5:  # Less than half have timepoints
        issues.append(Issue(
            id="PICO-002",
            severity="low",
            category="PICO",
            item="Outcomes lack specific timepoints",
            evidence={"outcomes": outcomes, "with_timepoints": len(outcomes_with_time)},
            recommendation="Specify clear timepoints for outcomes (e.g., '6-month mortality', '1-year eGFR decline').",
            agent="PICO-Parser"
        ))
    
    # Check for composite outcomes without component specification
    composite_keywords = ["composite", "combined", "major", "composite of"]
    composite_outcomes = [o for o in outcomes if any(kw in o.lower() for kw in composite_keywords)]
    
    if composite_outcomes:
        issues.append(Issue(
            id="PICO-003",
            severity="medium",
            category="PICO",
            item="Composite outcomes may need component definition",
            evidence={"composite_outcomes": composite_outcomes},
            recommendation="Define individual components of composite outcomes and justify combination.",
            agent="PICO-Parser"
        ))
    
    return issues

def _validate_population_specificity(population: str) -> List[Issue]:
    """Check population description specificity"""
    issues = []
    
    # Check for age specification
    age_pattern = r'\b(age[sd]?|year[s]?|\d+\s*[-–]\s*\d+|\d+\+|adult[s]?|pediatric|child|elderly)\b'
    if not re.search(age_pattern, population.lower()):
        issues.append(Issue(
            id="PICO-004",
            severity="low", 
            category="PICO",
            item="Population lacks age specification",
            evidence={"population": population},
            recommendation="Specify target age range or demographic (e.g., 'adults ≥18 years', 'children 2-17 years').",
            agent="PICO-Parser"
        ))
    
    # Check for severity/stage specification for conditions
    severity_keywords = ["stage", "grade", "severity", "mild", "moderate", "severe", "early", "advanced"]
    if not any(kw in population.lower() for kw in severity_keywords):
        issues.append(Issue(
            id="PICO-005",
            severity="low",
            category="PICO", 
            item="Population may need disease severity/stage specification",
            evidence={"population": population},
            recommendation="Consider specifying disease stage, severity, or functional status if relevant.",
            agent="PICO-Parser"
        ))
        
    return issues

def run(manuscript: Manuscript) -> List[Issue]:
    logger.info("🎯 [PICO-Parser] Starting rule-based PICO analysis...")
    issues: List[Issue] = []
    q = manuscript.question
    
    # Basic completeness check
    logger.debug("🔍 [PICO-Parser] Checking PICO completeness...")
    missing = []
    if not q:
        logger.warning("❌ [PICO-Parser] No PICO question found in manuscript")
        missing = ["population","intervention","comparator","outcomes"]
    else:
        logger.info("✓ [PICO-Parser] PICO question found, validating components...")
        if not q.population: 
            missing.append("population")
            logger.debug("❌ [PICO-Parser] Missing population")
        else:
            logger.debug(f"✓ [PICO-Parser] Population: {q.population[:50]}...")
            
        if not q.intervention: 
            missing.append("intervention")
            logger.debug("❌ [PICO-Parser] Missing intervention")
        else:
            logger.debug(f"✓ [PICO-Parser] Intervention: {q.intervention[:50]}...")
            
        if q.comparator is None: 
            missing.append("comparator")
            logger.debug("❌ [PICO-Parser] Missing comparator")
        else:
            logger.debug(f"✓ [PICO-Parser] Comparator: {q.comparator[:50]}...")
            
        if not q.outcomes: 
            missing.append("outcomes")
            logger.debug("❌ [PICO-Parser] Missing outcomes")
        else:
            logger.debug(f"✓ [PICO-Parser] Outcomes: {len(q.outcomes)} specified")
        
    if missing:
        severity = "high" if len(missing) > 2 else "medium"
        logger.warning(f"⚠️ [PICO-Parser] Incomplete PICO - missing {len(missing)} components: {', '.join(missing)} (severity: {severity})")
        issues.append(Issue(
            id="PICO-001",
            severity=severity,
            category="PICO",
            item="Incomplete PICO specification",
            evidence={"missing": missing},
            recommendation="Provide explicit PICO fields; list concrete primary/secondary outcomes with timepoints.",
            agent="PICO-Parser"
        ))
    
    # Enhanced validation if PICO is present
    if q:
        logger.info("🔍 [PICO-Parser] Running enhanced PICO validation...")
        
        if q.outcomes:
            logger.debug("🎯 [PICO-Parser] Validating outcome quality...")
            outcome_issues = _validate_outcome_quality(q.outcomes)
            issues.extend(outcome_issues)
            if outcome_issues:
                logger.info(f"⚠️ [PICO-Parser] Found {len(outcome_issues)} outcome quality issues")
            
        if q.population:
            logger.debug("👥 [PICO-Parser] Validating population specificity...")
            pop_issues = _validate_population_specificity(q.population)
            issues.extend(pop_issues)
            if pop_issues:
                logger.info(f"⚠️ [PICO-Parser] Found {len(pop_issues)} population specificity issues")
            
        # Framework appropriateness check
        if q.framework not in ["PICO", "PECO"]:
            logger.debug(f"📋 [PICO-Parser] Framework check: current={q.framework}, expected=PICO/PECO")
            issues.append(Issue(
                id="PICO-006", 
                severity="low",
                category="PICO",
                item="Consider PICO/PECO framework for intervention studies",
                evidence={"current_framework": q.framework},
                recommendation="PICO framework is standard for intervention studies; PECO for exposure studies.",
                agent="PICO-Parser"
            ))
    
    logger.info(f"✅ [PICO-Parser] Rule-based analysis complete - identified {len(issues)} issues")
    return issues
