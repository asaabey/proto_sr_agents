from typing import List, Optional
import logging
from app.models.schemas import Manuscript, ReviewResult, Issue, MetaResult, AnalysisMethod, AnalysisMetadata
from app.agents import pico_parser, prisma_checker, meta_analysis

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("orchestrator")

# Import enhanced agents
try:
    from app.agents.pico_parser_enhanced import EnhancedPICOParser
    from app.agents.rob_assessor import RoBAssessor
    from app.services.llm_config import get_llm_environment
    LLM_AGENTS_AVAILABLE = True
except ImportError as e:
    print(f"LLM agents not available: {e}")
    LLM_AGENTS_AVAILABLE = False

def get_llm_config() -> Optional[dict]:
    """Get current LLM configuration for metadata tracking."""
    try:
        if LLM_AGENTS_AVAILABLE:
            env = get_llm_environment()
            return {
                "provider": env.settings.default_provider,
                "model": env.settings.default_model,
                "available": env.validate_setup()["configured"]
            }
    except Exception:
        pass
    return None

def simple_review(manuscript: Manuscript) -> ReviewResult:
    """
    Enhanced review workflow with LLM-powered agents when available.
    Falls back to rule-based analysis if LLM integration fails.
    """
    logger.info(f"🔍 Starting systematic review analysis for manuscript: {manuscript.manuscript_id}")
    logger.info(f"📄 Title: {manuscript.title[:100] if manuscript.title else 'No title'}...")
    
    issues: List[Issue] = []
    analysis_methods: List[AnalysisMethod] = []
    llm_config = get_llm_config()
    
    # Log LLM configuration status
    if llm_config:
        logger.info(f"⚙️ LLM Config - Available: {llm_config.get('available', False)}, Provider: {llm_config.get('provider', 'None')}, Model: {llm_config.get('model', 'None')}")
    else:
        logger.info("❌ LLM Config - Not available")
    
    # PICO Analysis - Enhanced with LLM when available
    logger.info("🎯 Starting PICO Analysis...")
    if LLM_AGENTS_AVAILABLE:
        try:
            logger.info("🤖 Attempting LLM-enhanced PICO parsing...")
            enhanced_pico = EnhancedPICOParser(use_llm=True, fallback_to_rules=True)
            pico_issues = enhanced_pico.run(manuscript)
            issues += pico_issues
            logger.info(f"✅ LLM-enhanced PICO parsing completed - found {len(pico_issues)} issues")
            analysis_methods.append(AnalysisMethod(
                agent="PICO-Parser",
                method="llm-enhanced",
                llm_model=llm_config["model"] if llm_config and llm_config["available"] else None,
                llm_provider=llm_config["provider"] if llm_config and llm_config["available"] else None
            ))
        except Exception as e:
            logger.warning(f"⚠️ Enhanced PICO parser failed, falling back to rule-based: {e}")
            pico_issues = pico_parser.run(manuscript)
            issues += pico_issues
            logger.info(f"✅ Rule-based PICO parsing completed - found {len(pico_issues)} issues")
            analysis_methods.append(AnalysisMethod(
                agent="PICO-Parser",
                method="rule-based",
                fallback_reason="LLM authentication failed"
            ))
    else:
        logger.info("📋 Using rule-based PICO parsing (LLM agents not available)...")
        pico_issues = pico_parser.run(manuscript)
        issues += pico_issues
        logger.info(f"✅ Rule-based PICO parsing completed - found {len(pico_issues)} issues")
        analysis_methods.append(AnalysisMethod(
            agent="PICO-Parser",
            method="rule-based"
        ))
    
    # PRISMA Validation - Keep existing rule-based approach
    logger.info("📊 Starting PRISMA validation...")
    prisma_issues = prisma_checker.run(manuscript)
    issues += prisma_issues
    logger.info(f"✅ PRISMA validation completed - found {len(prisma_issues)} issues")
    analysis_methods.append(AnalysisMethod(
        agent="PRISMA-Checker",
        method="rule-based"
    ))
    
    # Risk of Bias Assessment - New LLM-enhanced agent
    logger.info("⚖️ Starting Risk of Bias assessment...")
    if LLM_AGENTS_AVAILABLE:
        try:
            logger.info("🤖 Attempting LLM-enhanced Risk of Bias assessment...")
            rob_assessor = RoBAssessor(use_llm=True)
            rob_issues = rob_assessor.run(manuscript)
            issues += rob_issues
            logger.info(f"✅ LLM-enhanced Risk of Bias assessment completed - found {len(rob_issues)} issues")
            analysis_methods.append(AnalysisMethod(
                agent="Risk-of-Bias",
                method="llm-enhanced",
                llm_model=llm_config["model"] if llm_config and llm_config["available"] else None,
                llm_provider=llm_config["provider"] if llm_config and llm_config["available"] else None
            ))
        except Exception as e:
            logger.warning(f"⚠️ Risk of Bias assessor failed: {e}")
            logger.info("📋 No fallback available for Risk of Bias - skipping")
            analysis_methods.append(AnalysisMethod(
                agent="Risk-of-Bias",
                method="rule-based",
                fallback_reason="LLM authentication failed"
            ))
    else:
        logger.info("📋 Risk of Bias assessment skipped (LLM agents not available)")
    
    # Meta-Analysis - Keep existing approach
    logger.info("📈 Starting Meta-analysis...")
    meta_results = meta_analysis.run(manuscript)
    logger.info(f"✅ Meta-analysis completed - generated {len(meta_results)} results")
    analysis_methods.append(AnalysisMethod(
        agent="Meta-Analysis",
        method="rule-based"
    ))
    
    # Create analysis metadata
    metadata = AnalysisMetadata(
        analysis_methods=analysis_methods,
        llm_available=llm_config["available"] if llm_config else False,
        total_llm_calls=len([m for m in analysis_methods if m.method == "llm-enhanced"])
    )
    
    # Final summary
    total_issues = len(issues)
    severity_counts = {}
    for issue in issues:
        sev = issue.severity
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
    
    logger.info(f"🎉 Analysis complete! Total issues: {total_issues}")
    for severity in ['high', 'medium', 'low']:
        count = severity_counts.get(severity, 0)
        if count > 0:
            logger.info(f"   {severity.upper()}: {count} issues")
    
    logger.info(f"🤖 LLM calls made: {metadata.total_llm_calls}")
    
    return ReviewResult(issues=issues, meta=meta_results, analysis_metadata=metadata)

