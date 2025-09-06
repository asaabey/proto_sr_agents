"""
Enhanced PRISMA Checker with LLM integration.

Combines rule-based PRISMA validation with LLM-powered analysis
for improved compliance assessment and recommendations.
"""

from typing import List, Dict, Optional
import logging
from app.models.schemas import Manuscript, Issue, SearchDescriptor, FlowCounts, StudyRecord
from app.services.llm_client import get_llm_client
from app.services.prompt_templates import get_prompt

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


class EnhancedPRISMAChecker:
    """PRISMA checker with LLM enhancement capabilities."""

    def __init__(self, use_llm: bool = True, fallback_to_rules: bool = True):
        self.use_llm = use_llm
        self.fallback_to_rules = fallback_to_rules
        self.llm_client = get_llm_client() if use_llm else None

    def run(self, manuscript: Manuscript) -> List[Issue]:
        """Enhanced PRISMA validation with LLM integration."""
        logger.info("📊🤖 [Enhanced-PRISMA-Checker] Starting enhanced PRISMA validation with LLM integration...")
        logger.debug(f"🔧 [Enhanced-PRISMA-Checker] Configuration - LLM: {self.use_llm}, Fallback: {self.fallback_to_rules}")

        issues = []

        # Always run rule-based checks first
        logger.info("📋 [Enhanced-PRISMA-Checker] Running rule-based PRISMA validation...")
        rule_based_issues = self._run_rule_based_checks(manuscript)
        issues.extend(rule_based_issues)
        logger.info(f"📊 [Enhanced-PRISMA-Checker] Rule-based validation found {len(rule_based_issues)} issues")

        # Add LLM-enhanced analysis if available
        if self.use_llm and self.llm_client:
            logger.info("🧠 [Enhanced-PRISMA-Checker] Starting LLM-enhanced PRISMA analysis...")
            try:
                llm_issues = self._llm_enhanced_analysis(manuscript)
                issues.extend(llm_issues)
                logger.info(f"📊 [Enhanced-PRISMA-Checker] LLM analysis found {len(llm_issues)} additional issues")
            except Exception as e:
                logger.error(f"💥 [Enhanced-PRISMA-Checker] LLM analysis failed: {e}")
                issues.append(Issue(
                    id="PRISMA-LLM-ERROR-001",
                    severity="low",
                    category="OTHER",
                    item="LLM PRISMA analysis failed, using rule-based results only",
                    evidence={"error": str(e)},
                    recommendation="Consider manual PRISMA compliance review.",
                    agent="Enhanced-PRISMA-Checker"
                ))

        logger.info(f"✅ [Enhanced-PRISMA-Checker] Enhanced PRISMA validation complete - identified {len(issues)} total issues")
        return issues

    def _run_rule_based_checks(self, manuscript: Manuscript) -> List[Issue]:
        """Run all original rule-based PRISMA checks."""
        issues = []

        # Original checks
        search_issues = _check_search(manuscript.search)
        issues.extend(search_issues)

        flow_issues = _check_flow(manuscript.flow)
        issues.extend(flow_issues)

        # Enhanced checks
        protocol_issues = _check_protocol_registration(manuscript)
        issues.extend(protocol_issues)

        selection_issues = _check_study_selection(manuscript)
        issues.extend(selection_issues)

        comprehensiveness_issues = _check_search_comprehensiveness(manuscript.search)
        issues.extend(comprehensiveness_issues)

        return issues

    def _llm_enhanced_analysis(self, manuscript: Manuscript) -> List[Issue]:
        """Use LLM for advanced PRISMA compliance assessment."""
        logger.info("🧠 [Enhanced-PRISMA-Checker] Starting LLM-enhanced PRISMA compliance assessment...")
        issues = []

        try:
            # Prepare manuscript context for LLM
            manuscript_context = self._prepare_manuscript_context(manuscript)
            logger.debug(f"📄 [Enhanced-PRISMA-Checker] Prepared manuscript context: {len(manuscript_context)} characters")

            # Get PRISMA assessment prompt
            prisma_prompt = get_prompt("prisma_assessment")

            formatted_prompt = prisma_prompt.format(
                manuscript_context=manuscript_context,
                search_count=len(manuscript.search),
                study_count=len(manuscript.included_studies)
            )

            logger.info("🔄 [Enhanced-PRISMA-Checker] Requesting LLM PRISMA assessment...")
            response = self.llm_client.generate_completion_sync(
                prompt=formatted_prompt,
                system_prompt=prisma_prompt.system_prompt
            )

            # Parse and process LLM response
            logger.debug("🔍 [Enhanced-PRISMA-Checker] Parsing LLM PRISMA assessment...")
            assessment_issues = self._process_llm_assessment(response)
            issues.extend(assessment_issues)

            logger.info(f"✅ [Enhanced-PRISMA-Checker] LLM assessment complete - identified {len(assessment_issues)} issues")

        except Exception as e:
            logger.error(f"💥 [Enhanced-PRISMA-Checker] LLM PRISMA assessment failed: {e}")

        return issues

    def _prepare_manuscript_context(self, manuscript: Manuscript) -> str:
        """Prepare manuscript information for LLM analysis."""
        context_parts = []

        if manuscript.title:
            context_parts.append(f"Title: {manuscript.title}")

        if manuscript.question:
            pico_text = f"""
            Population: {manuscript.question.population or 'Not specified'}
            Intervention: {manuscript.question.intervention or 'Not specified'}
            Comparator: {manuscript.question.comparator or 'Not specified'}
            Outcomes: {', '.join(manuscript.question.outcomes) if manuscript.question.outcomes else 'Not specified'}
            """
            context_parts.append(f"Research Question (PICO): {pico_text}")

        # Search information
        if manuscript.search:
            search_info = []
            for search in manuscript.search:
                search_desc = f"Database: {search.db}"
                if search.strategy:
                    search_desc += f", Strategy: {search.strategy[:100]}..."
                if search.dates:
                    search_desc += f", Dates: {search.dates}"
                search_info.append(search_desc)
            context_parts.append(f"Search Strategy: {'; '.join(search_info)}")

        # Flow information
        if manuscript.flow:
            flow_text = f"""
            Identified: {manuscript.flow.identified or 'Not reported'}
            Deduplicated: {manuscript.flow.deduplicated or 'Not reported'}
            Screened: {manuscript.flow.screened or 'Not reported'}
            Full-text: {manuscript.flow.fulltext or 'Not reported'}
            Included: {manuscript.flow.included or 'Not reported'}
            """
            context_parts.append(f"Study Flow: {flow_text}")

        # Study information
        if manuscript.included_studies:
            study_info = []
            for study in manuscript.included_studies:
                study_desc = f"Study: {study.study_id}"
                if study.design:
                    study_desc += f", Design: {study.design}"
                if study.n_total:
                    study_desc += f", N: {study.n_total}"
                study_info.append(study_desc)
            context_parts.append(f"Included Studies: {'; '.join(study_info)}")

        return "\n\n".join(context_parts)

    def _process_llm_assessment(self, response: str) -> List[Issue]:
        """Process LLM PRISMA assessment response."""
        issues = []

        try:
            import json
            assessment = json.loads(response)

            # Process overall compliance score
            compliance_score = assessment.get("compliance_score", 100)
            if compliance_score < 80:
                severity = "high" if compliance_score < 60 else "medium"
                issues.append(Issue(
                    id="PRISMA-COMPLIANCE-001",
                    severity=severity,
                    category="PRISMA",
                    item=f"PRISMA compliance score: {compliance_score}/100",
                    evidence=assessment,
                    recommendation="; ".join(assessment.get("recommendations", [])),
                    agent="Enhanced-PRISMA-Checker"
                ))

            # Process specific issues
            specific_issues = assessment.get("issues", [])
            for i, issue_data in enumerate(specific_issues):
                severity = issue_data.get("severity", "medium")
                issues.append(Issue(
                    id=f"PRISMA-LLM-{i+1:03d}",
                    severity=severity,
                    category="PRISMA",
                    item=issue_data.get("item", "PRISMA compliance issue"),
                    evidence=issue_data,
                    recommendation=issue_data.get("recommendation", "Review PRISMA guidelines"),
                    agent="Enhanced-PRISMA-Checker"
                ))

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"� [Enhanced-PRISMA-Checker] Failed to parse LLM assessment: {e}")
            # Create a generic issue if parsing fails
            issues.append(Issue(
                id="PRISMA-LLM-PARSE-001",
                severity="low",
                category="OTHER",
                item="LLM PRISMA assessment completed but results could not be parsed",
                evidence={"raw_response": response[:500]},
                recommendation="Manual PRISMA compliance review recommended.",
                agent="Enhanced-PRISMA-Checker"
            ))

        return issues


# Enhanced wrapper function
def run_enhanced_prisma_analysis(manuscript: Manuscript, use_llm: bool = True) -> List[Issue]:
    """Run enhanced PRISMA analysis with LLM integration."""
    checker = EnhancedPRISMAChecker(use_llm=use_llm)
    return checker.run(manuscript)


# Original function for backward compatibility
def run(manuscript: Manuscript) -> List[Issue]:
    """Original PRISMA checker function - now uses enhanced version with LLM if available."""
    return run_enhanced_prisma_analysis(manuscript, use_llm=True)
