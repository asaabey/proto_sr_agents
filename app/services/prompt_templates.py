"""
Structured prompt templates for LLM-enhanced systematic review analysis.

Contains specialized prompts for PICO extraction, PRISMA validation,
risk of bias assessment, and other systematic review tasks.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    system_prompt: str
    user_template: str

    def format(self, **kwargs) -> str:
        """Format the user template with provided arguments."""
        return self.user_template.format(**kwargs)


class SystemReviewPrompts:
    """Collection of prompt templates for systematic review analysis."""

    PICO_EXTRACTION = PromptTemplate(
        system_prompt="""You are an expert systematic review methodologist. Your task is to extract PICO elements from manuscript text with high precision. Focus on identifying:
- Population: Specific demographics, conditions, settings
- Intervention: Treatments, exposures, diagnostic tests
- Comparator: Control conditions, alternative treatments
- Outcomes: Primary and secondary endpoints with timeframes

Be conservative - only extract elements that are explicitly stated. Return structured JSON only.""",
        user_template="""Extract PICO elements from this systematic review text:

{manuscript_text}

Return a JSON object with this exact structure:
{{
  "population": "specific population description or null",
  "intervention": "intervention description or null", 
  "comparator": "comparator description or null",
  "outcomes": ["outcome1", "outcome2"] or [],
  "confidence": "high|medium|low",
  "extraction_notes": "brief notes about extraction quality"
}}""",
    )

    PRISMA_ASSESSMENT = PromptTemplate(
        system_prompt="""You are a systematic review quality assessor specializing in PRISMA 2020 guidelines. Evaluate manuscripts for reporting completeness and methodological rigor. Focus on:
- Search strategy comprehensiveness
- Study selection transparency  
- Risk of bias assessment
- Results presentation clarity

Provide specific, actionable feedback with evidence citations.""",
        user_template="""Assess this systematic review for PRISMA 2020 compliance:

Manuscript Context:
{manuscript_context}

Search Strategies: {search_count}
Included Studies: {study_count}

Evaluate for:
1. Completeness of reporting
2. Methodological soundness  
3. Transparency of methods
4. Adherence to PRISMA guidelines

Return JSON with:
{{
  "compliance_score": 0-100,
  "issues": [
    {{
      "item": "PRISMA item number/description",
      "severity": "low|medium|high",
      "description": "specific issue found",
      "recommendation": "actionable improvement suggestion"
    }}
  ],
  "recommendations": ["list of specific improvements"],
  "overall_assessment": "brief summary"
}}""",
    )

    ROB_ASSESSMENT = PromptTemplate(
        system_prompt="""You are a risk of bias expert using RoB 2 (for RCTs) and ROBINS-I (for non-randomized studies). Assess study quality across all domains with careful attention to:
- Randomization process and allocation concealment
- Deviations from intended interventions
- Missing outcome data and measurement issues
- Selective reporting concerns

Provide domain-specific judgments with clear justifications.""",
        user_template="""Assess risk of bias for this study:

Study Design: {study_design}
Study Description: {study_text}

For {assessment_tool} (RoB 2 or ROBINS-I), evaluate:
{domains}

Return JSON assessment:
{{
  "overall_rob": "low|some_concerns|high",
  "domains": {{
    "domain1": {{
      "judgment": "low|some_concerns|high",
      "rationale": "specific justification",
      "supporting_info": "evidence from study text"
    }}
  }},
  "summary": "overall risk of bias summary"
}}""",
    )

    GRADE_EVALUATION = PromptTemplate(
        system_prompt="""You are a GRADE methodology expert evaluating certainty of evidence. Assess evidence quality across five domains:
1. Risk of bias
2. Inconsistency  
3. Indirectness
4. Imprecision
5. Publication bias

Consider upgrade factors for observational studies. Provide transparent, evidence-based certainty ratings.""",
        user_template="""Evaluate GRADE certainty for this outcome:

Outcome: {outcome_name}
Study Designs: {study_designs}
Effect Estimates: {effect_data}
Meta-analysis Results: {meta_results}