def enhanced_review(manuscript: Manuscript, use_llm: bool = True) -> ReviewResult:
    """
    Fully enhanced review workflow with explicit LLM control and graceful fallbacks.
    """
    issues: List[Issue] = []
    analysis_methods: List[AnalysisMethod] = []
    llm_config = get_llm_config()
    
    # Enhanced PICO Analysis with graceful fallback
    if LLM_AGENTS_AVAILABLE and use_llm:
        try:
            enhanced_pico = EnhancedPICOParser(use_llm=True, fallback_to_rules=True)
            issues += enhanced_pico.run(manuscript)
            analysis_methods.append(AnalysisMethod(
                agent="PICO-Parser",
                method="llm-enhanced",
                llm_model=llm_config["model"] if llm_config and llm_config["available"] else None,
                llm_provider=llm_config["provider"] if llm_config and llm_config["available"] else None
            ))
        except Exception as e:
            print(f"Enhanced PICO parser failed in enhanced_review, falling back to rule-based: {e}")
            issues += pico_parser.run(manuscript)
            analysis_methods.append(AnalysisMethod(
                agent="PICO-Parser",
                method="rule-based",
                fallback_reason="LLM authentication failed"
            ))
    else:
        issues += pico_parser.run(manuscript)
        analysis_methods.append(AnalysisMethod(
            agent="PICO-Parser",
            method="rule-based",
            fallback_reason="LLM disabled by parameter" if not use_llm else None
        ))
    
    # PRISMA Validation
    issues += prisma_checker.run(manuscript)
    analysis_methods.append(AnalysisMethod(
        agent="PRISMA-Checker",
        method="rule-based"
    ))
    
    # Risk of Bias Assessment with graceful fallback
    if LLM_AGENTS_AVAILABLE and use_llm:
        try:
            rob_assessor = RoBAssessor(use_llm=True)
            issues += rob_assessor.run(manuscript)
            analysis_methods.append(AnalysisMethod(
                agent="Risk-of-Bias",
                method="llm-enhanced",
                llm_model=llm_config["model"] if llm_config and llm_config["available"] else None,
                llm_provider=llm_config["provider"] if llm_config and llm_config["available"] else None
            ))
        except Exception as e:
            print(f"Risk of Bias assessor failed in enhanced_review: {e}")
            analysis_methods.append(AnalysisMethod(
                agent="Risk-of-Bias",
                method="rule-based",
                fallback_reason="LLM authentication failed"
            ))
    else:
        analysis_methods.append(AnalysisMethod(
            agent="Risk-of-Bias",
            method="rule-based",
            fallback_reason="LLM disabled by parameter" if not use_llm else "LLM agents not available"
        ))
    
    # Meta-Analysis
    meta: List[MetaResult] = meta_analysis.run(manuscript)
    analysis_methods.append(AnalysisMethod(
        agent="Meta-Analysis",
        method="rule-based"
    ))
    
    # Create analysis metadata
    metadata = AnalysisMetadata(
        analysis_methods=analysis_methods,
        llm_available=llm_config["available"] if llm_config else False,
        total_llm_calls=len([m for m in analysis_methods if m.method == "llm-enhanced"])
    )
    
    return ReviewResult(issues=issues, meta=meta, analysis_metadata=metadata)
