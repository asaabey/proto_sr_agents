#!/usr/bin/env python3
"""
Test script for the new Langraph multi-agent systematic review system.
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import (
    Manuscript,
    PICO,
    SearchDescriptor,
    FlowCounts,
    StudyRecord,
    OutcomeEffect,
)
from app.langraph_orchestrator import run_multi_agent_review


def create_test_manuscript():
    """Create a test manuscript for demonstration."""
    return Manuscript(
        manuscript_id="TEST-001",
        title="Effectiveness of Cognitive Behavioral Therapy for Depression in Adults",
        question=PICO(
            framework="PICO",
            population="Adults with major depressive disorder",
            intervention="Cognitive behavioral therapy",
            comparator="Waitlist control or treatment as usual",
            outcomes=[
                "Depression symptom reduction",
                "Quality of life improvement",
                "Treatment adherence",
            ],
        ),
        search=[
            SearchDescriptor(
                db="PubMed",
                strategy="cognitive behavioral therapy AND depression AND adult",
                dates="2010-2023",
            ),
            SearchDescriptor(
                db="Cochrane",
                strategy="cognitive behavioral therapy depression",
                dates="2010-2023",
            ),
        ],
        flow=FlowCounts(
            identified=175,
            screened=175,
            eligible=160,
            included=12,
            excluded_screening=15,
            excluded_eligibility=148,
        ),
        included_studies=[
            StudyRecord(
                study_id="Study1",
                design="RCT",
                n_total=100,
                outcomes=[
                    OutcomeEffect(
                        name="Depression symptom reduction",
                        effect_metric="SMD",
                        effect=-0.8,
                        var=0.1,
                    )
                ],
            ),
            StudyRecord(
                study_id="Study2",
                design="RCT",
                n_total=80,
                outcomes=[
                    OutcomeEffect(
                        name="Depression symptom reduction",
                        effect_metric="SMD",
                        effect=-0.6,
                        var=0.15,
                    )
                ],
            ),
        ],
    )


def main():
    """Run the multi-agent analysis demonstration."""
    print("🚀 Testing Langraph Multi-Agent Systematic Review System")
    print("=" * 60)

    # Create test manuscript
    manuscript = create_test_manuscript()
    print(f"📄 Test Manuscript: {manuscript.title}")
    print(f"🆔 ID: {manuscript.manuscript_id}")
    print(
        f"📊 Studies: {len(manuscript.included_studies) if manuscript.included_studies else 0}"
    )
    print()

    # Run multi-agent analysis
    print("🤖 Starting multi-agent analysis...")
    try:
        result = run_multi_agent_review(manuscript)

        print("✅ Analysis completed successfully!")
        print()

        # Display results
        print("📋 ANALYSIS RESULTS")
        print("-" * 30)

        print(f"🔍 Total Issues Found: {len(result.issues)}")

        # Group issues by severity
        severity_counts = {}
        for issue in result.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1

        for severity in ["high", "medium", "low"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                print(f"   {severity.upper()}: {count} issues")

        print()
        print("📊 Analysis Methods Used:")
        for method in result.analysis_metadata.analysis_methods:
            llm_info = ""
            if method.llm_model:
                llm_info = f" ({method.llm_provider}/{method.llm_model})"
            print(f"   • {method.agent}: {method.method}{llm_info}")

        print()
        print("🧠 LLM Integration:")
        print(f"   Available: {result.analysis_metadata.llm_available}")
        print(f"   Total LLM Calls: {result.analysis_metadata.total_llm_calls}")

        print()
        print("📈 Meta-Analysis Results:")
        print(f"   Generated: {len(result.meta) if result.meta else 0} results")

        print()
        print("🎉 Multi-agent analysis demonstration completed!")

    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