Additional Context: {additional_context}

Assess GRADE domains and provide:
{{
  "certainty": "high|moderate|low|very_low",
  "starting_level": "high|low",
  "downgrades": [
    {{
      "domain": "risk_of_bias|inconsistency|indirectness|imprecision|publication_bias",
      "levels": 1 or 2,
      "rationale": "specific justification"
    }}
  ],
  "upgrades": [
    {{
      "factor": "large_effect|dose_response|confounding",
      "levels": 1 or 2,
      "rationale": "justification"
    }}
  ],
  "summary_statement": "GRADE summary for this outcome"
}}""",
    )

    SEARCH_STRATEGY_REVIEW = PromptTemplate(
        system_prompt="""You are a systematic review information specialist. Evaluate search strategies for comprehensiveness, appropriateness, and reproducibility. Consider:
- Database selection and coverage
- Search term comprehensiveness  
- Boolean logic and syntax
- Date restrictions and filters
- Grey literature inclusion

Provide specific suggestions for improvement.""",
        user_template="""Review this search strategy:

Research Question: {research_question}
Databases Searched: {databases}
Search Terms: {search_terms}
Filters Applied: {filters}
Date Range: {date_range}

Evaluate for:
1. Database appropriateness for topic
2. Search term comprehensiveness
3. Boolean logic effectiveness
4. Reproducibility
5. Bias minimization

Return assessment:
{{
  "completeness_score": 0-100,
  "database_adequacy": "excellent|good|adequate|inadequate",
  "search_term_coverage": "comprehensive|adequate|limited",
  "recommendations": [
    {{
      "category": "databases|terms|filters|methodology",
      "suggestion": "specific improvement",
      "rationale": "why this would improve the search"
    }}
  ],
  "missing_elements": ["list of important missing components"],
  "overall_assessment": "summary evaluation"
}}""",
    )

    META_ANALYSIS_INTERPRETATION = PromptTemplate(
        system_prompt="""You are a biostatistician specializing in systematic reviews and meta-analysis. Interpret statistical results in clinical context, assess heterogeneity, and provide clear explanations. Consider:
- Effect size clinical significance
- Statistical vs clinical significance
- Heterogeneity sources and implications
- Confidence interval interpretation

Translate statistical findings into actionable clinical insights.""",
        user_template="""Interpret these meta-analysis results:

{results_summary}

Provide interpretation:
{{
  "clinical_significance": "high|moderate|low|negligible",
  "statistical_significance": "significant|not_significant",
  "heterogeneity_assessment": {{
    "level": "low|moderate|substantial|considerable",
    "likely_sources": ["list of potential sources"],
    "impact_on_conclusions": "how heterogeneity affects interpretation"
  }},
  "clinical_interpretation": "plain language explanation for clinicians",
  "certainty_factors": "factors affecting confidence in results",
  "recommendations": "clinical and research implications"
}}""",
    )


# Convenience function to get specific prompts
def get_prompt(prompt_name: str) -> PromptTemplate:
    """Get a specific prompt template by name."""
    prompts_map = {
        "pico_extraction": SystemReviewPrompts.PICO_EXTRACTION,
        "prisma_assessment": SystemReviewPrompts.PRISMA_ASSESSMENT,
        "rob_assessment": SystemReviewPrompts.ROB_ASSESSMENT,
        "grade_evaluation": SystemReviewPrompts.GRADE_EVALUATION,
        "search_review": SystemReviewPrompts.SEARCH_STRATEGY_REVIEW,
        "statistical_interpretation": SystemReviewPrompts.META_ANALYSIS_INTERPRETATION,
        "meta_analysis_interpretation": SystemReviewPrompts.META_ANALYSIS_INTERPRETATION,
    }

    if prompt_name not in prompts_map:
        available = ", ".join(prompts_map.keys())
        raise ValueError(f"Unknown prompt: {prompt_name}. Available: {available}")

    return prompts_map[prompt_name]
