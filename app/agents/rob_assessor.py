"""
Risk of Bias (RoB) Assessment Agent using LLM integration.

Implements RoB 2 for randomized trials and ROBINS-I for
non-randomized studies using structured LLM prompts.
"""

from typing import List, Dict, Optional, Any
import json
import logging
from app.models.schemas import Manuscript, StudyRecord, Issue
from app.services.llm_client import get_llm_client
from app.services.prompt_templates import get_prompt

logger = logging.getLogger("agents.rob_assessor")


class RoBAssessor:
    """Risk of Bias assessment agent with LLM integration."""

    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        self.llm_client = get_llm_client() if use_llm else None

        # RoB 2 domains for randomized trials
        self.rob2_domains = {
            "randomization": "Randomization process",
            "deviations": "Deviations from intended interventions",
            "missing_data": "Missing outcome data",
            "outcome_measurement": "Measurement of the outcome",
            "selective_reporting": "Selection of the reported result",
        }

        # ROBINS-I domains for non-randomized studies
        self.robins_domains = {
            "confounding": "Confounding",
            "selection": "Selection of participants",
            "intervention_classification": "Classification of interventions",
            "deviations": "Deviations from intended interventions",
            "missing_data": "Missing data",
            "outcome_measurement": "Measurement of outcomes",
            "selective_reporting": "Selection of the reported result",
        }

    def run(self, manuscript: Manuscript) -> List[Issue]:
        """Assess risk of bias for all included studies."""
        logger.info("⚖️ [RoB-Assessor] Starting Risk of Bias assessment...")
        logger.debug(
            f"🔧 [RoB-Assessor] Configuration - LLM: {self.use_llm}, Studies: {len(manuscript.included_studies)}"
        )

        issues = []

        if not manuscript.included_studies:
            logger.warning(
                "❌ [RoB-Assessor] No included studies found for RoB assessment"
            )
            return issues

        logger.info(
            f"📊 [RoB-Assessor] Assessing {len(manuscript.included_studies)} studies..."
        )

        for i, study in enumerate(manuscript.included_studies, 1):
            logger.info(
                f"🔍 [RoB-Assessor] Assessing study {i}/{len(manuscript.included_studies)}: {study.study_id}"
            )
            logger.debug(f"   Study design: {study.design or 'Not specified'}")
            logger.debug(f"   Sample size: {study.n_total or 'Not specified'}")

            if self.use_llm and self.llm_client:
                # LLM-based assessment
                logger.info(
                    f"🤖 [RoB-Assessor] Using LLM for RoB assessment of {study.study_id}"
                )
                rob_issues = self._assess_study_with_llm(study)
            else:
                # Rule-based fallback assessment
                logger.info(
                    f"📋 [RoB-Assessor] Using rule-based assessment for {study.study_id}"
                )
                rob_issues = self._assess_study_rule_based(study)

            issues.extend(rob_issues)
            logger.info(
                f"✅ [RoB-Assessor] Study {study.study_id} assessment complete - found {len(rob_issues)} issues"
            )

        # Overall manuscript-level RoB issues
        logger.info("📋 [RoB-Assessor] Assessing overall manuscript RoB reporting...")
        overall_issues = self._assess_overall_rob_reporting(manuscript)
        issues.extend(overall_issues)
        logger.info(
            f"📊 [RoB-Assessor] Overall reporting assessment complete - found {len(overall_issues)} issues"
        )

        logger.info(
            f"✅ [RoB-Assessor] Risk of Bias assessment complete - identified {len(issues)} total issues"
        )
        return issues

    def _assess_study_with_llm(self, study: StudyRecord) -> List[Issue]:
        """Assess individual study using LLM with structured prompts."""
        issues = []

        try:
            # Determine assessment tool based on study design
            is_rct = study.design and "rct" in study.design.lower()
            assessment_tool = "RoB 2" if is_rct else "ROBINS-I"
            domains = self.rob2_domains if is_rct else self.robins_domains

            logger.debug(
                f"🔍 [RoB-Assessor] {study.study_id}: Detected {'RCT' if is_rct else 'non-RCT'}, using {assessment_tool}"
            )
            logger.debug(
                f"🔍 [RoB-Assessor] {study.study_id}: Will assess {len(domains)} bias domains"
            )

            # Prepare study context
            study_text = f"""
            Study ID: {study.study_id}
            Design: {study.design or 'Not specified'}
            Sample Size: {study.n_total or 'Not specified'}
            Outcomes: {len(study.outcomes)} outcomes reported
            """

            logger.debug(
                f"📝 [RoB-Assessor] {study.study_id}: Prepared study context for LLM"
            )

            # Get RoB assessment prompt
            rob_prompt = get_prompt("rob_assessment")

            # Format prompt with study details
            formatted_prompt = rob_prompt.format(
                study_design=study.design or "Not specified",
                study_text=study_text,
                assessment_tool=assessment_tool,
                domains="\n".join(
                    [f"- {name}: {desc}" for name, desc in domains.items()]
                ),
            )

            logger.debug(
                f"📝 [RoB-Assessor] {study.study_id}: Formatted prompt length: {len(formatted_prompt)} characters"
            )

            # Get LLM assessment
            logger.info(
                f"🔄 [RoB-Assessor] {study.study_id}: Requesting LLM assessment..."
            )
            response = self.llm_client.generate_completion_sync(
                prompt=formatted_prompt, system_prompt=rob_prompt.system_prompt
            )

            logger.debug(
                f"📨 [RoB-Assessor] {study.study_id}: LLM response length: {len(response)} characters"
            )

            # Parse LLM response
            logger.debug(
                f"🔍 [RoB-Assessor] {study.study_id}: Parsing LLM RoB assessment..."
            )
            rob_assessment = self._parse_rob_response(response, study.study_id)

            overall_rob = rob_assessment.get("overall_rob", "unclear")
            logger.info(
                f"📊 [RoB-Assessor] {study.study_id}: LLM assessed overall risk as '{overall_rob}'"
            )

            # Convert to issues
            logger.debug(
                f"🔄 [RoB-Assessor] {study.study_id}: Converting assessment to issues..."
            )
            converted_issues = self._convert_rob_to_issues(
                rob_assessment, study.study_id
            )
            issues.extend(converted_issues)

            logger.info(
                f"✅ [RoB-Assessor] {study.study_id}: LLM assessment complete - generated {len(converted_issues)} issues"
            )

        except Exception as e:
            # Fallback to rule-based if LLM fails
            logger.error(
                f"💥 [RoB-Assessor] {study.study_id}: LLM assessment failed: {str(e)}"
            )
            logger.info(
                f"🔄 [RoB-Assessor] {study.study_id}: Falling back to rule-based assessment..."
            )

            issues.append(
                Issue(
                    id=f"ROB-LLM-ERROR-{study.study_id}",
                    severity="medium",
                    category="OTHER",
                    item=f"LLM risk of bias assessment failed for {study.study_id}",
                    evidence={"error": str(e)},
                    recommendation="Perform manual risk of bias assessment for this study.",
                    agent="RoB-Assessor",
                )
            )

            fallback_issues = self._assess_study_rule_based(study)
            issues.extend(fallback_issues)
            logger.info(
                f"📋 [RoB-Assessor] {study.study_id}: Rule-based fallback complete - generated {len(fallback_issues)} issues"
            )

        return issues

    def _assess_study_rule_based(self, study: StudyRecord) -> List[Issue]:
        """Rule-based fallback risk of bias assessment."""
        logger.debug(
            f"📋 [RoB-Assessor] {study.study_id}: Starting rule-based assessment..."
        )
        issues = []

        # Check for missing design specification
        if not study.design:
            logger.warning(
                f"⚠️ [RoB-Assessor] {study.study_id}: Missing study design specification"
            )
            issues.append(
                Issue(
                    id=f"ROB-DESIGN-001-{study.study_id}",
                    severity="high",
                    category="DATA",
                    item=f"Study design not specified for {study.study_id}",
                    evidence={"study_id": study.study_id},
                    recommendation="Specify study design (RCT, cohort, case-control, etc.) for risk of bias assessment.",
                    agent="RoB-Assessor",
                )
            )
        else:
            logger.debug(
                f"✅ [RoB-Assessor] {study.study_id}: Study design specified: {study.design}"
            )

        # Check for missing sample size
        if not study.n_total:
            logger.warning(f"⚠️ [RoB-Assessor] {study.study_id}: Missing sample size")
            issues.append(
                Issue(
                    id=f"ROB-SAMPLE-001-{study.study_id}",
                    severity="medium",
                    category="DATA",
                    item=f"Sample size not reported for {study.study_id}",
                    evidence={"study_id": study.study_id},
                    recommendation="Report total sample size for precision assessment.",
                    agent="RoB-Assessor",
                )
            )
        else:
            logger.debug(
                f"✅ [RoB-Assessor] {study.study_id}: Sample size reported: {study.n_total}"
            )

        # Check for outcome reporting
        if not study.outcomes:
            logger.warning(f"⚠️ [RoB-Assessor] {study.study_id}: No outcomes reported")
            issues.append(
                Issue(
                    id=f"ROB-OUTCOMES-001-{study.study_id}",
                    severity="high",
                    category="DATA",
                    item=f"No outcomes reported for {study.study_id}",
                    evidence={"study_id": study.study_id},
                    recommendation="Include outcome data with effect sizes and confidence intervals.",
                    agent="RoB-Assessor",
                )
            )
        else:
            logger.debug(
                f"✅ [RoB-Assessor] {study.study_id}: {len(study.outcomes)} outcomes reported"
            )

        logger.debug(
            f"📋 [RoB-Assessor] {study.study_id}: Rule-based assessment complete - found {len(issues)} issues"
        )
        return issues

    def _parse_rob_response(self, response: str, study_id: str) -> Dict[str, Any]:
        """Parse LLM response into structured risk of bias assessment."""
        try:
            # Try to parse JSON response
            assessment = json.loads(response)
            return assessment
        except json.JSONDecodeError:
            # Fallback parsing if JSON is malformed
            return {
                "overall_rob": "unclear",
                "domains": {},
                "summary": f"Could not parse LLM assessment for {study_id}",
                "raw_response": response,
            }

    def _convert_rob_to_issues(
        self, assessment: Dict[str, Any], study_id: str
    ) -> List[Issue]:
        """Convert RoB assessment to Issue objects."""
        issues = []

        overall_rob = assessment.get("overall_rob", "unclear")

        # Overall risk of bias issue
        if overall_rob in ["high", "some_concerns"]:
            severity = "high" if overall_rob == "high" else "medium"
            issues.append(
                Issue(
                    id=f"ROB-OVERALL-001-{study_id}",
                    severity=severity,
                    category="DATA",
                    item=f"Risk of bias concerns for {study_id}",
                    evidence={
                        "overall_judgment": overall_rob,
                        "summary": assessment.get("summary", ""),
                        "domains": assessment.get("domains", {}),
                    },
                    recommendation=f"Consider impact of {overall_rob} risk of bias on results interpretation.",
                    agent="RoB-Assessor",
                )
            )

        # Domain-specific issues
        domains = assessment.get("domains", {})
        for domain, domain_assessment in domains.items():
            if isinstance(domain_assessment, dict):
                judgment = domain_assessment.get("judgment", "unclear")
                if judgment in ["high", "some_concerns"]:
                    severity = "high" if judgment == "high" else "medium"
                    issues.append(
                        Issue(
                            id=f"ROB-{domain.upper()}-001-{study_id}",
                            severity=severity,
                            category="DATA",
                            item=f"{domain.replace('_', ' ').title()} bias concerns for {study_id}",
                            evidence={
                                "domain": domain,
                                "judgment": judgment,
                                "rationale": domain_assessment.get("rationale", ""),
                                "supporting_info": domain_assessment.get(
                                    "supporting_info", ""
                                ),
                            },
                            recommendation=domain_assessment.get(
                                "rationale", "Review methodology for this bias domain."
                            ),
                            agent="RoB-Assessor",
                        )
                    )

        return issues

    def _assess_overall_rob_reporting(self, manuscript: Manuscript) -> List[Issue]:
        """Assess manuscript-level risk of bias reporting."""
        issues = []

        # Check if RoB assessment is mentioned in methodology
        # This would require full manuscript text analysis

        # For now, check basic completeness
        total_studies = len(manuscript.included_studies)
        if total_studies == 0:
            return issues

        studies_with_design = sum(1 for s in manuscript.included_studies if s.design)
        if studies_with_design < total_studies:
            issues.append(
                Issue(
                    id="ROB-REPORTING-001",
                    severity="high",
                    category="PRISMA",
                    item="Incomplete study design reporting affects risk of bias assessment",
                    evidence={
                        "total_studies": total_studies,
                        "studies_with_design": studies_with_design,
                        "missing_design": total_studies - studies_with_design,
                    },
                    recommendation="Report study design for all included studies to enable proper risk of bias assessment.",
                    agent="RoB-Assessor",
                )
            )

        return issues


# Convenience function for direct use
def assess_risk_of_bias(manuscript: Manuscript, use_llm: bool = True) -> List[Issue]:
    """Assess risk of bias for all studies in manuscript."""
    assessor = RoBAssessor(use_llm=use_llm)
    return assessor.run(manuscript)
