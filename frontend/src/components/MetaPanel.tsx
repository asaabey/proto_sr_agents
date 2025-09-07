import React from 'react';
import { useAppState } from '../state';

export const MetaPanel: React.FC = () => {
    const { finalResult } = useAppState();
    const first = finalResult?.meta?.[0];
    if (!first) return <div className="text-xs text-muted-foreground">No meta-analysis yet.</div>;
    return (
        <div className="text-sm grid gap-2">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <Stat label="Effect" value={first.pooled != null ? first.pooled.toFixed(3) : '—'} />
                <Stat label="CI" value={(first.ci_low != null && first.ci_high != null) ? `${first.ci_low.toFixed(2)} – ${first.ci_high.toFixed(2)}` : '—'} />
                <Stat label="I²" value={first.I2 != null ? `${first.I2.toFixed(1)}%` : '—'} />
                <Stat label="τ²" value={first.tau2 != null ? first.tau2.toExponential(2) : '—'} />
            </div>
            <div className="text-xs text-muted-foreground">Model: {first.model ?? '—'} • Outcome idx: 0</div>
            <div className="text-xs">(Plots integration TBD - will load images from /artifacts)</div>
        </div>
    );
};

const Stat: React.FC<{ label: string; value?: string }> = ({ label, value }) => (
    <div className="rounded border p-2 bg-card">
        <div className="text-[10px] uppercase text-muted-foreground">{label}</div>
        <div className="font-medium">{value ?? '—'}</div>
    </div>
);
