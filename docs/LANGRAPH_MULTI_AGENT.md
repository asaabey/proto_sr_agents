# Langraph Multi-Agent Architecture

This document describes the new multi-agent architecture implemented using Langraph for the Systematic Review Auditor platform.

## Overview

The application has been upgraded from a simple sequential orchestrator to a truly multi-agentic system using Langraph. This enables:

- **Dynamic agent coordination**: Agents can communicate and hand off tasks
- **Intelligent decision making**: Supervisor agent decides workflow based on manuscript content
- **Parallel processing**: Agents can run concurrently when appropriate
- **Stateful workflows**: Shared state between agents with persistent context
- **Flexible routing**: Conditional execution based on analysis results

## Architecture Components

### 1. State Management
```python
class MultiAgentState(TypedDict):
    manuscript: Manuscript
    issues: List[Issue]
    meta_results: List[MetaResult]
    analysis_methods: List[AnalysisMethod]
    current_agent: Optional[str]
    supervisor_decision: Optional[str]
    llm_config: Optional[dict]
    completed_agents: List[str]
```

### 2. Agent Nodes

#### Supervisor Agent
- **Role**: Central coordinator that analyzes the manuscript and decides which agents to call
- **Decision Logic**: Uses LLM to determine optimal execution order based on manuscript content
- **Fallback**: Sequential execution if LLM fails

#### Specialized Agents
- **PICO Parser**: Analyzes research questions and PICO framework
- **PRISMA Checker**: Validates flow diagram compliance
- **ROB Assessor**: Evaluates risk of bias (LLM-enhanced)
- **Meta-Analysis**: Performs statistical analysis

### 3. Communication Patterns

#### Handoffs
Agents can transfer control to each other using handoff tools:
```python
@tool
def transfer_to_pico_parser(state_update: dict = None):
    return Command(goto="pico_parser_agent", update=state_update)
```

#### State Sharing
All agents share the same state object, allowing them to:
- Access previous analysis results
- Update the issue list collaboratively
- Track completion status
- Share LLM configuration

## Workflow Execution

1. **Initialization**: Supervisor receives manuscript and initializes state
2. **Analysis**: Supervisor evaluates manuscript content and agent completion status
3. **Decision**: LLM-powered decision on which agent to execute next
4. **Execution**: Selected agent runs its analysis and updates state
5. **Handoff**: Agent returns control to supervisor
6. **Iteration**: Process repeats until all analyses complete
7. **Finalization**: Results compiled and returned

## Benefits of Multi-Agent Architecture

### 1. Intelligent Orchestration
- Supervisor can skip irrelevant analyses
- Dynamic routing based on manuscript characteristics
- Optimized execution order

### 2. Collaborative Analysis
- Agents can build on each other's work
- Cross-validation between analyses
- Shared context improves accuracy

### 3. Scalability
- Easy to add new specialized agents
- Parallel execution when dependencies allow
- Modular architecture

### 4. Robustness
- Graceful fallback to sequential execution
- Error handling at agent level
- State persistence through failures

## Usage

The new architecture is fully backward compatible. Existing API endpoints work unchanged:

```python
# Simple review
result = run_multi_agent_review(manuscript)

# Enhanced review with LLM control
result = run_enhanced_multi_agent_review(manuscript, use_llm=True)
```

## Future Enhancements

### 1. Advanced Architectures
- **Swarm**: Agents dynamically hand off without central supervisor
- **Hierarchical**: Teams of agents with sub-supervisors
- **Network**: Many-to-many agent communication

### 2. Human-in-the-Loop
- Supervisor can request human input for complex decisions
- Manual agent selection and routing
- Interactive workflow modification

### 3. Learning and Adaptation
- Agents learn from previous analyses
- Adaptive routing based on success patterns
- Performance optimization over time

## Migration Notes

- Original `orchestrator.py` remains for fallback
- All existing functionality preserved
- New features are opt-in through new functions
- State schema designed for extensibility

## Testing

The multi-agent system includes comprehensive logging:
- Agent execution tracking
- Decision reasoning (when LLM available)
- Performance metrics
- Error handling and fallbacks

Monitor logs for:
- Supervisor decisions and reasoning
- Agent handoffs and state updates
- Completion status and timing
- LLM usage and fallback events
