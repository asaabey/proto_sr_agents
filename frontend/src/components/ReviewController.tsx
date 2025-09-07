import React from 'react';
import { useAppState } from '../state';
import { startStream } from '../lib/api';

export const ReviewController: React.FC = () => {
    const { manuscript, startReview, updateFromEvent, setError, reviewStatus } = useAppState();
    const disabled = !manuscript || reviewStatus === 'running' || reviewStatus === 'starting';
    const onStart = async () => {
        if (!manuscript) return;
        startReview();
        await startStream(manuscript, updateFromEvent, (e: unknown) => setError(String(e)));
    };
    return (
        <div className="flex gap-2 items-center">
            <button disabled={disabled} onClick={onStart} className="px-4 py-2 rounded bg-primary disabled:opacity-40 text-primary-foreground text-sm">Start Review</button>
            <div className="text-xs text-muted-foreground">Status: {reviewStatus}</div>
        </div>
    );
};
