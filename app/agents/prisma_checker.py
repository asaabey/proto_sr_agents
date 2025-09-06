from typing import List, Dict, Optional
import logging
from app.models.schemas import Manuscript, Issue, SearchDescriptor, FlowCounts, StudyRecord

logger = logging.getLogger("agents.prisma_checker")

def _check_search(search: List[SearchDescriptor]) -> List[Issue]:
    issues: List[Issue] = []
    if not search:
        issues.append(Issue(
            id="PRISMA-SEARCH-000",
            severity="high",
            category="PRISMA",
            item="No search strategy reported",
            recommendation="Report at least MEDLINE and one additional database; include dates and full strings.",
            agent="PRISMA-Checker"
        ))
        return issues

    have_dates = all([s.dates for s in search])
    have_db_diversity = len({s.db.lower() for s in search}) >= 2

    if not have_dates:
        issues.append(Issue(
            id="PRISMA-SEARCH-001",
            severity="medium",
            category="PRISMA",
            item="Missing date ranges for one or more databases",
            recommendation="Add explicit search date ranges for each database (e.g., inception–YYYY-MM-DD).",
            agent="PRISMA-Checker"
        ))
    if not have_db_diversity:
        issues.append(Issue(
            id="PRISMA-SEARCH-002",
            severity="medium",
            category="PRISMA",
            item="Only one database reported",
            recommendation="Search multiple databases (e.g., MEDLINE + Embase/CENTRAL) and justify any limits.",
            agent="PRISMA-Checker"
        ))
    return issues

def _check_flow(flow: FlowCounts) -> List[Issue]:
    issues: List[Issue] = []
    if not flow:
        issues.append(Issue(
            id="PRISMA-FLOW-000",
            severity="high",
            category="PRISMA",
            item="No PRISMA flow provided",
            recommendation="Provide identification → screening → eligibility → included counts with exclusion reasons.",
            agent="PRISMA-Checker"
        ))
        return issues

    # Simple arithmetic consistency checks
    nums = {k: getattr(flow, k) for k in ["identified","deduplicated","screened","fulltext","included"]}
    if any(v is None for v in nums.values()):
        issues.append(Issue(
            id="PRISMA-FLOW-001",
            severity="medium",
            category="PRISMA",
            item="Incomplete PRISMA counts",
            evidence={"present": nums},
            recommendation="Report all key counts; ensure totals are traceable.",
            agent="PRISMA-Checker"
        ))
    if flow.identified is not None and flow.deduplicated is not None:
        if flow.deduplicated > flow.identified:
            issues.append(Issue(
                id="PRISMA-FLOW-002",
                severity="high",
                category="PRISMA",
                item="Deduplicated exceeds identified",
                evidence={"identified": flow.identified, "deduplicated": flow.deduplicated},
                recommendation="Verify counts; deduplicated should be ≤ identified.",
                agent="PRISMA-Checker"
            ))
    return issues

def _check_protocol_registration(manuscript: Manuscript) -> List[Issue]:
    """Check for protocol registration and adherence"""
    issues = []
    
    if not manuscript.protocol:
        issues.append(Issue(
            id="PRISMA-PROTOCOL-001",
            severity="high",
            category="PRISMA", 
            item="No protocol registration reported",
            recommendation="Register protocol in PROSPERO, OSF, or similar registry before starting review.",
            agent="PRISMA-Checker"
        ))
    else:
        # Check for PROSPERO ID format
        prospero_id = manuscript.protocol.get("prospero_id", "")
        if prospero_id and not prospero_id.startswith("CRD"):
            issues.append(Issue(
                id="PRISMA-PROTOCOL-002",
                severity="medium",
                category="PRISMA",
                item="Invalid PROSPERO ID format",
                evidence={"provided_id": prospero_id},
                recommendation="PROSPERO IDs should start with 'CRD' followed by numbers.",
                agent="PRISMA-Checker"
            ))
    
    return issues

