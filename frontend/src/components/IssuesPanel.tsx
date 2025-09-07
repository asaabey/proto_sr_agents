import React from 'react';
import { useAppState } from '../state';

export const IssuesPanel: React.FC = () => {
    const { agentStates, finalResult } = useAppState();
    // Prefer final result issues; fallback to aggregated agent issues
    const rawIssues: any[] = (finalResult?.issues && finalResult.issues.length > 0)
        ? finalResult.issues as any[]
        : Object.values(agentStates).flatMap(a => a.issues as any[]);

    const issues = rawIssues.map(i => ({
        id: i.id || i.item || Math.random().toString(36).slice(2),
        title: i.title || i.item || i.id || 'Issue',
        severity: (i.severity || 'medium').toString().toUpperCase(),
        category: i.category || i.agent || 'OTHER',
        recommendation: i.recommendation || i.fix || '',
        evidence: i.evidence || null,
    }));

    const renderEvidence = (evidence: any) => {
        if (!evidence) return null;
        if (typeof evidence === 'string') return evidence;
        try {
            // Provide a compact key:value list instead of raw object
            if (typeof evidence === 'object') {
                const entries = Object.entries(evidence).slice(0, 6);
                return entries.map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' | ');
            }
            return String(evidence);
        } catch {
            return '—';
        }
    };
    return (
        <div className="space-y-2">
            {issues.length === 0 && <div className="text-xs text-muted-foreground">No issues yet.</div>}
            {issues.map(i => {
                const evSummary = renderEvidence(i.evidence);
                return (
                    <div key={i.id} className="rounded border p-2 text-xs space-y-1 bg-card">
                        <div className="flex items-center justify-between">
                            <span className="font-medium">{i.title}</span>
                            <span className="px-2 py-0.5 rounded bg-secondary text-secondary-foreground text-[10px]">{i.severity}</span>
                        </div>
                        <div className="text-muted-foreground">{i.category}</div>
                        {evSummary && <div className="text-[11px] break-words">{evSummary}</div>}
                        {i.recommendation && <div className="text-[11px] text-primary">{i.recommendation}</div>}
                    </div>
                );
            })}
        </div>
    );
};
