"""
Langraph-based Multi-Agent Orchestrator for Systematic Review Analysis.

This module implements a truly multi-agentic system using Langraph where agents
can communicate, hand off tasks, and make collaborative decisions.
"""

from typing import List, Optional, Literal, TypedDict, Annotated
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from app.services.llm_client import get_llm_client

from app.models.schemas import (
    Manuscript,
    ReviewResult,
    Issue,
    MetaResult,
    AnalysisMethod,
)
from app.agents import pico_parser, prisma_checker, meta_analysis
from app.services.llm_config import get_llm_environment

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("langraph_orchestrator")


# Define the state schema for our multi-agent system
class MultiAgentState(TypedDict):
    """State shared between all agents in the systematic review analysis."""

    manuscript: Manuscript
    issues: List[Issue]
    meta_results: List[MetaResult]
    analysis_methods: List[AnalysisMethod]
    current_agent: Optional[str]
    supervisor_decision: Optional[str]
    llm_config: Optional[dict]
    completed_agents: List[str]


# Initialize LLM models
def get_llm_model():
    """Get the LLM client using the existing configuration system."""
    try:
        return get_llm_client()
    except Exception:
        logger.warning(
            "Could not initialize LLM client, supervisor will use fallback logic"
        )
        return None


# Define handoff tools for agent communication
@tool
def transfer_to_pico_parser(state_update: dict = None):
    """Transfer control to the PICO parser agent for research question analysis."""
    logger.info("🤝 [Supervisor] Transferring to PICO Parser agent")
    return Command(goto="pico_parser_agent", update=state_update or {})


@tool
def transfer_to_prisma_checker(state_update: dict = None):
    """Transfer control to the PRISMA checker agent for flow diagram validation."""
    logger.info("🤝 [Supervisor] Transferring to PRISMA Checker agent")
    return Command(goto="prisma_checker_agent", update=state_update or {})


@tool
def transfer_to_rob_assessor(state_update: dict = None):
    """Transfer control to the Risk of Bias assessor agent."""
    logger.info("🤝 [Supervisor] Transferring to ROB Assessor agent")
    return Command(goto="rob_assessor_agent", update=state_update or {})


@tool
def transfer_to_meta_analyzer(state_update: dict = None):
    """Transfer control to the Meta-analysis agent."""
    logger.info("🤝 [Supervisor] Transferring to Meta-Analysis agent")
    return Command(goto="meta_analysis_agent", update=state_update or {})


@tool
def finalize_review(state_update: dict = None):
    """Finalize the systematic review analysis."""
    logger.info("✅ [Supervisor] Finalizing systematic review analysis")
    return Command(goto=END, update=state_update or {})


# Supervisor Agent - Decides which agents to call and in what order
def supervisor_agent(state: MultiAgentState) -> Command:
    """Supervisor agent that orchestrates the multi-agent workflow."""
    logger.info("🎯 [Supervisor] Analyzing manuscript and deciding next steps...")

    manuscript = state["manuscript"]
    completed_agents = state.get("completed_agents", [])
    issues = state.get("issues", [])

    # Get LLM configuration
    llm_config = state.get("llm_config")
    if not llm_config:
        try:
            env = get_llm_environment()
            llm_config = {
                "provider": env.settings.default_provider,
                "model": env.settings.default_model,
                "available": env.validate_setup()["configured"],
            }
            state["llm_config"] = llm_config
        except Exception:
            llm_config = {"available": False}


