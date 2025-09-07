import React from 'react';
import { useAppState } from '../state';

const statusColor: Record<string, string> = {
    idle: 'bg-muted text-muted-foreground',
    running: 'bg-blue-500 text-white',
    done: 'bg-green-600 text-white',
    error: 'bg-destructive text-destructive-foreground'
};

export const AgentStatusBoard: React.FC = () => {
    const { agentStates } = useAppState();
    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(agentStates).map(([agent, st]) => (
                <div key={agent} className="rounded border p-2 space-y-1 bg-card">
                    <div className="text-sm font-medium flex items-center justify-between">
                        <span>{agent}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wide ${statusColor[st.status] || 'bg-secondary'}`}>{st.status}</span>
                    </div>
                    <div className="text-[10px] text-muted-foreground">Issues: {st.issues.length}</div>
                </div>
            ))}
        </div>
    );
};
