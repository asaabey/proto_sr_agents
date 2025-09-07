import React, { useEffect, useRef, useState } from 'react';
import { useAppState } from '../state';

export const StreamConsole: React.FC = () => {
    const { streamEvents, reviewStatus } = useAppState();
    const [spinnerIndex, setSpinnerIndex] = useState(0);
    const spinnerFrames = ['|', '/', '-', '\\'];
    useEffect(() => {
        if (reviewStatus === 'running' || reviewStatus === 'starting') {
            const id = setInterval(() => setSpinnerIndex(i => (i + 1) % spinnerFrames.length), 120);
            return () => clearInterval(id);
        }
    }, [reviewStatus]);
    const bottomRef = useRef<HTMLDivElement | null>(null);
    useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [streamEvents.length]);
    return (
        <div className="h-64 overflow-auto rounded border bg-muted/30 p-2 text-xs font-mono space-y-0.5">
            {(reviewStatus === 'running' || reviewStatus === 'starting') && (
                <div className="flex gap-2 items-center text-muted-foreground">
                    <span>{spinnerFrames[spinnerIndex]}</span>
                    <span>Analysis in progress...</span>
                </div>
            )}
            {streamEvents.map((e, i) => {
                const isLog = e.event_type === 'log';
                return (
                    <div key={i} className="flex gap-2">
                        <span className={"text-muted-foreground" + (isLog ? ' opacity-60' : '')}>{e.event_type}</span>
                        <span className={isLog ? 'text-muted-foreground' : ''}>{e.message}</span>
                        {e.agent && <span className="text-primary">[{e.agent}]</span>}
                    </div>
                );
            })}
            <div ref={bottomRef} />
        </div>
    );
};