def supervisor_agent(state: MultiAgentState) -> Command:
    """Supervisor agent that orchestrates the multi-agent workflow."""
    logger.info("🎯 [Supervisor] Analyzing manuscript and deciding next steps...")

    manuscript = state["manuscript"]
    completed_agents = state.get("completed_agents", [])
    issues = state.get("issues", [])

    logger.info(f"🎯 [Supervisor] Completed agents so far: {completed_agents}")

    # Get LLM configuration
    llm_config = state.get("llm_config")
    if not llm_config:
        try:
            env = get_llm_environment()
            llm_config = {
                "provider": env.settings.default_provider,
                "model": env.settings.default_model,
                "available": env.validate_setup()["configured"],
            }
            state["llm_config"] = llm_config
        except Exception:
            llm_config = {"available": False}

    # Check if all agents are completed
    all_agents = ["pico_parser", "prisma_checker", "rob_assessor", "meta_analysis"]
    if set(completed_agents) == set(all_agents):
        logger.info("✅ [Supervisor] All agents completed, finalizing review")
        return state, Command(goto=END)

    # Determine next agent based on completion status (sequential)
    next_agent = None
    for agent in all_agents:
        if agent not in completed_agents:
            next_agent = agent
            break

    logger.info(f"🎯 [Supervisor] Next agent to run: {next_agent}")

    if not next_agent:
        logger.info("✅ [Supervisor] All agents completed, finalizing review")
        return state, Command(goto=END)

    # Map agent names to node names
    agent_node_map = {
        "pico_parser": "pico_parser_agent",
        "prisma_checker": "prisma_checker_agent",
        "rob_assessor": "rob_assessor_agent",
        "meta_analysis": "meta_analysis_agent",
    }

    target_node = agent_node_map.get(next_agent)
    if target_node:
        logger.info(f"🎯 [Supervisor] Routing to {target_node}")
        return state, Command(goto=target_node)
    else:
        logger.error(f"❌ [Supervisor] Unknown agent: {next_agent}")
        return state, Command(goto=END)


# Individual Agent Nodes
def pico_parser_agent(state: MultiAgentState) -> Command:
    """PICO Parser Agent - analyzes research questions and PICO framework."""
    logger.info("🎯 [PICO-Parser] Starting PICO analysis...")

    manuscript = state["manuscript"]
    issues = state.get("issues", [])
    analysis_methods = state.get("analysis_methods", [])
    llm_config = state.get("llm_config", {})

    # Try enhanced PICO parsing first
    try:
        from app.agents.pico_parser_enhanced import EnhancedPICOParser

        parser = EnhancedPICOParser(use_llm=llm_config.get("available", False))
        new_issues = parser.run(manuscript)
        issues.extend(new_issues)

        analysis_methods.append(
            AnalysisMethod(
                agent="PICO-Parser",
                method=(
                    "llm-enhanced"
                    if llm_config.get("available", False)
                    else "rule-based"
                ),
                llm_model=(
                    llm_config.get("model")
                    if llm_config.get("available", False)
                    else None
                ),
                llm_provider=(
                    llm_config.get("provider")
                    if llm_config.get("available", False)
                    else None
                ),
            )
        )

    except Exception as e:
        logger.warning(
            f"⚠️ [PICO-Parser] Enhanced parsing failed: {e}, using basic parser"
        )
        new_issues = pico_parser.run(manuscript)
        issues.extend(new_issues)
        analysis_methods.append(
            AnalysisMethod(agent="PICO-Parser", method="rule-based")
        )

    # Update state
    state["issues"] = issues
    state["analysis_methods"] = analysis_methods
    state["completed_agents"] = state.get("completed_agents", []) + ["pico_parser"]

    logger.info(f"✅ [PICO-Parser] Completed - found {len(new_issues)} issues")
    logger.info(
        f"✅ [PICO-Parser] Updated completed_agents: {state.get('completed_agents', [])}"
    )
    return state, Command(goto="supervisor")