def _check_study_selection(manuscript: Manuscript) -> List[Issue]:
    """Validate study selection and extraction reporting"""
    issues = []
    
    # Check for study design reporting
    studies_without_design = [s for s in manuscript.included_studies if not s.design]
    if studies_without_design:
        issues.append(Issue(
            id="PRISMA-STUDIES-001",
            severity="medium",
            category="PRISMA",
            item="Some studies missing design specification",
            evidence={"studies_missing_design": [s.study_id for s in studies_without_design]},
            recommendation="Report study design for all included studies (RCT, cohort, case-control, etc.).",
            agent="PRISMA-Checker"
        ))
    
    # Check for sample size reporting
    studies_without_n = [s for s in manuscript.included_studies if not s.n_total]
    if studies_without_n:
        issues.append(Issue(
            id="PRISMA-STUDIES-002", 
            severity="medium",
            category="PRISMA",
            item="Some studies missing total sample size",
            evidence={"studies_missing_n": [s.study_id for s in studies_without_n]},
            recommendation="Report total sample size for all included studies.",
            agent="PRISMA-Checker"
        ))
    
    return issues

def _check_search_comprehensiveness(search: List[SearchDescriptor]) -> List[Issue]:
    """Enhanced search strategy validation"""
    issues = []
    
    # Check for core databases
    db_names = {s.db.lower() for s in search}
    core_dbs = {"medline", "pubmed", "embase"}
    
    if not any(core_db in db_names for core_db in core_dbs):
        issues.append(Issue(
            id="PRISMA-SEARCH-003",
            severity="high", 
            category="PRISMA",
            item="Missing core medical databases",
            evidence={"searched_dbs": list(db_names)},
            recommendation="Include MEDLINE/PubMed and at least one other major database (Embase, CENTRAL).",
            agent="PRISMA-Checker"
        ))
    
    # Check for search strategy details
    strategies_missing = [s for s in search if not s.strategy or len(s.strategy.strip()) < 10]
    if strategies_missing:
        issues.append(Issue(
            id="PRISMA-SEARCH-004",
            severity="medium",
            category="PRISMA", 
            item="Insufficient search strategy detail",
            evidence={"databases_missing_strategy": [s.db for s in strategies_missing]},
            recommendation="Provide full search strings for each database, including MeSH terms and keywords.",
            agent="PRISMA-Checker"
        ))
    
    return issues

def run(manuscript: Manuscript) -> List[Issue]:
    logger.info("📊 [PRISMA-Checker] Starting PRISMA 2020 compliance validation...")
    issues: List[Issue] = []
    
    # Original checks
    logger.debug("🔍 [PRISMA-Checker] Checking search strategy reporting...")
    search_issues = _check_search(manuscript.search)
    issues += search_issues
    if search_issues:
        logger.warning(f"⚠️ [PRISMA-Checker] Found {len(search_issues)} search strategy issues")
    else:
        logger.info("✓ [PRISMA-Checker] Search strategy validation passed")
    
    logger.debug("📈 [PRISMA-Checker] Checking PRISMA flow diagram...")
    flow_issues = _check_flow(manuscript.flow)
    issues += flow_issues
    if flow_issues:
        logger.warning(f"⚠️ [PRISMA-Checker] Found {len(flow_issues)} flow diagram issues")
    else:
        logger.info("✓ [PRISMA-Checker] Flow diagram validation passed")
    
    # Enhanced checks
    logger.debug("📋 [PRISMA-Checker] Checking protocol registration...")
    protocol_issues = _check_protocol_registration(manuscript)
    issues += protocol_issues
    if protocol_issues:
        logger.warning(f"⚠️ [PRISMA-Checker] Found {len(protocol_issues)} protocol registration issues")
    
    logger.debug("🎯 [PRISMA-Checker] Checking study selection reporting...")
    selection_issues = _check_study_selection(manuscript)
    issues += selection_issues
    if selection_issues:
        logger.warning(f"⚠️ [PRISMA-Checker] Found {len(selection_issues)} study selection issues")
    
    logger.debug("🔍 [PRISMA-Checker] Checking search comprehensiveness...")
    comprehensiveness_issues = _check_search_comprehensiveness(manuscript.search)
    issues += comprehensiveness_issues
    if comprehensiveness_issues:
        logger.warning(f"⚠️ [PRISMA-Checker] Found {len(comprehensiveness_issues)} search comprehensiveness issues")
    
    logger.info(f"✅ [PRISMA-Checker] PRISMA validation complete - identified {len(issues)} issues")
    return issues
