"""
Enhanced PICO Parser with LLM integration.

Combines rule-based extraction with LLM-powered analysis
for improved PICO element identification and validation.
"""

from typing import List, Optional
import re
import json
import logging
from app.models.schemas import Manuscript, Issue, PICO
from app.services.llm_client import get_llm_client
from app.services.prompt_templates import get_prompt

logger = logging.getLogger("agents.pico_parser_enhanced")

# Import original functions for fallback
from app.agents.pico_parser import (
    _validate_outcome_quality,
    _validate_population_specificity
)

class EnhancedPICOParser:
    """PICO parser with LLM enhancement capabilities."""
    
    def __init__(self, use_llm: bool = True, fallback_to_rules: bool = True):
        self.use_llm = use_llm
        self.fallback_to_rules = fallback_to_rules
        self.llm_client = get_llm_client() if use_llm else None
    
    def run(self, manuscript: Manuscript) -> List[Issue]:
        """Enhanced PICO parsing with LLM integration."""
        logger.info("🎯🤖 [Enhanced-PICO-Parser] Starting enhanced PICO analysis with LLM integration...")
        logger.debug(f"🔧 [Enhanced-PICO-Parser] Configuration - LLM: {self.use_llm}, Fallback: {self.fallback_to_rules}")
        
        issues = []
        
        # If PICO already exists, validate it
        if manuscript.question:
            logger.info("✅ [Enhanced-PICO-Parser] Existing PICO found, validating quality...")
            existing_issues = self._validate_existing_pico(manuscript.question)
            issues.extend(existing_issues)
            logger.info(f"📋 [Enhanced-PICO-Parser] Existing PICO validation complete - found {len(existing_issues)} issues")
        else:
            logger.info("❌ [Enhanced-PICO-Parser] No existing PICO question found")
        
        # If no PICO or LLM extraction enabled, try to extract/enhance
        if not manuscript.question or self.use_llm:
            logger.info("🔍 [Enhanced-PICO-Parser] Attempting PICO extraction/enhancement...")
            
            # For this demo, we'll extract from title since we don't have full text
            manuscript_text = self._extract_available_text(manuscript)
            logger.debug(f"📄 [Enhanced-PICO-Parser] Extracted {len(manuscript_text)} characters for analysis")
            
            if manuscript_text and self.use_llm and self.llm_client:
                logger.info("🤖 [Enhanced-PICO-Parser] Using LLM for PICO extraction...")
                try:
                    enhanced_pico = self._extract_pico_with_llm(manuscript_text)
                    if enhanced_pico:
                        logger.info("✅ [Enhanced-PICO-Parser] LLM successfully extracted PICO elements")
                        logger.debug(f"   Population: {enhanced_pico.population[:100] if enhanced_pico.population else 'None'}...")
                        logger.debug(f"   Intervention: {enhanced_pico.intervention[:100] if enhanced_pico.intervention else 'None'}...")
                        logger.debug(f"   Comparator: {enhanced_pico.comparator[:100] if enhanced_pico.comparator else 'None'}...")
                        logger.debug(f"   Outcomes: {len(enhanced_pico.outcomes) if enhanced_pico.outcomes else 0} specified")
                        
                        # If no existing PICO, use LLM result
                        if not manuscript.question:
                            manuscript.question = enhanced_pico
                            logger.info("📝 [Enhanced-PICO-Parser] Applied LLM-extracted PICO to manuscript")
                        
                        # Validate the LLM-extracted PICO
                        logger.info("🔍 [Enhanced-PICO-Parser] Validating LLM-extracted PICO quality...")
                        validation_issues = self._validate_existing_pico(enhanced_pico)
                        issues.extend(validation_issues)
                        logger.info(f"📊 [Enhanced-PICO-Parser] LLM-extracted PICO validation found {len(validation_issues)} issues")
                        
                        # Add extraction quality note
                        issues.append(Issue(
                            id="PICO-LLM-001",
                            severity="low",
                            category="PICO",
                            item="PICO elements extracted using AI analysis",
                            evidence={"extraction_method": "LLM", "confidence": "medium"},
                            recommendation="Verify AI-extracted PICO elements for accuracy.",
                            agent="Enhanced-PICO-Parser"
                        ))
                        logger.debug("📌 [Enhanced-PICO-Parser] Added LLM extraction quality note")
                    else:
                        logger.warning("❌ [Enhanced-PICO-Parser] LLM extraction returned no valid PICO elements")
                    
                except Exception as e:
                    logger.error(f"💥 [Enhanced-PICO-Parser] LLM PICO extraction failed: {str(e)}")
                    if self.fallback_to_rules:
                        logger.info("🔄 [Enhanced-PICO-Parser] Falling back to rule-based analysis...")
                        fallback_issues = self._fallback_rule_based_analysis(manuscript)
                        issues.extend(fallback_issues)
                        logger.info(f"📋 [Enhanced-PICO-Parser] Rule-based fallback completed - found {len(fallback_issues)} issues")
                    
                    issues.append(Issue(
                        id="PICO-LLM-ERROR-001",
                        severity="low",
                        category="OTHER",
                        item="LLM PICO extraction failed, using rule-based analysis",
                        evidence={"error": str(e)},
                        recommendation="Consider manual PICO specification for optimal analysis.",
                        agent="Enhanced-PICO-Parser"
                    ))
            else:
                logger.info("📋 [Enhanced-PICO-Parser] No LLM available or enabled, using rule-based fallback...")
                # Fallback to rule-based analysis
                if self.fallback_to_rules:
                    fallback_issues = self._fallback_rule_based_analysis(manuscript)
                    issues.extend(fallback_issues)
                    logger.info(f"📋 [Enhanced-PICO-Parser] Rule-based fallback completed - found {len(fallback_issues)} issues")
        
        logger.info(f"✅ [Enhanced-PICO-Parser] Enhanced PICO analysis complete - identified {len(issues)} total issues")
        return issues
    
    def _extract_available_text(self, manuscript: Manuscript) -> str:
        """Extract available text from manuscript for LLM analysis."""
        text_parts = []
        
        if manuscript.title:
            text_parts.append(f"Title: {manuscript.title}")
        
        if manuscript.question:
            pico_text = f"""
            Population: {manuscript.question.population or 'Not specified'}
            Intervention: {manuscript.question.intervention or 'Not specified'}
            Comparator: {manuscript.question.comparator or 'Not specified'}
            Outcomes: {', '.join(manuscript.question.outcomes) if manuscript.question.outcomes else 'Not specified'}
            """
            text_parts.append(f"PICO: {pico_text}")
        
        # Include search strategy context
        if manuscript.search:
            search_text = []
            for search in manuscript.search:
                search_desc = f"{search.db}: {search.strategy or 'Database search'}"
                if search.dates:
                    search_desc += f" ({search.dates})"
                search_text.append(search_desc)
            text_parts.append(f"Search Strategy: {'; '.join(search_text)}")
        
        return "\n\n".join(text_parts)
    
    def _extract_pico_with_llm(self, manuscript_text: str) -> Optional[PICO]:
        """Extract PICO elements using LLM."""
        logger.debug("🤖 [Enhanced-PICO-Parser] Preparing LLM prompt for PICO extraction...")
        pico_prompt = get_prompt("pico_extraction")
        
        formatted_prompt = pico_prompt.format(manuscript_text=manuscript_text)
        logger.debug(f"📝 [Enhanced-PICO-Parser] Formatted prompt length: {len(formatted_prompt)} characters")
        
        logger.info("🔄 [Enhanced-PICO-Parser] Sending request to LLM...")
        response = self.llm_client.generate_completion_sync(
            prompt=formatted_prompt,
            system_prompt=pico_prompt.system_prompt
        )
        logger.debug(f"📨 [Enhanced-PICO-Parser] LLM response length: {len(response)} characters")
        
        # Parse LLM response
        try:
            logger.debug("🔍 [Enhanced-PICO-Parser] Parsing LLM JSON response...")
            pico_data = json.loads(response)
            
            # Validate required structure
            required_keys = ["population", "intervention", "comparator", "outcomes"]
            missing_keys = [key for key in required_keys if key not in pico_data]
            
            if missing_keys:
                logger.warning(f"❌ [Enhanced-PICO-Parser] LLM response missing required keys: {missing_keys}")
                return None
            
            logger.info("✅ [Enhanced-PICO-Parser] Successfully parsed LLM PICO response")
            return PICO(
                framework="PICO",
                population=pico_data["population"],
                intervention=pico_data["intervention"],
                comparator=pico_data["comparator"],
                outcomes=pico_data["outcomes"] or []
            )
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"💥 [Enhanced-PICO-Parser] Failed to parse LLM PICO response: {e}")
            logger.debug(f"🔍 [Enhanced-PICO-Parser] Raw LLM response: {response[:200]}...")
            return None
    
    def _validate_existing_pico(self, pico: PICO) -> List[Issue]:
        """Validate existing PICO using enhanced logic."""
        issues = []
        
        # Basic completeness check
        missing = []
        if not pico.population:
            missing.append("population")
        if not pico.intervention:
            missing.append("intervention")
        if not pico.comparator:
            missing.append("comparator")
        if not pico.outcomes:
            missing.append("outcomes")
        
        if missing:
            issues.append(Issue(
                id="PICO-COMPLETE-001",
                severity="high" if len(missing) > 2 else "medium",
                category="PICO",
                item="Incomplete PICO specification",
                evidence={"missing": missing},
                recommendation="Provide explicit PICO fields for comprehensive systematic review methodology.",
                agent="Enhanced-PICO-Parser"
            ))
        
        # Enhanced validation using original functions
        if pico.outcomes:
            issues.extend(_validate_outcome_quality(pico.outcomes))
        
        if pico.population:
            issues.extend(_validate_population_specificity(pico.population))
        
        # LLM-enhanced validation if available
        if self.use_llm and self.llm_client:
            issues.extend(self._llm_enhanced_validation(pico))
        
        return issues
    
    def _llm_enhanced_validation(self, pico: PICO) -> List[Issue]:
        """Use LLM for advanced PICO quality assessment.""" 
        logger.info("🧠 [Enhanced-PICO-Parser] Starting LLM-enhanced PICO quality assessment...")
        issues = []
        
        try:
            # Create PICO quality assessment prompt
            pico_text = f"""
            Population: {pico.population}
            Intervention: {pico.intervention}
            Comparator: {pico.comparator}
            Outcomes: {', '.join(pico.outcomes)}
            """
            logger.debug("📝 [Enhanced-PICO-Parser] Created PICO quality assessment prompt")
            
            quality_prompt = f"""
            Assess the quality and specificity of this PICO framework for a systematic review:

            {pico_text}

            Evaluate:
            1. Population specificity (age, condition, setting)
            2. Intervention clarity (dose, duration, delivery)
            3. Comparator appropriateness
            4. Outcome measurability and timeframes
            5. Overall framework coherence

            Return JSON with recommendations for improvement:
            {{
              "quality_score": 0-100,
              "strengths": ["list of well-defined elements"],
              "weaknesses": ["areas needing improvement"],
              "recommendations": ["specific suggestions"],
              "clinical_relevance": "high|medium|low"
            }}
            """
            
            logger.info("🔄 [Enhanced-PICO-Parser] Requesting LLM quality assessment...")
            response = self.llm_client.generate_completion_sync(
                prompt=quality_prompt,
                system_prompt="You are a systematic review methodology expert. Provide specific, actionable feedback on PICO frameworks."
            )
            
            # Parse response and create issues
            logger.debug("🔍 [Enhanced-PICO-Parser] Parsing LLM quality assessment response...")
            quality_assessment = json.loads(response)
            
            quality_score = quality_assessment.get("quality_score", 100)
            clinical_relevance = quality_assessment.get("clinical_relevance", "medium")
            
            logger.info(f"📊 [Enhanced-PICO-Parser] LLM Assessment - Score: {quality_score}/100, Relevance: {clinical_relevance}")
            
            if quality_score < 70:
                logger.warning(f"⚠️ [Enhanced-PICO-Parser] Low quality score detected: {quality_score}")
                issues.append(Issue(
                    id="PICO-QUALITY-001",
                    severity="medium",
                    category="PICO",
                    item="PICO framework could be more specific",
                    evidence=quality_assessment,
                    recommendation="; ".join(quality_assessment.get("recommendations", [])),
                    agent="Enhanced-PICO-Parser"
                ))
            
            if clinical_relevance == "low":
                logger.warning("⚠️ [Enhanced-PICO-Parser] Low clinical relevance detected")
                issues.append(Issue(
                    id="PICO-RELEVANCE-001", 
                    severity="medium",
                    category="PICO",
                    item="PICO framework may have limited clinical relevance",
                    evidence={"clinical_relevance": "low"},
                    recommendation="Consider refining PICO elements to address clinically important questions.",
                    agent="Enhanced-PICO-Parser"
                ))
            
            logger.info(f"✅ [Enhanced-PICO-Parser] LLM quality assessment complete - identified {len(issues)} quality issues")
        
        except Exception as e:
            # Don't fail the whole analysis if LLM enhancement fails
            logger.error(f"💥 [Enhanced-PICO-Parser] LLM PICO validation failed: {e}")
        
        return issues
    
    def _fallback_rule_based_analysis(self, manuscript: Manuscript) -> List[Issue]:
        """Fallback to original rule-based PICO analysis."""
        from app.agents.pico_parser import run as original_pico_run
        return original_pico_run(manuscript)

# Wrapper function to maintain compatibility
def run_enhanced_pico_analysis(manuscript: Manuscript, use_llm: bool = True) -> List[Issue]:
    """Run enhanced PICO analysis with LLM integration."""
    parser = EnhancedPICOParser(use_llm=use_llm)
    return parser.run(manuscript)