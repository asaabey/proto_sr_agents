import { create } from 'zustand';
import type { Manuscript, StreamEvent, Issue, ReviewResult } from './types';

interface AgentState { status: string; startedAt?: string; endedAt?: string; issues: Issue[]; }

interface AppState {
    manuscript: Manuscript | null;
    reviewStatus: 'idle' | 'starting' | 'running' | 'completed' | 'error';
    agentStates: Record<string, AgentState>;
    streamEvents: StreamEvent[];
    finalResult?: ReviewResult;
    error?: string;
    setManuscript: (m: Manuscript | null) => void;
    startReview: () => void;
    updateFromEvent: (ev: StreamEvent) => void;
    setError: (e: string) => void;
    reset: () => void;
}

const baseAgents = ['PICO', 'PRISMA', 'ROB', 'META'];

const emptyAgentStates = (): Record<string, AgentState> => Object.fromEntries(baseAgents.map(a => [a, { status: 'idle', issues: [] }])) as Record<string, AgentState>;

export const useAppState = create<AppState>((set) => ({
    manuscript: null,
    reviewStatus: 'idle',
    agentStates: emptyAgentStates(),
    streamEvents: [],
    setManuscript: (m: Manuscript | null) => set({ manuscript: m }),
    startReview: () => set({ reviewStatus: 'starting', streamEvents: [], agentStates: emptyAgentStates(), finalResult: undefined, error: undefined }),
    updateFromEvent: (ev: StreamEvent) => set((s: AppState) => {
        const agentStates = { ...s.agentStates };
        if (ev.agent && agentStates[ev.agent]) {
            if (ev.event_type === 'agent_start') agentStates[ev.agent] = { ...agentStates[ev.agent], status: 'running', startedAt: new Date().toISOString() };
            if (ev.event_type === 'agent_complete') agentStates[ev.agent] = { ...agentStates[ev.agent], status: 'done', endedAt: new Date().toISOString() };
            if (ev.event_type === 'issue' && ev.data?.issue) agentStates[ev.agent] = { ...agentStates[ev.agent], issues: [...agentStates[ev.agent].issues, ev.data.issue] };
        }
        let reviewStatus = s.reviewStatus;
        if (ev.event_type === 'agent_start') reviewStatus = 'running';
        if (ev.event_type === 'complete') reviewStatus = 'completed';
        if (ev.event_type === 'error') reviewStatus = 'error';
        const finalResult = ev.event_type === 'complete' && ev.data?.result ? ev.data.result as ReviewResult : s.finalResult;
        return { streamEvents: [...s.streamEvents, ev], agentStates, reviewStatus, finalResult };
    }),
    setError: (e: string) => set({ error: e, reviewStatus: 'error' }),
    reset: () => set({ manuscript: null, reviewStatus: 'idle', agentStates: emptyAgentStates(), streamEvents: [], finalResult: undefined, error: undefined })
}));