def prisma_checker_agent(state: MultiAgentState) -> Command:
    """PRISMA Checker Agent - validates flow diagram compliance."""
    logger.info("📊 [PRISMA-Checker] Starting PRISMA validation...")

    manuscript = state["manuscript"]
    issues = state.get("issues", [])
    analysis_methods = state.get("analysis_methods", [])
    llm_config = state.get("llm_config", {})

    # Try enhanced PRISMA checking first
    try:
        from app.agents.prisma_checker import EnhancedPRISMAChecker

        checker = EnhancedPRISMAChecker(use_llm=llm_config.get("available", False))
        new_issues = checker.run(manuscript)
        issues.extend(new_issues)

        analysis_methods.append(
            AnalysisMethod(
                agent="PRISMA-Checker",
                method=(
                    "llm-enhanced"
                    if llm_config.get("available", False)
                    else "rule-based"
                ),
                llm_model=(
                    llm_config.get("model")
                    if llm_config.get("available", False)
                    else None
                ),
                llm_provider=(
                    llm_config.get("provider")
                    if llm_config.get("available", False)
                    else None
                ),
            )
        )

    except Exception as e:
        logger.warning(
            f"⚠️ [PRISMA-Checker] Enhanced checking failed: {e}, using basic checker"
        )
        new_issues = prisma_checker.run(manuscript)
        issues.extend(new_issues)
        analysis_methods.append(
            AnalysisMethod(agent="PRISMA-Checker", method="rule-based")
        )

    # Update state
    state["issues"] = issues
    state["analysis_methods"] = analysis_methods
    state["completed_agents"] = state.get("completed_agents", []) + ["prisma_checker"]

    logger.info(f"✅ [PRISMA-Checker] Completed - found {len(new_issues)} issues")
    return state, Command(goto="supervisor")


def rob_assessor_agent(state: MultiAgentState) -> Command:
    """Risk of Bias Assessor Agent - evaluates study quality."""
    logger.info("⚖️ [ROB-Assessor] Starting Risk of Bias assessment...")

    manuscript = state["manuscript"]
    issues = state.get("issues", [])
    analysis_methods = state.get("analysis_methods", [])
    llm_config = state.get("llm_config", {})

    try:
        from app.agents.rob_assessor import RoBAssessor

        assessor = RoBAssessor(use_llm=True)
        new_issues = assessor.run(manuscript)
        issues.extend(new_issues)

        analysis_methods.append(
            AnalysisMethod(
                agent="Risk-of-Bias",
                method="llm-enhanced",
                llm_model=llm_config.get("model"),
                llm_provider=llm_config.get("provider"),
            )
        )

    except Exception as e:
        logger.warning(f"⚠️ [ROB-Assessor] LLM assessment failed: {e}")
        analysis_methods.append(
            AnalysisMethod(
                agent="Risk-of-Bias",
                method="rule-based",
                fallback_reason="LLM authentication failed",
            )
        )

    # Update state
    state["issues"] = issues
    state["analysis_methods"] = analysis_methods
    state["completed_agents"] = state.get("completed_agents", []) + ["rob_assessor"]

    logger.info(
        f"✅ [ROB-Assessor] Completed - found {len(new_issues) if 'new_issues' in locals() else 0} issues"
    )
    return state, Command(goto="supervisor")


def meta_analysis_agent(state: MultiAgentState) -> Command:
    """Meta-Analysis Agent - performs statistical analysis."""
    logger.info("📈 [Meta-Analysis] Starting statistical analysis...")

    manuscript = state["manuscript"]
    meta_results = state.get("meta_results", [])
    analysis_methods = state.get("analysis_methods", [])
    llm_config = state.get("llm_config", {})

    # Try enhanced meta-analysis first
    try:
        from app.agents.meta_analysis import EnhancedMetaAnalysis

        analyzer = EnhancedMetaAnalysis(use_llm=llm_config.get("available", False))
        new_meta_results = analyzer.run(manuscript)
        meta_results.extend(new_meta_results)

        analysis_methods.append(
            AnalysisMethod(
                agent="Meta-Analysis",
                method=(
                    "llm-enhanced"
                    if llm_config.get("available", False)
                    else "rule-based"
                ),
                llm_model=(
                    llm_config.get("model")
                    if llm_config.get("available", False)
                    else None
                ),
                llm_provider=(
                    llm_config.get("provider")
                    if llm_config.get("available", False)
                    else None
                ),
            )
        )

    except Exception as e:
        logger.warning(
            f"⚠️ [Meta-Analysis] Enhanced analysis failed: {e}, using basic analyzer"
        )
        new_meta_results = meta_analysis.run(manuscript)
        meta_results.extend(new_meta_results)
        analysis_methods.append(
            AnalysisMethod(agent="Meta-Analysis", method="rule-based")
        )

    # Update state
    state["meta_results"] = meta_results
    state["analysis_methods"] = analysis_methods
    state["completed_agents"] = state.get("completed_agents", []) + ["meta_analysis"]

    logger.info(
        f"✅ [Meta-Analysis] Completed - generated {len(new_meta_results)} results"
    )
    return state, Command(goto="supervisor")


# Build the multi-agent graph
def build_multi_agent_graph():
    """Build the Langraph multi-agent system for systematic review analysis."""
    logger.info("🔧 Building multi-agent graph...")

    # Create the state graph
    builder = StateGraph(MultiAgentState)

    # Add nodes (agents)
    builder.add_node("supervisor", supervisor_agent)
    builder.add_node("pico_parser_agent", pico_parser_agent)
    builder.add_node("prisma_checker_agent", prisma_checker_agent)
    builder.add_node("rob_assessor_agent", rob_assessor_agent)
    builder.add_node("meta_analysis_agent", meta_analysis_agent)

    # Define the workflow
    builder.add_edge(START, "supervisor")

    # Compile the graph with higher recursion limit
    graph = builder.compile()
    graph.recursion_limit = 50  # Increase from default 25

    logger.info("✅ Multi-agent graph built successfully")
    return graph


# Global graph instance
_multi_agent_graph = None


def get_multi_agent_graph():
    """Get or create the multi-agent graph instance."""
    global _multi_agent_graph
    if _multi_agent_graph is None:
        _multi_agent_graph = build_multi_agent_graph()
    return _multi_agent_graph


# Main function to run the multi-agent analysis
def run_multi_agent_review(manuscript: Manuscript) -> ReviewResult:
    """
    Run the multi-agent systematic review analysis using Langraph.

    This function orchestrates multiple specialized agents that can communicate
    and collaborate on analyzing a systematic review manuscript.
    """
    logger.info("🚀 Starting multi-agent systematic review analysis...")

    # Initialize state
    initial_state: MultiAgentState = {
        "manuscript": manuscript,
        "issues": [],
        "meta_results": [],
        "analysis_methods": [],
        "current_agent": None,
        "supervisor_decision": None,
        "llm_config": None,
        "completed_agents": [],
    }

    # Get the multi-agent graph
    graph = get_multi_agent_graph()

    # Run the multi-agent workflow
    try:
        final_state = graph.invoke(initial_state)

        # Extract results
        issues = final_state.get("issues", [])
        meta_results = final_state.get("meta_results", [])
        analysis_methods = final_state.get("analysis_methods", [])

        # Create analysis metadata
        llm_config = final_state.get("llm_config", {})
        from app.models.schemas import AnalysisMetadata

        metadata = AnalysisMetadata(
            analysis_methods=analysis_methods,
            llm_available=llm_config.get("available", False),
            total_llm_calls=len(
                [m for m in analysis_methods if m.method == "llm-enhanced"]
            ),
        )

        # Log completion summary
        total_issues = len(issues)
        severity_counts = {}
        for issue in issues:
            sev = issue.severity
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        logger.info("🎉 Multi-agent analysis complete!")
        logger.info(f"   Total issues: {total_issues}")
        for severity in ["high", "medium", "low"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                logger.info(f"   {severity.upper()}: {count} issues")
        logger.info(f"   LLM calls: {metadata.total_llm_calls}")
        logger.info(f"   Agents completed: {final_state.get('completed_agents', [])}")

        return ReviewResult(
            issues=issues, meta=meta_results, analysis_metadata=metadata
        )

    except Exception as e:
        logger.error(f"💥 Multi-agent analysis failed: {e}")
        # Fallback to original orchestrator
        logger.info("🔄 Falling back to original orchestrator...")
        from app.orchestrator import simple_review

        return simple_review(manuscript)


# Enhanced review function (for compatibility)
def run_enhanced_multi_agent_review(
    manuscript: Manuscript, use_llm: bool = True
) -> ReviewResult:
    """Enhanced multi-agent review with LLM control."""
    return run_multi_agent_review(manuscript)
